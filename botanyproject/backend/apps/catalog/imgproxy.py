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


# Catalog presets. fit keeps aspect; quality tuned for plant photos.
def full(key: str) -> str:
    """Large image for the plant card page."""
    return imgproxy_url(s3_source(key), "rs:fit:1600:1600:0/q:82")


def thumb(key: str) -> str:
    """Card thumbnail (4:3-ish), cropped to fill."""
    return imgproxy_url(s3_source(key), "rs:fill:600:450:0/q:78")
