"""Yandex SmartCaptcha server-side verification (ТЗ Этап 3.8).

No-op when SMARTCAPTCHA_ENABLED is off (dev/tests). Fails closed on errors.
"""
import json
import logging
import urllib.parse
import urllib.request

from django.conf import settings

logger = logging.getLogger("apps.accounts.captcha")

VALIDATE_URL = "https://smartcaptcha.yandexcloud.net/validate"


def verify_captcha(token, ip=None):
    if not settings.SMARTCAPTCHA_ENABLED:
        return True
    if not token:
        logger.warning("captcha: пустой токен от клиента (ip=%s)", ip)
        return False
    params = {"secret": settings.SMARTCAPTCHA_SERVER_KEY, "token": token}
    if ip:
        params["ip"] = ip
    try:
        with urllib.request.urlopen(f"{VALIDATE_URL}?{urllib.parse.urlencode(params)}", timeout=5) as resp:
            data = json.loads(resp.read())
            if data.get("status") != "ok":
                logger.warning(
                    "captcha: Яндекс отклонил token (len=%s status=%s msg=%s ip=%s)",
                    len(token), data.get("status"), data.get("message"), ip,
                )
            return data.get("status") == "ok"
    except Exception as exc:  # noqa: BLE001 — fail closed
        logger.warning("captcha: ошибка обращения к Яндексу: %r", exc)
        return False
