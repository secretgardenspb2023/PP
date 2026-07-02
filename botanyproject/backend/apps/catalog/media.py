"""Загрузка изображений пользователей (фото отзывов) в S3 + imgproxy-URL.

Повторяет схему migrate_photos: кладём байты в S3 под уникальным ключом, отдаём
подписанные imgproxy-URL (full для просмотра, thumb для превью). Используется
вьюхой создания отзыва.
"""
import os
import urllib.request
import uuid
from urllib.parse import quote, urlsplit, urlunsplit

import boto3
from django.conf import settings

_UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
       "(KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36")
_EXT_CT = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png",
           ".webp": "image/webp", ".gif": "image/gif"}

ALLOWED_CT = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/gif": ".gif",
}
MAX_BYTES = 8 * 1024 * 1024  # 8 МБ на файл (фото карточки в админке)
REVIEW_MAX_BYTES = 1 * 1024 * 1024  # 1 МБ на фото в отзыве (согласовано с заказчицей)


def _s3():
    return boto3.client(
        "s3",
        endpoint_url=settings.AWS_S3_ENDPOINT_URL,
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name=settings.AWS_S3_REGION_NAME,
    )


def upload_image(data: bytes, content_type: str, *, prefix: str = "reviews",
                 max_bytes: int = MAX_BYTES) -> str:
    """Залить картинку в S3, вернуть storage_key. Бросает ValueError при неверном типе/размере.
    max_bytes задаёт лимит размера (по умолчанию 8 МБ; для отзывов передаётся REVIEW_MAX_BYTES)."""
    ext = ALLOWED_CT.get(content_type)
    if ext is None:
        raise ValueError("Неподдерживаемый тип файла (нужно изображение).")
    if len(data) > max_bytes:
        raise ValueError(f"Файл слишком большой (макс. {max_bytes // (1024 * 1024)} МБ).")
    key = f"{prefix}/{uuid.uuid4().hex}{ext}"
    _s3().put_object(
        Bucket=settings.AWS_STORAGE_BUCKET_NAME, Key=key, Body=data, ContentType=content_type
    )
    return key


def download_image(url: str, *, timeout: int = 30) -> tuple[bytes, str]:
    """Скачать картинку по URL → (bytes, content_type). ValueError при ошибке.
    Тип/размер потом валидирует upload_image."""
    url = (url or "").strip()
    if not url.lower().startswith(("http://", "https://")):
        raise ValueError("нужна полная ссылка вида https://…")
    try:  # percent-кодируем не-ASCII путь (кириллич. имена файлов)
        url.encode("ascii")
    except UnicodeEncodeError:
        p = urlsplit(url)
        url = urlunsplit((p.scheme, p.netloc, quote(p.path), quote(p.query, safe="=&"), p.fragment))
    req = urllib.request.Request(url, headers={"User-Agent": _UA, "Accept": "*/*"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:  # noqa: S310
            data = r.read()
            ct = (r.headers.get("Content-Type") or "").split(";")[0].strip().lower()
    except Exception as exc:  # noqa: BLE001
        raise ValueError(f"не удалось скачать ({type(exc).__name__})") from exc
    if ct not in ALLOWED_CT:  # тип не пришёл/неверный — определяем по расширению
        ct = _EXT_CT.get(os.path.splitext(urlsplit(url).path)[1].lower(), ct)
    return data, ct
