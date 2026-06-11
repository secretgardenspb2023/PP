"""Yandex SmartCaptcha server-side verification (ТЗ Этап 3.8).

No-op when SMARTCAPTCHA_ENABLED is off (dev/tests). Fails closed on errors.
"""
import json
import urllib.parse
import urllib.request

from django.conf import settings

VALIDATE_URL = "https://smartcaptcha.yandexcloud.net/validate"


def verify_captcha(token, ip=None):
    if not settings.SMARTCAPTCHA_ENABLED:
        return True
    if not token:
        return False
    params = {"secret": settings.SMARTCAPTCHA_SERVER_KEY, "token": token}
    if ip:
        params["ip"] = ip
    try:
        with urllib.request.urlopen(f"{VALIDATE_URL}?{urllib.parse.urlencode(params)}", timeout=5) as resp:
            return json.loads(resp.read()).get("status") == "ok"
    except Exception:  # noqa: BLE001 — fail closed
        return False
