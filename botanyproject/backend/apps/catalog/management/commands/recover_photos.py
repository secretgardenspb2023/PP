"""Восстановление потерянных фото карточек со СТАРОГО сайта (old.poiskplant.ru).

Источник — выгрузка каталога старого сайта (Directory-listings export), заранее
сматченная с карточками без фото в `recover_map.csv` (колонки: id_plant, name_rus,
permalink). Команда заходит на каждую страницу старого сайта (обязателен браузерный
User-Agent — хостинг режет не-браузерные запросы), достаёт фото карточки из слайдера
Directorist (`plasmaSliderTempImg`) или og:image, скачивает, кладёт в S3 (media.upload_image)
и создаёт PlantPhoto с imgproxy-URL и source_type="old-site".

Идемпотентна: карточки, у которых уже есть фото, пропускаются (можно гонять батчами).
Устойчива: ошибка по одной карточке/фото логируется и не валит прогон.

    python manage.py recover_photos --csv /tmp/recover_map.csv [--limit N] [--dry-run]
"""
import csv
import os
import re
import time
import urllib.request
from urllib.parse import quote, urlsplit, urlunsplit

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.catalog import imgproxy, media
from apps.catalog.models import PlantPhoto

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36")
EXT_CT = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png",
          ".webp": "image/webp", ".gif": "image/gif"}
_SKIP_IMG = re.compile(r"cropped-|/logo|favicon|avatar|placeholder|no-?image|sprite", re.I)


def _enc(url):
    """Percent-кодируем не-ASCII (сырые кириллич. имена файлов). Уже-ASCII URL
    (в т.ч. заранее %-кодированные ссылки на страницы) не трогаем — иначе % → %25."""
    try:
        url.encode("ascii")
        return url
    except UnicodeEncodeError:
        p = urlsplit(url)
        return urlunsplit(
            (p.scheme, p.netloc, quote(p.path), quote(p.query, safe="=&"), p.fragment)
        )


def _get(url, timeout=30):
    req = urllib.request.Request(_enc(url), headers={"User-Agent": UA, "Accept": "*/*"})
    with urllib.request.urlopen(req, timeout=timeout) as r:  # noqa: S310
        return r.read(), (r.headers.get("Content-Type") or "")


def _extract(html):
    """Ссылки на фото карточки: ВСЯ галерея слайдера Directorist, иначе og:image.

    Галерея лежит в `<span class='plasmaSliderImageItem' data-src='...'>` (несколько
    кадров). Берём их все по порядку — цикл загрузки пропустит битые (404) и возьмёт
    живой кадр. Раньше читали только одну превью-картинку `plasmaSliderTempImg`, и если
    она оказывалась битой — карточка ошибочно считалась «без фото».
    """
    imgs = []
    for m in re.finditer(r"plasmaSliderImageItem[^>]*?data-src=['\"]([^'\"]+)['\"]", html, re.I):
        imgs.append(m.group(1))
    for m in re.finditer(r"<img[^>]*plasmaSliderTempImg[^>]*>", html, re.I):
        s = re.search(r"src=['\"]([^'\"]+)['\"]", m.group(0))
        if s:
            imgs.append(s.group(1))
    if not imgs:
        m = re.search(r"og:image['\"][^>]*content=['\"]([^'\"]+)['\"]", html, re.I)
        if m:
            imgs.append(m.group(1))
    out = []
    for u in imgs:
        u = u.split("?")[0].replace("https://poiskplant.ru/", "https://old.poiskplant.ru/")
        u = u.replace("http://poiskplant.ru/", "https://old.poiskplant.ru/")
        if _SKIP_IMG.search(u) or not u.lower().startswith("http"):
            continue
        if u not in out:
            out.append(u)
    return out


def _ct_for(url, header_ct):
    ext = os.path.splitext(url)[1].lower()
    if ext in EXT_CT:
        return EXT_CT[ext]
    hc = (header_ct or "").split(";")[0].strip().lower()
    return hc if hc in media.ALLOWED_CT else None


class Command(BaseCommand):
    help = "Восстановление фото карточек со старого сайта по recover_map.csv."

    def add_arguments(self, p):
        p.add_argument("--csv", default="/tmp/recover_map.csv")
        p.add_argument("--limit", type=int, default=0)
        p.add_argument("--max-photos", type=int, default=5)
        p.add_argument("--sleep", type=float, default=0.3, help="пауза между карточками, сек")
        p.add_argument("--dry-run", action="store_true", help="не писать в S3/БД, только считать")

    def handle(self, *args, **o):
        with open(o["csv"], encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        if o["limit"]:
            rows = rows[: o["limit"]]
        have = set(PlantPhoto.objects.values_list("plant_id", flat=True))
        total = len(rows)
        done = skipped = nophoto = failed = added = 0
        self.stdout.write(f"СТАРТ: {total} карточек, dry_run={o['dry_run']}")

        for i, row in enumerate(rows, 1):
            try:
                pid = int(float(row["id_plant"]))
            except (ValueError, KeyError):
                continue
            perm = (row.get("permalink") or "").strip()
            if pid in have:
                skipped += 1
                continue
            if not perm:
                nophoto += 1
                continue
            try:
                raw, _ = _get(perm)
                html = raw.decode("utf-8", "ignore")
            except Exception as e:  # noqa: BLE001
                failed += 1
                self.stderr.write(f"[{pid}] страница: {type(e).__name__} {e}")
                continue

            urls = _extract(html)[: o["max_photos"]]
            if not urls:
                nophoto += 1
                self.stdout.write(f"[{pid}] фото не найдено: {perm}")
                continue

            saved = 0
            for u in urls:
                try:
                    data, hct = _get(u)
                    ct = _ct_for(u, hct)
                    if not ct or len(data) < 1024:
                        continue
                    if o["dry_run"]:
                        saved += 1
                        continue
                    key = media.upload_image(data, ct, prefix=f"plants/{pid}")
                    PlantPhoto.objects.create(
                        plant_id=pid, storage_key=key,
                        public_url=imgproxy.full(key), preview_url=imgproxy.thumb(key),
                        source_type="old-site", is_main=(saved == 0),
                        created_at=timezone.now(),
                    )
                    saved += 1
                    added += 1
                except Exception as e:  # noqa: BLE001
                    self.stderr.write(f"[{pid}] фото {u}: {type(e).__name__} {e}")

            if saved:
                done += 1
                have.add(pid)
            else:
                nophoto += 1
            if i % 50 == 0:
                self.stdout.write(
                    f"...{i}/{total} карточек_с_фото={done} фото={added} "
                    f"без_фото={nophoto} ошибок={failed}"
                )
            time.sleep(o["sleep"])

        self.stdout.write(
            f"ГОТОВО: карточек_с_фото={done}, фото_добавлено={added}, "
            f"без_фото_на_странице={nophoto}, пропущено(уже_было)={skipped}, ошибок={failed}"
        )
