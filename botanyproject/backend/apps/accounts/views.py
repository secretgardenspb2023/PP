"""Email auth API (ТЗ Этап 3): register, verify, login, refresh, logout, reset.

Access token is returned in the body; the refresh token lives in an HttpOnly,
SameSite cookie scoped to /api/v1/auth/ and is rotated + blacklisted on refresh
and logout. OAuth (Google/VK/Telegram) and 2FA are added later.
"""
import base64
import binascii
import time

from django.conf import settings
from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.tokens import default_token_generator
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.mail import send_mail
from django.shortcuts import redirect
from django.utils.crypto import constant_time_compare, get_random_string
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django_otp.plugins.otp_totp.models import TOTPDevice
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken
from rest_framework_simplejwt.tokens import RefreshToken

from . import audit, captcha, oauth
from .models import PROVIDER_GOOGLE, PROVIDER_TELEGRAM, PROVIDER_VK
from .serializers import (
    EmailVerifySerializer,
    LoginSerializer,
    OTPSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetSerializer,
    ProfileUpdateSerializer,
    RegisterSerializer,
    UserSerializer,
)

User = get_user_model()


# --------------------------------------------------------------------------- #
#  helpers
# --------------------------------------------------------------------------- #
def _client_ip(request):
    xff = request.META.get("HTTP_X_FORWARDED_FOR")
    return xff.split(",")[0].strip() if xff else request.META.get("REMOTE_ADDR")


def _set_refresh_cookie(response, refresh):
    response.set_cookie(
        settings.AUTH_REFRESH_COOKIE,
        str(refresh),
        max_age=int(settings.SIMPLE_JWT["REFRESH_TOKEN_LIFETIME"].total_seconds()),
        httponly=True,
        secure=settings.AUTH_REFRESH_COOKIE_SECURE,
        samesite=settings.AUTH_REFRESH_COOKIE_SAMESITE,
        path=settings.AUTH_REFRESH_COOKIE_PATH,
    )


def _tokens_response(user, body_extra=None, code=status.HTTP_200_OK):
    refresh = RefreshToken.for_user(user)
    body = {"access": str(refresh.access_token)}
    if body_extra:
        body.update(body_extra)
    response = Response(body, status=code)
    _set_refresh_cookie(response, refresh)
    return response


def _decode_uid(uid):
    try:
        return User.objects.get(pk=force_str(urlsafe_base64_decode(uid)))
    except (User.DoesNotExist, ValueError, TypeError, OverflowError):
        return None


def _send_token_email(user, subject, intro, path):
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    link = f"{settings.FRONTEND_URL}{path}?uid={uid}&token={token}"
    send_mail(
        subject,
        f"{intro}\n\n{link}\n\n(uid={uid} token={token})",
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
    )


