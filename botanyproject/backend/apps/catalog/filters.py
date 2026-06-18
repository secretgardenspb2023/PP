"""Manual filtering + faceting for the catalog API (ТЗ Этап 5.12–5.17).

Multi-select inside a dimension is OR (``__in``); across dimensions it is AND
(successive ``.filter()``). Facet counts for a dimension are computed with every
*other* filter applied but the dimension itself excluded — the marketplace
behaviour, so picking one value does not zero out its siblings.
"""
from django.db.models import Count, Max, Min, Q

from . import search as es

# Number of bars in a range-filter distribution histogram (ТЗ 5.14).
HISTOGRAM_BUCKETS = 8

# query param -> queryset path to the dictionary value name
DIMENSIONS = {
    "leaf_shape": "leaf_shapes__value__name",
    "habit_form": "habit_forms__value__name",
    "flower_form": "flower_forms__value__name",
    "sun": "sun_types__value__name",
    "soil_acid": "soil_acidity__value__name",
    "propagation": "propagation_methods__value__name",
    "care_level": "care_levels__value__name",
    "design_use": "design_uses_m2m__value__name",
    "garden_style": "garden_styles_m2m__value__name",
    "designer": "designers__value__name",
    "fruit_use": "fruit_uses_m2m__value__name",
    "flower_color": "flower_colors_m2m__value__color_name",
    "leaf_color": "leaf_colors_m2m__value__color_name",
    "vegetation_period": "vegetation_periods_m2m__value__month_name",
    "flowering_month": "flowering_months_m2m__value__month_name",
    "fruiting_month": "fruiting_months_m2m__value__month_name",
}

# param prefix (<prefix>_min / <prefix>_max) -> numeric field
RANGES = {
    "height": "visual__height_max_cm",
    "diameter": "visual__diameter_max_cm",
    "growth": "visual__annual_growth_cm",
}

BOOLEANS = {
    "is_thorny": "visual__is_thorny",
    "is_toxic": "design__is_toxic",
    "has_aroma": "design__has_aroma",
}

SORTS = {
    "name": "lat_name_unique",
    "-name": "-lat_name_unique",
    "new": "-created_at",
    "old": "created_at",
    "id": "id_plant",
}

SEARCH_FIELDS = [
    "name_rus", "lat_name_unique", "rus_name_unique", "url_slug",
    "species__name", "species__rus_name",
    "species__genus__name", "species__genus__rus_name",
]


def _multi(params, key):
    raw = params.get(key)
    return [v.strip() for v in raw.split(",") if v.strip()] if raw else []


def _to_int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _bool(value):
    return str(value).lower() in ("1", "true", "yes", "on")


def _fulltext_ids(query):
    """id_plant matches from Elasticsearch, or None when ES is unavailable.

    None signals the caller to degrade to the PostgreSQL fallback (ТЗ 5.11)."""
    try:
        if es.is_available():
            return es.search_ids(query)
    except Exception:  # noqa: BLE001 — any ES error degrades to PostgreSQL
        pass
    return None


def _ilike_condition(query):
    # PostgreSQL fallback used only when ES is down. Fold «ё»→«е» so a "клён"
    # query still matches data stored without «ё» ("Клен") — the literal ILIKE
    # match the previous implementation lacked. No morphology/synonyms here; the
    # ES path (above) is the real search.
    folded = query.replace("ё", "е").replace("Ё", "Е")
    cond = Q()
    for field in SEARCH_FIELDS:
        cond |= Q(**{f"{field}__icontains": folded})
    return cond


def apply_filters(qs, params, *, exclude=None, exclude_range=None):
    q = (params.get("q") or "").strip()
    if q:
        ids = _fulltext_ids(q)
        if ids is None:
            qs = qs.filter(_ilike_condition(q))
        elif ids:
            qs = qs.filter(id_plant__in=ids)
        else:
            qs = qs.none()

    for dim, path in DIMENSIONS.items():
        if dim == exclude:
            continue
        values = _multi(params, dim)
        if values:
            qs = qs.filter(**{f"{path}__in": values})

    for prefix, field in RANGES.items():
        if prefix == exclude_range:
            continue
        lo = _to_int(params.get(f"{prefix}_min"))
        hi = _to_int(params.get(f"{prefix}_max"))
        if lo is not None:
            qs = qs.filter(**{f"{field}__gte": lo})
        if hi is not None:
            qs = qs.filter(**{f"{field}__lte": hi})

    zones = [z for z in (_to_int(u) for u in _multi(params, "usda_zone")) if z is not None]
    if zones:
        qs = qs.filter(usda_zone__in=zones)

    # Алфавитный навигатор (ТЗ 5.17 / дизайн): карточки по первой букве отображаемого
    # имени (rus_name_unique). Спецзначение "#" — всё, что начинается не с буквы.
    letter = (params.get("letter") or "").strip()
    if letter == "#":
        qs = qs.exclude(rus_name_unique__iregex=r"^[A-Za-zА-Яа-яЁё]")
    elif letter:
        qs = qs.filter(rus_name_unique__istartswith=letter[:1])

    for param, field in BOOLEANS.items():
        if param in params:
            qs = qs.filter(**{field: _bool(params.get(param))})

    return qs


def facet_counts(base_qs, params):
    """{dimension: [{value, count}, ...]} respecting all other active filters."""
    facets = {}
    for dim, path in DIMENSIONS.items():
        rows = (
            apply_filters(base_qs, params, exclude=dim)
            .values(path)
            .annotate(count=Count("pk", distinct=True))
            .order_by("-count")
        )
        facets[dim] = [
            {"value": row[path], "count": row["count"]}
            for row in rows
            if row[path] is not None
        ]
    return facets


def histograms(base_qs, params):
    """Distribution of each range field for slider histograms (ТЗ 5.14).

    Returns ``{prefix: {min, max, buckets: [{from, to, count}, …]}}``. Like facets,
    each range respects every *other* active filter but excludes its own min/max,
    so dragging a slider does not reshape its own distribution chart.
    """
    out = {}
    for prefix, field in RANGES.items():
        qs = apply_filters(base_qs, params, exclude_range=prefix).filter(
            **{f"{field}__isnull": False}
        )
        bounds = qs.aggregate(lo=Min(field), hi=Max(field))
        lo, hi = bounds["lo"], bounds["hi"]
        if lo is None or hi is None:
            out[prefix] = {"min": None, "max": None, "buckets": []}
            continue
        if hi == lo:
            out[prefix] = {
                "min": lo, "max": hi,
                "buckets": [{"from": lo, "to": hi, "count": qs.count()}],
            }
            continue
        width = (hi - lo) / HISTOGRAM_BUCKETS
        edges = [lo + width * i for i in range(HISTOGRAM_BUCKETS + 1)]
        edges[-1] = hi  # avoid float drift dropping the top value
        # One aggregate query per range: a conditional count per bucket.
        annotations = {}
        for i in range(HISTOGRAM_BUCKETS):
            cond = Q(**{f"{field}__gte": edges[i]})
            # Last bucket is closed on the right; the others are half-open.
            upper = "lte" if i == HISTOGRAM_BUCKETS - 1 else "lt"
            cond &= Q(**{f"{field}__{upper}": edges[i + 1]})
            annotations[f"b{i}"] = Count("pk", filter=cond, distinct=True)
        row = qs.aggregate(**annotations)
        out[prefix] = {
            "min": lo, "max": hi,
            "buckets": [
                {"from": round(edges[i], 1), "to": round(edges[i + 1], 1),
                 "count": row[f"b{i}"]}
                for i in range(HISTOGRAM_BUCKETS)
            ],
        }
    return out
