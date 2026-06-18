"""Email confirmation codes (OTP) kept in the Redis cache — no DB migration.

Replaces the old magic-link verification: register issues a 6-digit code,
the user types it on the site and VerifyEmailView checks it here.
"""
import secrets

from django.conf import settings
from django.core.cache import cache
from django.core.mail import send_mail
from django.utils.crypto import constant_time_compare

CODE_TTL = 15 * 60  # seconds the code stays valid
MAX_ATTEMPTS = 5    # wrong guesses before the code is burned


def _key(email):
    return f"email_verify:{email.strip().lower()}"


def issue_code(user):
    """Generate, store and email a fresh 6-digit code for the user."""
    code = f"{secrets.randbelow(1_000_000):06d}"
    cache.set(_key(user.email), {"code": code, "attempts": 0}, CODE_TTL)
    send_mail(
        "Код подтверждения PoiskPlant",
        f"Ваш код подтверждения: {code}\n\n"
        "Введите его на сайте, чтобы активировать аккаунт. "
        "Код действует 15 минут.",
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
    )
    return code


def check_code(email, code):
    """Return 'ok' | 'invalid' | 'expired' | 'too_many'."""
    key = _key(email)
    data = cache.get(key)
    if not data:
        return "expired"
    if data["attempts"] >= MAX_ATTEMPTS:
        cache.delete(key)
        return "too_many"
    if constant_time_compare(str(data["code"]), str(code or "").strip()):
        cache.delete(key)
        return "ok"
    data["attempts"] += 1
    cache.set(key, data, CODE_TTL)
    return "invalid"
