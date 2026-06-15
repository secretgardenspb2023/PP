"""Очистка осиротевших файлов в S3 (ТЗ Этап 4.8).

Находит объекты в бакете под заданным префиксом, на которые НЕ ссылается ни одна
строка ``media.plant_photos`` (``storage_key``), и по флагу ``--delete`` удаляет их.
По умолчанию — dry-run: только показывает, что было бы удалено.

    python manage.py cleanup_orphans                 # dry-run, префикс plants/
    python manage.py cleanup_orphans --delete         # реально удалить
    python manage.py cleanup_orphans --prefix plants/ --limit 100
"""
import boto3
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from apps.catalog.models import PlantPhoto

BATCH = 1000  # S3 DeleteObjects принимает до 1000 ключей за вызов


class Command(BaseCommand):
    help = "Удаляет (с --delete) объекты S3 без ссылки из media.plant_photos. По умолчанию dry-run."

    def add_arguments(self, parser):
        parser.add_argument("--prefix", default="plants/", help="Префикс ключей в бакете (по умолчанию plants/).")
        parser.add_argument("--delete", action="store_true", help="Реально удалить (по умолчанию только показать).")
        parser.add_argument("--limit", type=int, default=0, help="Обработать не более N осиротевших (0 = все).")

    def handle(self, *args, **opts):
        if not (settings.AWS_ACCESS_KEY_ID and settings.AWS_STORAGE_BUCKET_NAME):
            raise CommandError("S3 не настроен (AWS_*). Запустите на сервере с доступами.")

        referenced = set(
            PlantPhoto.objects.exclude(storage_key__isnull=True)
            .exclude(storage_key="")
            .values_list("storage_key", flat=True)
        )
        bucket = settings.AWS_STORAGE_BUCKET_NAME
        s3 = boto3.client(
            "s3",
            endpoint_url=settings.AWS_S3_ENDPOINT_URL,
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_S3_REGION_NAME,
        )

        scanned, orphans = 0, []
        paginator = s3.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=bucket, Prefix=opts["prefix"]):
            for obj in page.get("Contents", []):
                scanned += 1
                if obj["Key"] not in referenced:
                    orphans.append(obj["Key"])

        targets = orphans[: opts["limit"]] if opts["limit"] else orphans
        for key in targets:
            self.stdout.write(("  удаляю " if opts["delete"] else "  [dry] ") + key)

        if opts["delete"] and targets:
            for i in range(0, len(targets), BATCH):
                chunk = targets[i:i + BATCH]
                s3.delete_objects(Bucket=bucket, Delete={"Objects": [{"Key": k} for k in chunk]})

        verb = "удалено" if opts["delete"] else "к удалению (dry-run)"
        self.stdout.write(self.style.SUCCESS(
            f"Просканировано {scanned}, в БД ссылок {len(referenced)}, "
            f"осиротевших {len(orphans)}, {verb} {len(targets)}"
        ))
