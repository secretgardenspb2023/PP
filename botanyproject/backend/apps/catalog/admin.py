"""Minimal admin for the catalog (ТЗ Этап 7 will build the full editing UX).

Read-oriented registration so the imported client data is browsable in /admin/.
"""
from django.contrib import admin

from .models import (
    Color,
    DictCareLevel,
    DictDesigner,
    DictDesignUse,
    DictFlowerForm,
    DictFruitUse,
    DictGardenStyle,
    DictHabitForm,
    DictLeafShape,
    DictPropagation,
    DictSoilAcidity,
    DictSunType,
    Family,
    Genus,
    Month,
    Plant,
    PlantPhoto,
    PlantSynonym,
    Species,
)


@admin.register(Plant)
class PlantAdmin(admin.ModelAdmin):
    list_display = ("id_plant", "lat_name_unique", "name_rus", "species", "usda_zone", "is_template")
    list_filter = ("is_template", "is_ishs_registered", "usda_zone")
    search_fields = ("lat_name_unique", "name_rus", "url_slug", "rus_name_unique", "species__name")
    list_select_related = ("species",)
    raw_id_fields = ("species",)
    list_per_page = 50


@admin.register(Species)
class SpeciesAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "rus_name", "genus")
    search_fields = ("name", "rus_name", "genus__name")
    list_select_related = ("genus",)
    raw_id_fields = ("genus",)
    list_per_page = 50


@admin.register(Genus)
class GenusAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "rus_name", "family")
    search_fields = ("name", "rus_name")
    list_select_related = ("family",)
    list_per_page = 50


@admin.register(Family)
class FamilyAdmin(admin.ModelAdmin):
    list_display = ("family_id", "family_rus", "family_lat")
    search_fields = ("family_rus", "family_lat")


@admin.register(PlantSynonym)
class PlantSynonymAdmin(admin.ModelAdmin):
    list_display = ("id", "synonym_name", "full_name", "synonym_lang", "synonym_type", "is_binomial")
    list_filter = ("synonym_lang", "synonym_type", "is_binomial")
    search_fields = ("synonym_name", "full_name")
    raw_id_fields = ("genus", "species", "plant")


@admin.register(PlantPhoto)
class PlantPhotoAdmin(admin.ModelAdmin):
    list_display = ("id", "plant", "is_main", "source_type", "public_url")
    list_filter = ("is_main", "source_type")
    raw_id_fields = ("plant",)


@admin.register(Color)
class ColorAdmin(admin.ModelAdmin):
    list_display = ("id", "color_name", "color_hex")


@admin.register(Month)
class MonthAdmin(admin.ModelAdmin):
    list_display = ("id", "month_name")


# Normalized characteristic dictionaries (ТЗ Этап 5) — simple name editing.
class DictAdmin(admin.ModelAdmin):
    list_display = ("id", "name")
    search_fields = ("name",)


admin.site.register(
    [
        DictLeafShape, DictHabitForm, DictFlowerForm, DictSunType, DictSoilAcidity,
        DictPropagation, DictCareLevel, DictDesignUse, DictGardenStyle, DictDesigner,
        DictFruitUse,
    ],
    DictAdmin,
)
