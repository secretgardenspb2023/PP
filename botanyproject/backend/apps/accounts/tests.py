"""Unit tests for auth helpers (ТЗ Этап 3): OAuth URL/exchange parsing, Telegram
HMAC, and the audit logger. These are pure (no DB, no network) so they run in CI
without the client dump — the User model is bound to the unmanaged ``user_info.users``
table, so DB-backed auth tests need a loaded dump and run on staging instead.
"""
import hashlib
import hmac
import logging
from urllib.parse import parse_qs, urlparse

from django.test import override_settings

from apps.accounts import audit, oauth


# --------------------------------------------------------------------------- #
#  VK OAuth (ТЗ 3.5)
# --------------------------------------------------------------------------- #
@override_settings(VK_APP_ID="123456", VK_REDIRECT_URI="https://x.ru/api/v1/auth/vk/callback/")
def test_vk_auth_url_has_required_params():
    # VK ID (OAuth 2.1 + PKCE): authorize on id.vk.com with a code_challenge.
    url = oauth.vk_auth_url("state-token-xyz", "challenge-abc")
    parsed = urlparse(url)
    qs = parse_qs(parsed.query)
    assert parsed.netloc == "id.vk.com"
    assert qs["client_id"] == ["123456"]
    assert qs["redirect_uri"] == ["https://x.ru/api/v1/auth/vk/callback/"]
    assert qs["response_type"] == ["code"]
    assert qs["scope"] == ["email"]
    assert qs["state"] == ["state-token-xyz"]
    assert qs["code_challenge"] == ["challenge-abc"]
    assert qs["code_challenge_method"] == ["S256"]


def test_vk_exchange_parses_token_and_profile(monkeypatch):
    """vk_exchange (VK ID + PKCE) reads user_id from the token response and
    name+email from user_info."""
    calls = []

    def fake_post_form(url, data):
        calls.append(url)
        if url == oauth.VK_USERINFO_URL:
            return {"user": {"user_id": 777, "first_name": "Иван", "last_name": "Петров",
                             "email": "ivan@vk.example", "avatar": "https://vk/ava.jpg"}}
        # token endpoint
        return {"access_token": "tok", "user_id": 777}

    monkeypatch.setattr(oauth, "_post_form", fake_post_form)
    profile = oauth.vk_exchange("auth-code", "verifier", "device-id")
    assert profile == {"id": "777", "email": "ivan@vk.example", "name": "Иван Петров",
                       "avatar": "https://vk/ava.jpg"}
    assert len(calls) == 2  # token + user_info


def test_vk_exchange_without_email(monkeypatch):
    """When VK returns no email, the profile email is None (keyed by VK id later)."""
    def fake_post_form(url, data):
        if url == oauth.VK_USERINFO_URL:
            return {"user": {"user_id": 1, "first_name": "А", "last_name": ""}}
        return {"access_token": "tok", "user_id": 1}

    monkeypatch.setattr(oauth, "_post_form", fake_post_form)
    profile = oauth.vk_exchange("code", "verifier", "device-id")
    assert profile["id"] == "1"
    assert profile["email"] is None


# --------------------------------------------------------------------------- #
#  Telegram Login Widget signature (ТЗ 3.5)
# --------------------------------------------------------------------------- #
def _sign_telegram(data, bot_token):
    check = "\n".join(f"{k}={data[k]}" for k in sorted(data))
    secret = hashlib.sha256(bot_token.encode()).digest()
    return hmac.new(secret, check.encode(), hashlib.sha256).hexdigest()


def test_verify_telegram_accepts_valid_signature():
    data = {"id": "42", "first_name": "Foo", "auth_date": "1700000000"}
    data["hash"] = _sign_telegram(data, "bot-token")
    assert oauth.verify_telegram(data, "bot-token") is True


def test_verify_telegram_rejects_tampered_payload():
    data = {"id": "42", "first_name": "Foo", "auth_date": "1700000000"}
    data["hash"] = _sign_telegram(data, "bot-token")
    data["id"] = "43"  # tamper after signing
    assert oauth.verify_telegram(data, "bot-token") is False


# --------------------------------------------------------------------------- #
#  Audit logger (ТЗ 3.10)
# --------------------------------------------------------------------------- #
def test_audit_log_event_format(caplog):
    with caplog.at_level(logging.INFO, logger="apps.accounts.audit"):
        audit.log_event("login_success", user="a@b.ru", provider="VK")
    line = caplog.records[-1].getMessage()
    assert "event=login_success" in line
    assert "user=a@b.ru" in line
    assert "provider=VK" in line
