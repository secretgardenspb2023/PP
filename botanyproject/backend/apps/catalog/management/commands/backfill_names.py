"""Массовая (пере)генерация lat_name_unique / rus_name_unique с транскрипцией
сорта (ТЗ №2). По умолчанию DRY-RUN: ничего не пишет, печатает образцы.

    # посмотреть, что изменится в rus-именах (без записи):
    manage.py backfill_names --field rus
    # применить:
    manage.py backfill_names --field rus --apply
    # только пустые поля (безопасно дозаполнить новые карточки):
    manage.py backfill_names --field both --missing-only --apply

Транскрипция несовершенна — перед --apply на боевом ОБЯЗАТЕЛЬНО просмотреть образцы.
"""
from django.core.management.base import BaseCommand

from apps.catalog import models as m
from apps.catalog.naming import build_lat_name, build_rus_name


class Command(BaseCommand):
    help = "Пересборка lat/rus_name_unique с транскрипцией сорта (dry-run по умолчанию)."

    def add_arguments(self, parser):
        parser.add_argument("--apply", action="store_true", help="записать изменения (иначе dry-run)")
        parser.add_argument("--field", choices=["rus", "lat", "both"], default="rus")
        parser.add_argument("--missing-only", action="store_true", help="только если поле пустое")
        parser.add_argument("--limit", type=int, default=0, help="ограничить число карточек (тест)")
        parser.add_argument("--samples", type=int, default=40, help="сколько образцов печатать")

    def handle(self, *args, **o):
        do_rus = o["field"] in ("rus", "both")
        do_lat = o["field"] in ("lat", "both")
        qs = m.Plant.objects.select_related("species__genus").order_by("id_plant")
        if o["limit"]:
            qs = qs[: o["limit"]]

        total = changed = 0
        samples = []
        to_update = []
        for p in qs.iterator(chunk_size=1000):
            total += 1
            sp = p.species
            g = sp.genus if sp else None
            if g is None:
                continue
            dirty = False
            if do_lat:
                new_lat = build_lat_name(g.name, sp.name, p.variety)
                if new_lat and new_lat != (p.lat_name_unique or "") and not (o["missing_only"] and p.lat_name_unique):
                    if len(samples) < o["samples"]:
                        samples.append(f"[lat] #{p.id_plant}: {p.lat_name_unique!r} -> {new_lat!r}")
                    p.lat_name_unique = new_lat
                    dirty = True
            if do_rus:
                new_rus = build_rus_name(g.rus_name, sp.rus_name, p.variety)
                if new_rus and new_rus != (p.rus_name_unique or "") and not (o["missing_only"] and p.rus_name_unique):
                    if len(samples) < o["samples"]:
                        samples.append(f"[rus] #{p.id_plant}: {p.rus_name_unique!r} -> {new_rus!r}")
                    p.rus_name_unique = new_rus
                    dirty = True
            if dirty:
                changed += 1
                to_update.append(p)

        for line in samples:
            self.stdout.write(line)
        self.stdout.write(f"\nВсего просмотрено: {total} | изменится: {changed}")

        if not o["apply"]:
            self.stdout.write(self.style.WARNING("DRY-RUN — ничего не записано. Для записи добавьте --apply."))
            return

        fields = [f for f, on in (("lat_name_unique", do_lat), ("rus_name_unique", do_rus)) if on]
        for i in range(0, len(to_update), 500):
            m.Plant.objects.bulk_update(to_update[i : i + 500], fields, batch_size=500)
        self.stdout.write(self.style.SUCCESS(f"Записано: {changed} карточек (поля: {', '.join(fields)})."))
        self.stdout.write("Не забудьте переиндексировать ES: manage.py es_reindex")
