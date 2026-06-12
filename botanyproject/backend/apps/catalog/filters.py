"""Manual filtering + faceting for the catalog API (ТЗ Этап 5.12–5.17).

Multi-select inside a dimension is OR (``__in``); across dimensions it is AND
(successive ``.filter()``). Facet counts for a dimension are computed with every
*other* filter applied but the dimension itself excluded — the marketplace
behaviour, so picking one value does not zero out its siblings.
"""
from django.db.models import Count, Q

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


def apply_filters(qs, params, *, exclude=None):
    q = params.get("q")
    if q:
        search = Q()
        for field in SEARCH_FIELDS:
            search |= Q(**{f"{field}__icontains": q})
        qs = qs.filter(search)

    for dim, path in DIMENSIONS.items():
        if dim == exclude:
            continue
        values = _multi(params, dim)
        if values:
            qs = qs.filter(**{f"{path}__in": values})

    for prefix, field in RANGES.items():
        lo = _to_int(params.get(f"{prefix}_min"))
        hi = _to_int(params.get(f"{prefix}_max"))
        if lo is not None:
            qs = qs.filter(**{f"{field}__gte": lo})
        if hi is not None:
            qs = qs.filter(**{f"{field}__lte": hi})

    zones = [z for z in (_to_int(u) for u in _multi(params, "usda_zone")) if z is not None]
    if zones:
        qs = qs.filter(usda_zone__in=zones)

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
