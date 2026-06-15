"""Auth-event logging (ТЗ Этап 3.10).

A single structured logger for security-relevant account events: logins (success/
failure/lockout), logout, registration, email confirmation, password resets, social
links and 2FA changes. Records go to the ``apps.accounts.audit`` logger → console,
which the prod stack ships to Docker's json-file logs (rotated). Keeping it as plain
logging (not a DB table) avoids extra schema on the client-owned ``user_info`` and is
enough for the audit trail required at this stage.
"""
import logging

logger = logging.getLogger("apps.accounts.audit")


def client_ip(request):
    if request is None:
        return None
    xff = request.META.get("HTTP_X_FORWARDED_FOR")
    return xff.split(",")[0].strip() if xff else request.META.get("REMOTE_ADDR")


def log_event(event, *, request=None, user=None, **extra):
    """Emit one structured auth-event line: ``event=… user=… ip=… key=value``."""
    parts = [f"event={event}"]
    if user is not None:
        parts.append(f"user={getattr(user, 'email', user)}")
    ip = client_ip(request)
    if ip:
        parts.append(f"ip={ip}")
    parts.extend(f"{k}={v}" for k, v in extra.items() if v is not None)
    logger.info(" ".join(parts))
