"""Загрузка изображений пользователей (фото отзывов) в S3 + imgproxy-URL.

Повторяет схему migrate_photos: кладём байты в S3 под уникальным ключом, отдаём
подписанные imgproxy-URL (full для просмотра, thumb для превью). Используется
вьюхой создания отзыва.
"""
import uuid

import boto3
from django.conf import settings

ALLOWED_CT = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/gif": ".gif",
}
MAX_BYTES = 8 * 1024 * 1024  # 8 МБ на файл


def _s3():
    return boto3.client(
        "s3",
        endpoint_url=settings.AWS_S3_ENDPOINT_URL,
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name=settings.AWS_S3_REGION_NAME,
    )


def upload_image(data: bytes, content_type: str, *, prefix: str = "reviews") -> str:
    """Залить картинку в S3, вернуть storage_key. Бросает ValueError при неверном типе/размере."""
    ext = ALLOWED_CT.get(content_type)
    if ext is None:
        raise ValueError("Неподдерживаемый тип файла (нужно изображение).")
    if len(data) > MAX_BYTES:
        raise ValueError("Файл слишком большой (макс. 8 МБ).")
    key = f"{prefix}/{uuid.uuid4().hex}{ext}"
    _s3().put_object(
        Bucket=settings.AWS_STORAGE_BUCKET_NAME, Key=key, Body=data, ContentType=content_type
    )
    return key
