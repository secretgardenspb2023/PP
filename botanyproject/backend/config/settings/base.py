"""Base settings shared across dev / staging / prod (ТЗ Этап 2.1)."""
from datetime import timedelta
from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parents[2]

env = environ.Env(
    DJANGO_DEBUG=(bool, False),
)
# Local .env (ignored in Docker, where vars come from env_file). Harmless if absent.
environ.Env.read_env(BASE_DIR / ".env")

# ---- Core ----
SECRET_KEY = env("DJANGO_SECRET_KEY", default="insecure-dev-key-change-me")
DEBUG = env.bool("DJANGO_DEBUG", default=False)
ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS", default=["localhost", "127.0.0.1"])

DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]
THIRD_PARTY_APPS = [
    "rest_framework",
    "rest_framework_simplejwt.token_blacklist",
    "corsheaders",
    "drf_spectacular",
    "axes",
    "django_otp",
    "django_otp.plugins.otp_totp",
]
LOCAL_APPS = [
    "apps.core",
    "apps.accounts",
    "apps.catalog",
]
INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django_otp.middleware.OTPMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    # AxesMiddleware must be last (handles the lockout response).
    "axes.middleware.AxesMiddleware",
]

# Axes runs first (lockout check), then the normal model backend (ТЗ 3.7).
AUTHENTICATION_BACKENDS = [
    "axes.backends.AxesStandaloneBackend",
    "django.contrib.auth.backends.ModelBackend",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

# ---- Database (django-environ reads DATABASE_URL) ----
DATABASES = {"default": env.db("DATABASE_URL")}
DATABASES["default"]["CONN_MAX_AGE"] = env.int("DB_CONN_MAX_AGE", default=60)

AUTH_USER_MODEL = "accounts.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# ---- Cache / Redis ----
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": env("REDIS_URL", default="redis://redis:6379/0"),
    }
}

# ---- Celery ----
CELERY_BROKER_URL = env("CELERY_BROKER_URL", default="redis://redis:6379/1")
CELERY_RESULT_BACKEND = env("CELERY_RESULT_BACKEND", default="redis://redis:6379/2")
CELERY_TASK_TIME_LIMIT = 300
CELERY_TASK_SOFT_TIME_LIMIT = 240

# ---- Elasticsearch (ТЗ Этап 5) ----
ELASTICSEARCH_URL = env("ELASTICSEARCH_URL", default="http://elasticsearch:9200")

# ---- DRF + OpenAPI ----
REST_FRAMEWORK = {
    # JWT-only. SessionAuthentication убран намеренно: при открытой сессии Django-
    # админки он включал CSRF-проверку на cookie-эндпоинтах (token/refresh, login,
    # соц-вход) → 403 «CSRF Failed» и не завершался вход. API авторизуется Bearer-JWT.
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 24,
    "DEFAULT_VERSIONING_CLASS": "rest_framework.versioning.NamespaceVersioning",
    "DEFAULT_VERSION": "v1",
    "ALLOWED_VERSIONS": ["v1"],
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": "60/min", "user": "240/min", "auth": "10/min", "reviews": "10/hour",
    },
}

SPECTACULAR_SETTINGS = {
    "TITLE": "PoiskPlant API",
    "DESCRIPTION": "API электронного справочника растений PoiskPlant.",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "SCHEMA_PATH_PREFIX": r"/api/v[0-9]+",
}

# ---- JWT auth (ТЗ Этап 3.4: access-токен + refresh в HttpOnly cookie) ----
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=15),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=14),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "AUTH_HEADER_TYPES": ("Bearer",),
}
# Refresh token lives in an HttpOnly cookie scoped to the auth endpoints.
AUTH_REFRESH_COOKIE = "refresh_token"
AUTH_REFRESH_COOKIE_PATH = "/api/v1/auth/"
AUTH_REFRESH_COOKIE_SAMESITE = "Lax"
AUTH_REFRESH_COOKIE_SECURE = env.bool("AUTH_COOKIE_SECURE", default=not DEBUG)
# Base URL the frontend uses in verification / password-reset emails.
FRONTEND_URL = env("FRONTEND_URL", default="http://localhost:3000")

# ---- Brute-force protection (ТЗ Этап 3.7) ----
AXES_FAILURE_LIMIT = env.int("AXES_FAILURE_LIMIT", default=5)
AXES_COOLOFF_TIME = env.int("AXES_COOLOFF_HOURS", default=1)  # hours
AXES_RESET_ON_SUCCESS = True
AXES_LOCKOUT_PARAMETERS = [["username", "ip_address"]]
AXES_ENABLE_ACCESS_FAILURE_LOG = True
# Read the username from the authenticate() credentials (JSON body → request.POST is empty).
AXES_USERNAME_CALLABLE = "apps.accounts.axes_utils.get_username"

