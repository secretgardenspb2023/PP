"""DRF serializers for the catalog read-API (ТЗ Этап 5)."""
import bleach
from rest_framework import serializers

from . import models as m

# Безопасная разметка в описаниях (ТЗ 9.3): разрешаем базовые теги форматирования,
# всё остальное (script, style, on*-атрибуты, js:-ссылки) bleach вырезает.
_ALLOWED_TAGS = [
    "p", "br", "strong", "b", "em", "i", "u", "ul", "ol", "li",
    "a", "h3", "h4", "h5", "blockquote", "span", "hr",
]
_ALLOWED_ATTRS = {"a": ["href", "title", "rel", "target"]}
_BLOCK_MARKERS = ("<p", "<br", "<ul", "<ol", "<li", "<h3", "<h4", "<h5", "<blockquote", "<hr")


def _clean_html(value):
    """Санитайзенный HTML для вывода. Разрешает белый список тегов, вырезает опасное.
    Если в тексте нет блочных тегов (обычный текст ~92% карточек) — переносы строк
    превращаем в <br>, чтобы абзацы сохранились. None для пустого."""
    if not value:
        return None
    cleaned = bleach.clean(str(value), tags=_ALLOWED_TAGS, attributes=_ALLOWED_ATTRS, strip=True).strip()
    if not cleaned:
        return None
    if not any(marker in cleaned.lower() for marker in _BLOCK_MARKERS):
        cleaned = cleaned.replace("\n", "<br>")
    return cleaned


def _names(manager, attr="name"):
    """Flat list of dictionary names from a prefetched plant↔dict link manager."""
    return [getattr(link.value, attr) for link in manager.all()]


def display_name(plant):
    """Russian display name. По решению заказчика заголовок берётся из
    ``rus_name_unique`` (заполнено для всех карточек, включает сорт). Остальное —
    подстраховка: ``name_rus``, канонический русский биномен (род + вид), латынь."""
    if plant.rus_name_unique:
        return plant.rus_name_unique
    if plant.name_rus:
        return plant.name_rus
    species = plant.species
    rus_binomial = " ".join(filter(None, [species.genus.rus_name, species.rus_name]))
    return rus_binomial or plant.lat_name_unique or f"#{plant.pk}"


class PlantListSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()
    species = serializers.CharField(source="species.name", read_only=True)
    genus = serializers.SerializerMethodField()
    family = serializers.SerializerMethodField()
    main_photo = serializers.SerializerMethodField()

    class Meta:
        model = m.Plant
        fields = [
            "id_plant", "url_slug", "name", "name_rus", "lat_name_unique",
            "usda_zone", "species", "genus", "family", "main_photo",
        ]

    def get_name(self, obj):
        return display_name(obj)

    def get_genus(self, obj):
        genus = obj.species.genus
        return genus.name or genus.rus_name

    def get_family(self, obj):
        family = obj.species.genus.family
        return family.family_lat if family else None

    def get_main_photo(self, obj):
        photos = list(obj.photos.all())
        if not photos:
            return None
        main = next((p for p in photos if p.is_main), photos[0])
        return main.preview_url or main.public_url


def _synonym(s, level):
    return {
        "synonym_name": s.synonym_name,
        "full_name": s.full_name,
        "synonym_lang": s.synonym_lang,
        "synonym_type": s.synonym_type,
        "is_binomial": s.is_binomial,
        "level": level,  # genus | species | plant — see docs/plant-card-matrix.md
    }


class PlantPhotoSerializer(serializers.ModelSerializer):
    class Meta:
        model = m.PlantPhoto
        fields = ["id", "public_url", "preview_url", "is_main", "source_type"]


class PlantDetailSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()
    taxonomy = serializers.SerializerMethodField()
    characteristics = serializers.SerializerMethodField()
    descriptions = serializers.SerializerMethodField()
    synonyms = serializers.SerializerMethodField()
    photos = serializers.SerializerMethodField()

    class Meta:
        model = m.Plant
        fields = [
            "id_plant", "url_slug", "name", "name_rus", "lat_name_unique", "variety",
            "rus_name_unique", "usda_zone", "is_template", "is_ishs_registered",
            "created_at", "taxonomy", "characteristics", "descriptions", "synonyms", "photos",
        ]

    def get_name(self, obj):
        return display_name(obj)

    def get_taxonomy(self, obj):
        species = obj.species
        genus = species.genus
        family = genus.family
        return {
            "species": species.name,
            "species_rus": species.rus_name,
            "genus": genus.name,
            "genus_rus": genus.rus_name,
            "family_lat": family.family_lat if family else None,
            "family_rus": family.family_rus if family else None,
        }

    def get_characteristics(self, obj):
        visual = getattr(obj, "visual", None)
        care = getattr(obj, "care", None)
        design = getattr(obj, "design", None)
        data = {
            "leaf_shapes": _names(obj.leaf_shapes),
            "habit_forms": _names(obj.habit_forms),
            "flower_forms": _names(obj.flower_forms),
            "flower_colors": _names(obj.flower_colors_m2m, "color_name"),
            "leaf_colors": _names(obj.leaf_colors_m2m, "color_name"),
            "vegetation_periods": _names(obj.vegetation_periods_m2m, "month_name"),
            "flowering_months": _names(obj.flowering_months_m2m, "month_name"),
            "fruiting_months": _names(obj.fruiting_months_m2m, "month_name"),
            "sun": _names(obj.sun_types),
            "soil_acidity": _names(obj.soil_acidity),
            "propagation": _names(obj.propagation_methods),
            "care_levels": _names(obj.care_levels),
            "design_uses": _names(obj.design_uses_m2m),
            "garden_styles": _names(obj.garden_styles_m2m),
            "designers": _names(obj.designers),
            "fruit_uses": _names(obj.fruit_uses_m2m),
        }
        if visual:
            data |= {
                "height_max_cm": visual.height_max_cm,
                "diameter_max_cm": visual.diameter_max_cm,
                "annual_growth_cm": visual.annual_growth_cm,
                "is_thorny": visual.is_thorny,
            }
        if care:
            data |= {
                "soil_demanding": care.soil_demanding,
                "disease_resistant": care.care_disease_resistant,
                "pest_resistant": care.care_pest_resistant,
                "no_shelter": care.care_no_shelter_boolean,
                "city_tolerant": care.care_city,
                "no_digging": care.care_no_digging_boolean,
                "no_watering": care.care_no_watering_boolean,
            }
        if design:
            data |= {
                "is_toxic": design.is_toxic,
                "has_aroma": design.has_aroma,
                "is_self_fertile": design.is_self_fertile,
                "is_allergen": design.is_allergen,
                "has_decorative_bark": design.has_decorative_bark,
                "has_decorative_fruit": design.has_decorative_fruit,
            }
        return data

    def get_descriptions(self, obj):
        d = getattr(obj, "description", None)
        if not d:
            return {}
        return {
            # Все текстовые поля описания отдаём как санитайзенный HTML (ТЗ 9.3):
            # редактор может размечать абзацами/списками/ссылками, опасное вырезается.
            "text": _clean_html(d.content_text),
            "facts": _clean_html(d.interesting_facts),
            "requirements": _clean_html(d.requirements),
            "problems": _clean_html(d.problems),
            "diseases_pests": _clean_html(d.diseases_pests),
            "propagation": _clean_html(d.propagation),
            "usage": _clean_html(d.usage_info),
        }

    def get_synonyms(self, obj):
        # Synonyms are polymorphic (one of genus/species/plant). Inherit the genus-
        # and species-level (binomial) synonyms into the card, plus plant-level ones
        # (matrix: "синонимы уровня род и род-вид"). See docs/plant-card-matrix.md.
        species = obj.species
        genus = species.genus
        return [
            *(_synonym(s, "genus") for s in genus.synonyms.all()),
            *(_synonym(s, "species") for s in species.synonyms.all()),
            *(_synonym(s, "plant") for s in obj.synonyms.all()),
        ]

    def get_photos(self, obj):
        return PlantPhotoSerializer(obj.photos.all(), many=True).data
