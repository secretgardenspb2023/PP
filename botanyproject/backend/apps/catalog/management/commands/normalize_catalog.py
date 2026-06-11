"""Normalize jsonb characteristic arrays → dictionaries + plant↔dict link tables.

Idempotent (safe to re-run): dictionary rows use get_or_create, link rows use
bulk_create(ignore_conflicts=True) backed by the (plant, value) unique
constraints. Applies the data-cleaning decided with the client (typos, duplicate
phrasings, slash-joined flower forms, the leaf_colors int-1 anomaly) and logs any
value that could not be mapped. Original jsonb columns are left untouched
(kept for rollback until release, proposal §6.9).

    docker compose exec backend python manage.py normalize_catalog [--flush]
"""
from collections import defaultdict

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.catalog import models as m


def _clean(token):
    return str(token).strip()


def _clean_flower_form(token):
    token = str(token).strip()
    # both observed misspellings of "асимметричный" (missing «н») → canonical
    return {
        "асимметричый": "асимметричный",
        "асимметрычый": "асимметричный",
    }.get(token, token)


def _clean_garden_style(token):
    token = str(token).strip()
    return {
        "природный": "природный/пейзажный",
        "природный, пейзажный": "природный/пейзажный",
    }.get(token, token)


def _clean_design_use(token):
    token = str(token).strip()
    return {"для укрепление склона": "для укрепления склона"}.get(token, token)


def _clean_color(token):
    if token in (1, "1"):  # id_plant=11594 stored int 1 instead of ["Белый"]
        return "Белый"
    return str(token).strip()


# (source_model, jsonb_field, splitter, through_model, dict_model, cleaner)
NEW_DICT_RELATIONS = [
    (m.PlantVisual, "leaf_shape", "list", m.PlantLeafShape, m.DictLeafShape, _clean),
    (m.PlantVisual, "habit_forms", "list", m.PlantHabitForm, m.DictHabitForm, _clean),
    (m.PlantVisual, "flower_form", "slash", m.PlantFlowerForm, m.DictFlowerForm, _clean_flower_form),
    (m.PlantCare, "sun", "list", m.PlantSunType, m.DictSunType, _clean),
    (m.PlantCare, "soil_acid", "list", m.PlantSoilAcidity, m.DictSoilAcidity, _clean),
    (m.PlantCare, "propagation", "list", m.PlantPropagation, m.DictPropagation, _clean),
    (m.PlantCare, "care_level", "list", m.PlantCareLevel, m.DictCareLevel, _clean),
    (m.PlantDesign, "design_uses", "list", m.PlantDesignUse, m.DictDesignUse, _clean_design_use),
    (m.PlantDesign, "garden_styles", "list", m.PlantGardenStyle, m.DictGardenStyle, _clean_garden_style),
    (m.PlantDesign, "designer", "list", m.PlantDesigner, m.DictDesigner, _clean),
    (m.PlantDesign, "fruit_uses", "list", m.PlantFruitUse, m.DictFruitUse, _clean),
]

# (source_model, jsonb_field, through_model) — reuse the existing Color dictionary
COLOR_RELATIONS = [
    (m.PlantVisual, "flower_colors", m.PlantFlowerColor),
    (m.PlantVisual, "leaf_colors", m.PlantLeafColor),
]
# (source_model, jsonb_field, through_model) — reuse the existing Month dictionary
MONTH_RELATIONS = [
    (m.PlantVisual, "vegetation_periods", m.PlantVegetationPeriod),
    (m.PlantVisual, "flowering_months", m.PlantFloweringMonth),
    (m.PlantDesign, "fruiting_months", m.PlantFruitingMonth),
]

ALL_THROUGH = (
    [r[3] for r in NEW_DICT_RELATIONS]
    + [r[2] for r in COLOR_RELATIONS]
    + [r[2] for r in MONTH_RELATIONS]
)
ALL_DICTS = [r[4] for r in NEW_DICT_RELATIONS]


def _iter_tokens(raw, splitter):
    if raw is None:
        return
    if splitter == "slash":
        for part in str(raw).split("/"):
            part = part.strip()
            if part:
                yield part
        return
    if isinstance(raw, list):
        yield from raw
    else:  # scalar anomaly (e.g. int 1)
        yield raw


class Command(BaseCommand):
    help = "Normalize jsonb characteristic arrays into dictionaries + link tables (idempotent)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--flush", action="store_true",
            help="Clear link + new dictionary tables before rebuilding.",
        )

    def handle(self, *args, **options):
        self.unconverted = defaultdict(set)

        if options["flush"]:
            for through in ALL_THROUGH:
                through.objects.all().delete()
            for dict_model in ALL_DICTS:
                dict_model.objects.all().delete()
            self.stdout.write("flushed link + dictionary tables")

        for source, field, splitter, through, dict_model, cleaner in NEW_DICT_RELATIONS:
            self._process_new_dict(source, field, splitter, through, dict_model, cleaner)

        # "Тень" has no data but is kept as a selectable option for future cards.
        m.DictSunType.objects.get_or_create(name="Тень")

        for source, field, through in COLOR_RELATIONS:
            self._process_existing(source, field, through, m.Color, "color_name", _clean_color)
        for source, field, through in MONTH_RELATIONS:
            self._process_existing(source, field, through, m.Month, "month_name", _clean)

        self._report()

    def _rows(self, source, field):
        return list(source.objects.values_list("plant_id", field))

    @transaction.atomic
    def _process_new_dict(self, source, field, splitter, through, dict_model, cleaner):
        rows = self._rows(source, field)

        names = set()
        for _pk, raw in rows:
            for token in _iter_tokens(raw, splitter):
                cleaned = cleaner(token)
                if cleaned:
                    names.add(cleaned)
        cache = {}
        for name in names:
            obj, _ = dict_model.objects.get_or_create(name=name)
            cache[name] = obj

        links = []
        for pk, raw in rows:
            for token in _iter_tokens(raw, splitter):
                cleaned = cleaner(token)
                if cleaned:
                    links.append(through(plant_id=pk, value=cache[cleaned]))
        through.objects.bulk_create(links, ignore_conflicts=True, batch_size=5000)
        self.stdout.write(f"{field:<22} dict={len(cache):>3}  links={len(links):>6}")

    @transaction.atomic
    def _process_existing(self, source, field, through, dict_model, name_attr, cleaner):
        cache = {getattr(o, name_attr): o for o in dict_model.objects.all()}
        rows = self._rows(source, field)

        links = []
        for pk, raw in rows:
            for token in _iter_tokens(raw, "list"):
                cleaned = cleaner(token)
                obj = cache.get(cleaned)
                if obj is None:
                    self.unconverted[field].add(repr(token))
                    continue
                links.append(through(plant_id=pk, value=obj))
        through.objects.bulk_create(links, ignore_conflicts=True, batch_size=5000)
        self.stdout.write(f"{field:<22} reuse={len(cache):>3}  links={len(links):>6}")

    def _report(self):
        if not self.unconverted:
            self.stdout.write(self.style.SUCCESS("all values mapped"))
            return
        self.stdout.write(self.style.WARNING("unconverted values:"))
        for field, vals in self.unconverted.items():
            self.stdout.write(f"  {field}: {sorted(vals)}")