# ---- 2FA / TOTP for staff (ТЗ Этап 3.12) ----
OTP_TOTP_ISSUER = "PoiskPlant"

# ---- OAuth providers (ТЗ Этап 3.5) ----
GOOGLE_CLIENT_ID = env("GOOGLE_CLIENT_ID", default="")
GOOGLE_CLIENT_SECRET = env("GOOGLE_CLIENT_SECRET", default="")
GOOGLE_REDIRECT_URI = env(
    "GOOGLE_REDIRECT_URI", default="http://localhost:8000/api/v1/auth/google/callback/"
)
TELEGRAM_BOT_TOKEN = env("TELEGRAM_BOT_TOKEN", default="")
TELEGRAM_BOT_USERNAME = env("TELEGRAM_BOT_USERNAME", default="")
VK_APP_ID = env("VK_APP_ID", default="")
VK_SECURE_KEY = env("VK_SECURE_KEY", default="")
VK_SERVICE_TOKEN = env("VK_SERVICE_TOKEN", default="")
VK_REDIRECT_URI = env(
    "VK_REDIRECT_URI", default="http://localhost:8000/api/v1/auth/vk/callback/"
)

# ---- Yandex SmartCaptcha (ТЗ Этап 3.8) ----
SMARTCAPTCHA_SERVER_KEY = env("SMARTCAPTCHA_SERVER_KEY", default="")
# Off by default so dev/tests aren't blocked; turn on in prod via env.
SMARTCAPTCHA_ENABLED = env.bool("SMARTCAPTCHA_ENABLED", default=False)

# ---- CORS ----
CORS_ALLOWED_ORIGINS = env.list("CORS_ALLOWED_ORIGINS", default=[])
CORS_ALLOW_CREDENTIALS = True

# ---- Media / S3 (ТЗ Этап 4) ----
AWS_ACCESS_KEY_ID = env("AWS_ACCESS_KEY_ID", default="")
AWS_SECRET_ACCESS_KEY = env("AWS_SECRET_ACCESS_KEY", default="")
AWS_STORAGE_BUCKET_NAME = env("AWS_STORAGE_BUCKET_NAME", default="")
AWS_S3_ENDPOINT_URL = env("AWS_S3_ENDPOINT_URL", default="https://storage.yandexcloud.net")
AWS_S3_REGION_NAME = env("AWS_S3_REGION_NAME", default="ru-central1")

# ---- imgproxy (HMAC-signed URLs, served via nginx /img/) ----
IMGPROXY_KEY = env("IMGPROXY_KEY", default="")
IMGPROXY_SALT = env("IMGPROXY_SALT", default="")
# Public path prefix the browser hits; nginx /img/ proxies to the imgproxy container.
IMGPROXY_PUBLIC_PATH = env("IMGPROXY_PUBLIC_PATH", default="/img")

STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}
if AWS_ACCESS_KEY_ID and AWS_STORAGE_BUCKET_NAME:
    STORAGES["default"] = {
        "BACKEND": "storages.backends.s3.S3Storage",
        "OPTIONS": {
            "bucket_name": AWS_STORAGE_BUCKET_NAME,
            "endpoint_url": AWS_S3_ENDPOINT_URL,
            "region_name": AWS_S3_REGION_NAME,
            "default_acl": None,
            "querystring_auth": True,
        },
    }

# ---- Email (Yandex Mail for domain SMTP, ТЗ Этап 3) ----
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = env("EMAIL_HOST", default="smtp.yandex.ru")
EMAIL_PORT = env.int("EMAIL_PORT", default=465)
EMAIL_USE_SSL = env.bool("EMAIL_USE_SSL", default=True)
EMAIL_HOST_USER = env("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", default="")
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default="PoiskPlant <noreply@poiskplant.ru>")

# ---- i18n ----
LANGUAGE_CODE = "ru-ru"
TIME_ZONE = "Europe/Moscow"
USE_I18N = True
USE_TZ = True

# ---- Static ----
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ---- Logging (JSON-friendly console for Docker, ТЗ Этап 2.6) ----
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {"format": "%(asctime)s %(levelname)s %(name)s %(message)s"},
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "verbose"},
    },
    "root": {"handlers": ["console"], "level": env("DJANGO_LOG_LEVEL", default="INFO")},
}
