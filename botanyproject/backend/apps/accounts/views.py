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
from django.contrib.auth.tokens import default_token_generator
from django.core.exceptions import PermissionDenied
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
from rest_framework_simplejwt.tokens import RefreshToken

from . import captcha, oauth
from .serializers import (
    EmailVerifySerializer,
    LoginSerializer,
    OTPSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetSerializer,
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
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
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
        return Response({"detail": "Email подтверждён."})


class LoginView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth"

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            # Pass the underlying Django HttpRequest so django-axes can read the
            # client IP and record attempts (it does not understand DRF's Request).
            user = authenticate(
                getattr(request, "_request", request),
                username=serializer.validated_data["email"],
                password=serializer.validated_data["password"],
            )
        except PermissionDenied:  # django-axes lockout (ТЗ 3.7)
            return Response(
                {"detail": "Слишком много попыток входа. Попробуйте позже."},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )
        if user is None:
            return Response({"detail": "Неверный email или пароль."}, status=status.HTTP_401_UNAUTHORIZED)
        if not user.is_active:
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
                return Response({"detail": "Неверный код 2FA."}, status=status.HTTP_401_UNAUTHORIZED)

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
        return Response({"detail": "Пароль изменён."})


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(UserSerializer(request.user).data)


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
        user = oauth.link_or_create_by_email(profile["email"], profile["name"], "google", profile["sub"])
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
        user = oauth.get_or_create_social("telegram", data["id"], name=name)
        return _tokens_response(user, body_extra={"user": UserSerializer(user).data})
