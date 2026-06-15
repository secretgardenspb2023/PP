"""imgproxy URL builder (ТЗ Этап 4).

Produces HMAC-signed imgproxy URLs served through nginx `/img/`. No format is
forced in the URL, so imgproxy negotiates WebP/AVIF from the Accept header
(IMGPROXY_ENABLE_WEBP/AVIF_DETECTION are on in the prod compose).
"""
import base64
import hashlib
import hmac

from django.conf import settings


def _b64(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def s3_source(key: str) -> str:
    return f"s3://{settings.AWS_STORAGE_BUCKET_NAME}/{key}"


def imgproxy_url(source: str, processing: str) -> str:
    """Signed URL for `source` with a processing-options string like
    ``rs:fit:1600:1600:0/q:82``. Falls back to /insecure when no key is set."""
    enc = _b64(source.encode())
    path = f"/{processing}/{enc}"
    base = settings.IMGPROXY_PUBLIC_PATH.rstrip("/")
    key, salt = settings.IMGPROXY_KEY, settings.IMGPROXY_SALT
    if not (key and salt):
        return f"{base}/insecure{path}"
    digest = hmac.new(bytes.fromhex(key), bytes.fromhex(salt) + path.encode(), hashlib.sha256).digest()
    return f"{base}/{_b64(digest)}{path}"


# Catalog presets (ТЗ 4.6): thumbnail 200 / card 400 / full 1200 / hero 2000.
# `fit` keeps aspect (detail/hero), `fill` crops to a fixed box (grid thumbs);
# quality tuned for plant photos. WebP/AVIF is negotiated by imgproxy via Accept.
def thumbnail(key: str) -> str:
    """200px square thumbnail (lists, admin previews)."""
    return imgproxy_url(s3_source(key), "rs:fill:200:200:0/q:75")


def card(key: str) -> str:
    """400px card image for the catalog grid (4:3-ish, cropped to fill)."""
    return imgproxy_url(s3_source(key), "rs:fill:400:300:0/q:78")


def full(key: str) -> str:
    """1200px image for the plant card page."""
    return imgproxy_url(s3_source(key), "rs:fit:1200:1200:0/q:82")


def hero(key: str) -> str:
    """2000px hero image."""
    return imgproxy_url(s3_source(key), "rs:fit:2000:2000:0/q:82")


# Backward-compatible alias: existing callers (migrate_photos / serializers) use
# `thumb` for the grid preview, which is now the `card` preset.
def thumb(key: str) -> str:
    return card(key)