# --------------------------------------------------------------------------- #
#  views
# --------------------------------------------------------------------------- #
class RegisterView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth"

    def post(self, request):
        if not captcha.verify_captcha(request.data.get("captcha_token"), _client_ip(request)):
            return Response({"detail": "Проверка капчи не пройдена."}, status=status.HTTP_400_BAD_REQUEST)

        # Повторная регистрация существующего email: если он уже подтверждён —
        # отправляем на вход; если ещё нет — повторно шлём письмо (а не ошибку
        # «уже существует»), позволяя задать свежий пароль/имя. Подтвердить всё
        # равно можно только по ссылке из письма, так что чужой адрес не угнать.
        email = (request.data.get("email") or "").strip()
        existing = User.objects.filter(email__iexact=email).first() if email else None
        if existing is not None:
            if existing.is_active:
                return Response(
                    {"detail": "Этот email уже зарегистрирован. Войдите или восстановите пароль."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            password = request.data.get("password") or ""
            try:
                validate_password(password, existing)
            except ValidationError as exc:
                return Response({"password": list(exc.messages)}, status=status.HTTP_400_BAD_REQUEST)
            name = request.data.get("full_name")
            if name is not None:
                existing.full_name = name
            existing.set_password(password)
            existing.save()
            _send_token_email(
                existing, "Подтверждение регистрации PoiskPlant",
                "Подтвердите ваш email по ссылке:", "/verify-email",
            )
            audit.log_event("register_resend", request=request, user=existing)
            return Response(
                {"detail": "Вы уже регистрировались, но не подтвердили email. "
                           "Мы отправили письмо повторно."},
                status=status.HTTP_200_OK,
            )

        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        audit.log_event("register", request=request, user=user)
        _send_token_email(
            user, "Подтверждение регистрации PoiskPlant",
            "Подтвердите ваш email по ссылке:", "/verify-email",
        )
        return Response(
            {"detail": "Регистрация успешна. Подтвердите email по ссылке из письма."},
            status=status.HTTP_201_CREATED,
        )


class VerifyEmailView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = EmailVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = _decode_uid(serializer.validated_data["uid"])
        if user is None or not default_token_generator.check_token(
            user, serializer.validated_data["token"]
        ):
            return Response({"detail": "Недействительная ссылка."}, status=status.HTTP_400_BAD_REQUEST)
        if not user.is_active:
            user.is_active = True
            user.save(update_fields=["is_active"])
        audit.log_event("email_verified", request=request, user=user)
        return Response({"detail": "Email подтверждён."})


class LoginView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth"

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"]
        try:
            # Pass the underlying Django HttpRequest so django-axes can read the
            # client IP and record attempts (it does not understand DRF's Request).
            user = authenticate(
                getattr(request, "_request", request),
                username=email,
                password=serializer.validated_data["password"],
            )
        except PermissionDenied:  # django-axes lockout (ТЗ 3.7)
            audit.log_event("login_locked", request=request, email=email)
            return Response(
                {"detail": "Слишком много попыток входа. Попробуйте позже."},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )
        if user is None:
            audit.log_event("login_failed", request=request, email=email)
            return Response({"detail": "Неверный email или пароль."}, status=status.HTTP_401_UNAUTHORIZED)
        if not user.is_active:
            audit.log_event("login_inactive", request=request, user=user)
            return Response({"detail": "Email не подтверждён."}, status=status.HTTP_403_FORBIDDEN)

        # Second factor for staff with a confirmed TOTP device (ТЗ 3.12).
        device = TOTPDevice.objects.filter(user=user, confirmed=True).first()
        if device is not None:
            otp = str(request.data.get("otp") or "")
            if not otp:
                return Response(
                    {"detail": "Требуется код 2FA.", "otp_required": True},
                    status=status.HTTP_401_UNAUTHORIZED,
                )
            if not device.verify_token(otp):
                audit.log_event("login_2fa_failed", request=request, user=user)
                return Response({"detail": "Неверный код 2FA."}, status=status.HTTP_401_UNAUTHORIZED)

        audit.log_event("login_success", request=request, user=user)
        return _tokens_response(user, body_extra={"user": UserSerializer(user).data})


class TokenRefreshView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        token = request.COOKIES.get(settings.AUTH_REFRESH_COOKIE)
        if not token:
            return Response({"detail": "Нет refresh-токена."}, status=status.HTTP_401_UNAUTHORIZED)
        try:
            old = RefreshToken(token)
        except TokenError:
            return Response({"detail": "Недействительный токен."}, status=status.HTTP_401_UNAUTHORIZED)
        user = _decode_uid_pk(old.get("user_id"))
        if user is None:
            return Response({"detail": "Пользователь не найден."}, status=status.HTTP_401_UNAUTHORIZED)
        try:
            old.blacklist()  # rotation: invalidate the used refresh token
        except AttributeError:
            pass
        return _tokens_response(user)


class LogoutView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        token = request.COOKIES.get(settings.AUTH_REFRESH_COOKIE)
        if token:
            try:
                RefreshToken(token).blacklist()
            except (TokenError, AttributeError):
                pass
        audit.log_event("logout", request=request)
        response = Response({"detail": "Выход выполнен."})
        response.delete_cookie(settings.AUTH_REFRESH_COOKIE, path=settings.AUTH_REFRESH_COOKIE_PATH)
        return response


class PasswordResetView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth"

    def post(self, request):
        if not captcha.verify_captcha(request.data.get("captcha_token"), _client_ip(request)):
            return Response({"detail": "Проверка капчи не пройдена."}, status=status.HTTP_400_BAD_REQUEST)
        serializer = PasswordResetSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = User.objects.filter(email__iexact=serializer.validated_data["email"]).first()
        audit.log_event("password_reset_requested", request=request,
                        email=serializer.validated_data["email"])
        if user is not None:
            _send_token_email(
                user, "Сброс пароля PoiskPlant",
                "Для сброса пароля перейдите по ссылке:", "/reset-password",
            )
        # Always 200 — do not reveal whether the email is registered.
        return Response({"detail": "Если email зарегистрирован, отправлено письмо."})


class PasswordResetConfirmView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth"

    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = _decode_uid(serializer.validated_data["uid"])
        if user is None or not default_token_generator.check_token(
            user, serializer.validated_data["token"]
        ):
            return Response({"detail": "Недействительная ссылка."}, status=status.HTTP_400_BAD_REQUEST)
        user.set_password(serializer.validated_data["new_password"])
        if not user.is_active:
            user.is_active = True
        user.save()
        audit.log_event("password_reset_done", request=request, user=user)
        return Response({"detail": "Пароль изменён."})


class MeView(APIView):
    """Profile read + edit (ТЗ 3.11). GET returns the current user; PATCH edits
    the editable fields (name, phone) — email/login are identity and not editable."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(UserSerializer(request.user).data)

    def patch(self, request):
        serializer = ProfileUpdateSerializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        audit.log_event("profile_updated", request=request, user=request.user)
        return Response(UserSerializer(request.user).data)


# --------------------------------------------------------------------------- #
#  Linked socials + active sessions (ТЗ Этап 3.11)
# --------------------------------------------------------------------------- #
class SocialAccountsView(APIView):
    """List the user's linked social account(s) and allow unlinking.

    The client table stores a single social link (``social_provider``/``social_id``),
    so the list is 0 or 1 entry. Unlinking is refused for social-only accounts with
    no usable password — otherwise the user would lock themselves out."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        u = request.user
        linked = (
            [{"provider": u.social_provider, "social_id": u.social_id}]
            if u.social_provider else []
        )
        return Response({"linked": linked, "has_password": u.has_usable_password()})

    def delete(self, request):
        u = request.user
        if not u.social_provider:
            return Response({"detail": "Соц-сеть не привязана."}, status=status.HTTP_400_BAD_REQUEST)
        if not u.has_usable_password():
            return Response(
                {"detail": "Сначала задайте пароль — иначе вход будет невозможен."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        provider = u.social_provider
        u.social_provider = None
        u.social_id = None
        u.save(update_fields=["social_provider", "social_id"])
        audit.log_event("social_unlinked", request=request, user=u, provider=provider)
        return Response({"detail": "Соц-сеть отвязана."})


class SessionsView(APIView):
    """List active sessions (outstanding, non-blacklisted refresh tokens) and let
    the user revoke all *other* sessions ("log out everywhere else", ТЗ 3.11)."""

    permission_classes = [IsAuthenticated]

    def _active(self, user):
        from django.utils import timezone
        revoked = BlacklistedToken.objects.values_list("token_id", flat=True)
        return (
            OutstandingToken.objects.filter(user=user, expires_at__gt=timezone.now())
            .exclude(id__in=revoked)
            .order_by("-created_at")
        )

    def get(self, request):
        sessions = [
            {"jti": t.jti, "created_at": t.created_at, "expires_at": t.expires_at}
            for t in self._active(request.user)
        ]
        return Response({"sessions": sessions})

    def delete(self, request):
        """Revoke every active session for the user (blacklist all refresh tokens)."""
        count = 0
        for token in self._active(request.user):
            _, created = BlacklistedToken.objects.get_or_create(token=token)
            count += int(created)
        audit.log_event("sessions_revoked", request=request, user=request.user, count=count)
        return Response({"detail": "Все сессии завершены.", "revoked": count})


def _decode_uid_pk(pk):
    try:
        return User.objects.get(pk=pk)
    except (User.DoesNotExist, ValueError, TypeError):
        return None


# --------------------------------------------------------------------------- #
#  2FA / TOTP (ТЗ Этап 3.12)
# --------------------------------------------------------------------------- #
class TwoFactorSetupView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        TOTPDevice.objects.filter(user=request.user, confirmed=False).delete()
        device = TOTPDevice.objects.create(user=request.user, name="default", confirmed=False)
        secret = base64.b32encode(binascii.unhexlify(device.key)).decode()
        return Response({"otpauth_url": device.config_url, "secret": secret})


class TwoFactorConfirmView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = OTPSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        device = TOTPDevice.objects.filter(user=request.user, confirmed=False).first()
        if device is None:
            return Response({"detail": "Сначала вызовите setup."}, status=status.HTTP_400_BAD_REQUEST)
        if not device.verify_token(serializer.validated_data["otp"]):
            return Response({"detail": "Неверный код."}, status=status.HTTP_400_BAD_REQUEST)
        device.confirmed = True
        device.save(update_fields=["confirmed"])
        # keep a single confirmed device
        TOTPDevice.objects.filter(user=request.user, confirmed=True).exclude(pk=device.pk).delete()
        audit.log_event("2fa_enabled", request=request, user=request.user)
        return Response({"detail": "2FA включена."})


class TwoFactorDisableView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = OTPSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        device = TOTPDevice.objects.filter(user=request.user, confirmed=True).first()
        if device is None:
            return Response({"detail": "2FA не включена."}, status=status.HTTP_400_BAD_REQUEST)
        if not device.verify_token(serializer.validated_data["otp"]):
            return Response({"detail": "Неверный код."}, status=status.HTTP_400_BAD_REQUEST)
        TOTPDevice.objects.filter(user=request.user).delete()
        audit.log_event("2fa_disabled", request=request, user=request.user)
        return Response({"detail": "2FA отключена."})


class TwoFactorStatusView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        enabled = TOTPDevice.objects.filter(user=request.user, confirmed=True).exists()
        return Response({"enabled": enabled})


# --------------------------------------------------------------------------- #
#  OAuth (ТЗ Этап 3.5): Google (authorization-code) + Telegram (Login Widget)
# --------------------------------------------------------------------------- #
class GoogleLoginView(APIView):
    """Redirect the browser to Google's consent screen."""

    permission_classes = [AllowAny]

    def get(self, request):
        if not settings.GOOGLE_CLIENT_ID:
            return Response({"detail": "Google OAuth не настроен."}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        state = get_random_string(32)
        request.session["google_oauth_state"] = state
        return redirect(oauth.google_auth_url(state))


class GoogleCallbackView(APIView):
    """Exchange the code, merge by verified email, set the refresh cookie and
    bounce back to the frontend (which then calls token/refresh for the access)."""

    permission_classes = [AllowAny]

    def get(self, request):
        if request.query_params.get("error"):
            return redirect(f"{settings.FRONTEND_URL}/auth/callback?error=denied")
        code = request.query_params.get("code", "")
        state = request.query_params.get("state", "")
        saved = request.session.pop("google_oauth_state", None)
        if not code or not saved or not constant_time_compare(state, saved):
            return Response({"detail": "Некорректный OAuth-ответ."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            profile = oauth.google_exchange(code)
        except Exception:  # noqa: BLE001 — upstream/network failure
            return Response({"detail": "Не удалось получить профиль Google."}, status=status.HTTP_502_BAD_GATEWAY)
        if not profile.get("email") or not profile["email_verified"]:
            return Response({"detail": "Google не подтвердил email."}, status=status.HTTP_400_BAD_REQUEST)
        user = oauth.link_or_create_by_email(profile["email"], profile["name"], PROVIDER_GOOGLE, profile["sub"])
        audit.log_event("oauth_login", request=request, user=user, provider=PROVIDER_GOOGLE)
        response = redirect(f"{settings.FRONTEND_URL}/auth/callback?status=ok")
        _set_refresh_cookie(response, RefreshToken.for_user(user))
        return response


class TelegramLoginView(APIView):
    """Verify Telegram Login Widget data (HMAC) and issue tokens."""

    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth"

    def post(self, request):
        if not settings.TELEGRAM_BOT_TOKEN:
            return Response({"detail": "Telegram-вход не настроен."}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        data = {k: str(v) for k, v in request.data.items()}
        if not oauth.verify_telegram(data, settings.TELEGRAM_BOT_TOKEN):
            return Response({"detail": "Подпись Telegram недействительна."}, status=status.HTTP_401_UNAUTHORIZED)
        try:
            if time.time() - int(data.get("auth_date", "0")) > 86400:
                return Response({"detail": "Данные Telegram устарели."}, status=status.HTTP_401_UNAUTHORIZED)
        except ValueError:
            return Response({"detail": "Некорректные данные."}, status=status.HTTP_400_BAD_REQUEST)
        name = " ".join(filter(None, [data.get("first_name"), data.get("last_name")]))
        user = oauth.get_or_create_social(PROVIDER_TELEGRAM, data["id"], name=name)
        audit.log_event("oauth_login", request=request, user=user, provider=PROVIDER_TELEGRAM)
        return _tokens_response(user, body_extra={"user": UserSerializer(user).data})


class VKLoginView(APIView):
    """Redirect the browser to the VK ID consent screen (OAuth 2.1 + PKCE)."""

    permission_classes = [AllowAny]

    def get(self, request):
        if not settings.VK_APP_ID:
            return Response({"detail": "VK-вход не настроен."}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        state = get_random_string(32)
        verifier, challenge = oauth.vk_pkce_pair()
        request.session["vk_oauth_state"] = state
        request.session["vk_oauth_verifier"] = verifier
        return redirect(oauth.vk_auth_url(state, challenge))


class VKCallbackView(APIView):
    """Exchange the code, key by VK id (merge by email when VK provides one),
    set the refresh cookie and bounce back to the frontend."""

    permission_classes = [AllowAny]

    def get(self, request):
        if request.query_params.get("error"):
            return redirect(f"{settings.FRONTEND_URL}/auth/callback?error=denied")
        code = request.query_params.get("code", "")
        state = request.query_params.get("state", "")
        # VK ID returns device_id on the callback; it is required for the token exchange.
        device_id = request.query_params.get("device_id", "")
        saved = request.session.pop("vk_oauth_state", None)
        verifier = request.session.pop("vk_oauth_verifier", None)
        if not code or not saved or not verifier or not constant_time_compare(state, saved):
            return Response({"detail": "Некорректный OAuth-ответ."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            profile = oauth.vk_exchange(code, verifier, device_id)
        except Exception:  # noqa: BLE001 — upstream/network failure
            return Response({"detail": "Не удалось получить профиль VK."}, status=status.HTTP_502_BAD_GATEWAY)
        user = oauth.get_or_create_social(
            PROVIDER_VK, profile["id"], email=profile.get("email"), name=profile["name"]
        )
        audit.log_event("oauth_login", request=request, user=user, provider=PROVIDER_VK)
        response = redirect(f"{settings.FRONTEND_URL}/auth/callback?status=ok")
        _set_refresh_cookie(response, RefreshToken.for_user(user))
        return response
