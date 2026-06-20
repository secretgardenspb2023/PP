"""OAuth helpers: Google (authorization-code) + Telegram (Login Widget HMAC).

No third-party deps — plain urllib + hmac. Account merging follows ТЗ 3.6:
join by a *verified* provider email; Telegram (no email) keys by social id.
"""
import base64
import hashlib
import hmac
import json
import os
import urllib.parse
import urllib.request

from django.conf import settings
from django.contrib.auth import get_user_model

User = get_user_model()

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"

# VK ID (OAuth 2.1 + PKCE). The legacy oauth.vk.com flow was retired by VK and
# now answers any authorize request with `{"error":"invalid_request",
# "error_description":"Security Error"}`, so the whole VK login goes through id.vk.com.
VK_AUTH_URL = "https://id.vk.com/authorize"
VK_TOKEN_URL = "https://id.vk.com/oauth2/auth"
VK_USERINFO_URL = "https://id.vk.com/oauth2/user_info"


def google_auth_url(state):
    params = {
        "client_id": settings.GOOGLE_CLIENT_ID,
        "redirect_uri": settings.GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
        "access_type": "online",
        "prompt": "select_account",
    }
    return f"{GOOGLE_AUTH_URL}?{urllib.parse.urlencode(params)}"


def _post_form(url, data):
    req = urllib.request.Request(
        url,
        data=urllib.parse.urlencode(data).encode(),
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read())


def _get_json(url, bearer):
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {bearer}"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read())


def google_exchange(code):
    """Exchange an authorization code for the Google profile."""
    tokens = _post_form(
        GOOGLE_TOKEN_URL,
        {
            "code": code,
            "client_id": settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "redirect_uri": settings.GOOGLE_REDIRECT_URI,
            "grant_type": "authorization_code",
        },
    )
    info = _get_json(GOOGLE_USERINFO_URL, tokens["access_token"])
    return {
        "sub": info["sub"],
        "email": info.get("email"),
        "email_verified": bool(info.get("email_verified")),
        "name": info.get("name", ""),
    }


def _b64url(raw):
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def vk_pkce_pair():
    """Return (code_verifier, code_challenge) for VK ID PKCE (method S256).

    The verifier (~86 url-safe chars, within the RFC 7636 43–128 range) is kept
    in the session; only the SHA-256 challenge travels to VK on the authorize step.
    """
    verifier = _b64url(os.urandom(64))
    challenge = _b64url(hashlib.sha256(verifier.encode()).digest())
    return verifier, challenge


def vk_auth_url(state, code_challenge):
    params = {
        "client_id": settings.VK_APP_ID,
        "redirect_uri": settings.VK_REDIRECT_URI,
        "response_type": "code",
        "scope": "email",
        "state": state,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
    }
    return f"{VK_AUTH_URL}?{urllib.parse.urlencode(params)}"


def vk_exchange(code, code_verifier, device_id):
    """Exchange a VK ID authorization code (OAuth 2.1 + PKCE) for the profile.

    PKCE replaces the client secret: the token call is authenticated by the
    code_verifier + device_id (both bound to the authorize step). Email comes
    back from user_info only when the `email` scope was granted and the account
    has one — otherwise we key by VK id (см. get_or_create_social).
    """
    token = _post_form(
        VK_TOKEN_URL,
        {
            "grant_type": "authorization_code",
            "code": code,
            "code_verifier": code_verifier,
            "client_id": settings.VK_APP_ID,
            "device_id": device_id,
            "redirect_uri": settings.VK_REDIRECT_URI,
        },
    )
    access_token = token["access_token"]
    uid = token.get("user_id")
    # VK ID отдаёт email (и phone) обычно прямо в ответе на обмен токена, когда
    # пользователь выдал scope email; user_info — запасной источник.
    email, name = token.get("email"), ""
    try:
        info = _post_form(
            VK_USERINFO_URL,
            {"client_id": settings.VK_APP_ID, "access_token": access_token},
        )
        u = info["user"]
        uid = u.get("user_id", uid)
        email = email or u.get("email")
        name = " ".join(filter(None, [u.get("first_name"), u.get("last_name")]))
    except Exception:  # noqa: BLE001 — email/name are optional
        pass
    return {"id": str(uid), "email": email, "name": name}


def verify_telegram(data, bot_token):
    """Validate Telegram Login Widget payload (HMAC-SHA256 with sha256(bot_token))."""
    received = data.get("hash", "")
    check_string = "\n".join(
        f"{k}={data[k]}" for k in sorted(data) if k != "hash"
    )
    secret = hashlib.sha256(bot_token.encode()).digest()
    digest = hmac.new(secret, check_string.encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(digest, received)


def link_or_create_by_email(email, name, provider, social_id):
    """Merge by verified email, else create (ТЗ 3.6)."""
    user = User.objects.filter(email__iexact=email).first()
    if user is None:
        user = User.objects.create_user(email=email, full_name=name, is_active=True)
    if not user.social_id:
        user.social_provider = provider
        user.social_id = str(social_id)
        user.save(update_fields=["social_provider", "social_id"])
    return user


def get_or_create_social(provider, social_id, *, email=None, name=""):
    """Key by (provider, social_id); fall back to a synthetic email when the
    provider gives none (Telegram)."""
    user = User.objects.filter(social_provider=provider, social_id=str(social_id)).first()
    if user is not None:
        return user
    if email:
        return link_or_create_by_email(email, name, provider, social_id)
    return User.objects.create_user(
        email=f"{provider}-{social_id}@social.poiskplant.ru",
        full_name=name,
        is_active=True,
        social_provider=provider,
        social_id=str(social_id),
    )
