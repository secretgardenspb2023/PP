"""Staging settings — same hardening as prod.

Staging-specific behaviour (HTTP Basic Auth, noindex/no-follow, robots Disallow)
is enforced at the Nginx layer per ТЗ Этап 1.12, not in Django.
"""
from .prod import *  # noqa: F401,F403
from .prod import env

SENTRY_ENVIRONMENT = env("SENTRY_ENVIRONMENT", default="staging")
