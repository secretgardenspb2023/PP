"""Миграция фото из media.tmp_donor_photos в S3 + media.plant_photos (ТЗ Этап 4).

Для каждой донорской записи (id_pp, raw_urls — ссылки через '|') скачивает
изображения по старым WP-ссылкам, заливает в S3 и создаёт строки media.plant_photos
с подписанными imgproxy-URL (WebP/AVIF + подбор размера отдаёт imgproxy).

Идемпотентна: растения с уже загруженными фото пропускаются (если не --force).

    python manage.py migrate_photos [--limit N] [--plant-pp ID] [--dry-run] [--force]
"""
import hashlib
import urllib.parse
import urllib.request

import boto3
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import connection

from apps.catalog import imgproxy
from apps.catalog.models import PlantPhoto

UA = "PoiskPlantPhotoMigrator/1.0"
EXT_BY_CT = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/gif": ".gif",
}


class Command(BaseCommand):
    help = "Мигрирует фото из media.tmp_donor_photos в S3 + media.plant_photos (imgproxy)."

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=0, help="Обработать не более N донорских записей.")
        parser.add_argument("--plant-pp", type=int, help="Только один донорский id_pp (для теста).")
        parser.add_argument("--timeout", type=int, default=20, help="Таймаут скачивания, сек.")
        parser.add_argument("--dry-run", action="store_true", help="Ничего не качать/не писать — только показать план.")
        parser.add_argument("--force", action="store_true", help="Перезаливать даже если у растения уже есть фото.")

    def handle(self, *args, **opts):
        if not opts["dry_run"] and not (settings.AWS_ACCESS_KEY_ID and settings.AWS_STORAGE_BUCKET_NAME):
            raise CommandError("S3 не настроен (AWS_*). Запустите на сервере с доступами или с --dry-run.")

        pp_to_plant = self._plant_map()
        donors = self._donor_rows(opts.get("plant_pp"), opts["limit"])
        self.stdout.write(f"Донорских записей к обработке: {len(donors)}; растений в маппинге: {len(pp_to_plant)}")

        s3 = None
        if not opts["dry_run"]:
            s3 = boto3.client(
                "s3",
                endpoint_url=settings.AWS_S3_ENDPOINT_URL,
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                region_name=settings.AWS_S3_REGION_NAME,
            )

        stats = {"plants": 0, "skipped_no_plant": 0, "skipped_existing": 0, "uploaded": 0, "errors": 0}
        for id_pp, raw_urls in donors:
            plant_id = pp_to_plant.get(id_pp)
            if not plant_id:
                stats["skipped_no_plant"] += 1
                continue
            if not opts["force"] and PlantPhoto.objects.filter(plant_id=plant_id).exists():
                stats["skipped_existing"] += 1
                continue

            urls = [u.strip() for u in raw_urls.split("|") if u.strip()]
            uploaded_here = 0
            for i, url in enumerate(urls):
                key = self._key(plant_id, i, url)
                if opts["dry_run"]:
                    self.stdout.write(f"  [dry] plant {plant_id} <= {url}  ->  {key}")
                    stats["uploaded"] += 1
                    continue
                try:
                    data, content_type = self._download(url, opts["timeout"])
                    key = self._key(plant_id, i, url, content_type)
                    s3.put_object(Bucket=settings.AWS_STORAGE_BUCKET_NAME, Key=key, Body=data, ContentType=content_type)
                    PlantPhoto.objects.create(
                        plant_id=plant_id,
                        storage_key=key,
                        public_url=imgproxy.full(key),
                        preview_url=imgproxy.thumb(key),
                        is_main=(uploaded_here == 0),
                        source_type="donor",
                    )
                    stats["uploaded"] += 1
                    uploaded_here += 1
                except Exception as exc:  # noqa: BLE001 — продолжаем по остальным
                    stats["errors"] += 1
                    self.stderr.write(f"  ! plant {plant_id}: {url} — {exc.__class__.__name__}: {exc}")
            if uploaded_here or opts["dry_run"]:
                stats["plants"] += 1

        self.stdout.write(self.style.SUCCESS(
            "Готово: растений {plants}, фото {uploaded}, "
            "пропущено (нет растения) {skipped_no_plant}, (уже есть) {skipped_existing}, ошибок {errors}".format(**stats)
        ))

    # ---- helpers ----
    @staticmethod
    def _plant_map():
        with connection.cursor() as cur:
            cur.execute("SELECT id_pp, id_plant FROM plant.plants WHERE id_pp IS NOT NULL")
            return {pp: pid for pp, pid in cur.fetchall()}

    @staticmethod
    def _donor_rows(plant_pp, limit):
        sql = "SELECT id_pp, raw_urls FROM media.tmp_donor_photos WHERE raw_urls IS NOT NULL AND raw_urls <> ''"
        params = []
        if plant_pp:
            sql += " AND id_pp = %s"
            params.append(plant_pp)
        sql += " ORDER BY id_pp"
        if limit:
            sql += " LIMIT %s"
            params.append(limit)
        with connection.cursor() as cur:
            cur.execute(sql, params)
            return cur.fetchall()

    @staticmethod
    def _download(url, timeout):
        safe = urllib.parse.quote(url, safe=":/?&=#%+")
        req = urllib.request.Request(safe, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310
            return resp.read(), (resp.headers.get_content_type() or "image/jpeg")

    @staticmethod
    def _key(plant_id, index, url, content_type=None):
        ext = EXT_BY_CT.get(content_type or "", "")
        if not ext:
            tail = urllib.parse.urlparse(url).path.rsplit(".", 1)
            ext = "." + tail[1].lower() if len(tail) == 2 and len(tail[1]) <= 4 else ".jpg"
        digest = hashlib.sha1(url.encode()).hexdigest()[:10]  # noqa: S324
        return f"plants/{plant_id}/{index + 1}-{digest}{ext}"
