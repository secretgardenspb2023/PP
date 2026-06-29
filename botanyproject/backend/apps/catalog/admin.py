"""Minimal admin for the catalog (ТЗ Этап 7 will build the full editing UX).

Read-oriented registration so the imported client data is browsable in /admin/.
"""
from django import forms
from django.contrib import admin, messages
from django.utils import timezone

from . import imgproxy, media
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
    Review,
    ReviewPhoto,
    Species,
)
from django.utils.html import format_html


class PlantPhotoInline(admin.TabularInline):
    """Текущие фото карточки: превью + удаление. Добавление — через поле
    «Загрузить фото» в форме карточки (нужна загрузка файла в S3)."""

    model = PlantPhoto
    extra = 0
    fields = ("preview", "is_main", "source_type", "public_url")
    readonly_fields = ("preview", "source_type", "public_url")
    verbose_name = "фото"
    verbose_name_plural = "Текущие фото (можно удалять)"

    def has_add_permission(self, request, obj=None):
        return False

    @admin.display(description="превью")
    def preview(self, obj):
        url = obj.preview_url or obj.public_url
        return format_html('<img src="{}" style="height:64px;border-radius:6px">', url) if url else "—"


class PlantAdminForm(forms.ModelForm):
    # FileField (не ImageField) — ImageField требует Pillow для валидации, которого нет
    # в контейнере; тип файла всё равно проверяет media.upload_image (только изображения).
    upload_photo = forms.FileField(
        required=False, label="Загрузить фото",
        widget=forms.ClearableFileInput(attrs={"accept": "image/*"}),
        help_text="Выберите файл изображения (JPG/PNG/WebP, до 8 МБ) — он добавится в карточку при сохранении.",
    )
    photo_url = forms.URLField(
        required=False, label="…или фото по ссылке (URL)", assume_scheme="https",
        help_text="Вставьте прямую ссылку на изображение — оно будет скачано и добавлено в карточку.",
    )
    photo_is_main = forms.BooleanField(
        required=False, initial=True, label="Сделать загруженное фото главным",
    )

    class Meta:
        model = Plant
        fields = "__all__"


@admin.register(Plant)
class PlantAdmin(admin.ModelAdmin):
    form = PlantAdminForm
    inlines = [PlantPhotoInline]
    list_display = ("id_plant", "lat_name_unique", "name_rus", "species", "usda_zone",
                    "is_template", "has_author_description")
    list_filter = ("is_template", "has_author_description", "is_ishs_registered", "usda_zone")
    search_fields = ("lat_name_unique", "name_rus", "url_slug", "rus_name_unique", "species__name")
    list_select_related = ("species",)
    raw_id_fields = ("species",)
    list_per_page = 50
    actions = ["make_template"]

    def get_changeform_initial_data(self, request):
        # Индивидуальное добавление карточки редактором — «авторское описание»
        # по умолчанию включено (ТЗ №5: защита от будущей массовой перезаписи).
        return {"has_author_description": True}

    def _attach_photo(self, request, obj, data, content_type, make_main):
        """Залить байты в S3 + создать PlantPhoto. Возвращает True при успехе."""
        try:
            key = media.upload_image(data, content_type, prefix=f"plants/{obj.pk}")
        except ValueError as exc:
            self.message_user(request, f"Фото не загружено: {exc}", level=messages.ERROR)
            return False
        is_main = make_main or not PlantPhoto.objects.filter(plant_id=obj.pk).exists()
        if is_main:
            PlantPhoto.objects.filter(plant_id=obj.pk).update(is_main=False)
        PlantPhoto.objects.create(
            plant_id=obj.pk, storage_key=key,
            public_url=imgproxy.full(key), preview_url=imgproxy.thumb(key),
            source_type="admin", is_main=is_main, created_at=timezone.now(),
        )
        return True

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        make_main = bool(form.cleaned_data.get("photo_is_main"))
        added = 0
        # 1) файл
        f = form.cleaned_data.get("upload_photo")
        if f and self._attach_photo(request, obj, f.read(), f.content_type, make_main and added == 0):
            added += 1
        # 2) по ссылке
        url = (form.cleaned_data.get("photo_url") or "").strip()
        if url:
            try:
                data, content_type = media.download_image(url)
            except ValueError as exc:
                self.message_user(request, f"Фото по ссылке не загружено: {exc}", level=messages.ERROR)
            else:
                if self._attach_photo(request, obj, data, content_type, make_main and added == 0):
                    added += 1
        if added:
            self.message_user(request, f"Добавлено фото: {added}.")

    @admin.action(description="Переопределить шаблон вида (сделать выбранную карточку шаблоном)")
    def make_template(self, request, queryset):
        # Снимаем is_template с других карточек того же вида, ставим на выбранную —
        # шаблон уникален в пределах вида (ТЗ №5).
        n = 0
        for plant in queryset.select_related("species"):
            Plant.objects.filter(species_id=plant.species_id).exclude(pk=plant.pk).update(is_template=False)
            if not plant.is_template:
                plant.is_template = True
                plant.save(update_fields=["is_template"])
            n += 1
        self.message_user(request, f"Шаблон вида переопределён ({n}).")


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


# --------------------------------------------------------------------------- #
#  Модерация отзывов (ТЗ §11 Фаза 2)
# --------------------------------------------------------------------------- #
class ReviewPhotoInline(admin.TabularInline):
    model = ReviewPhoto
    extra = 0
    fields = ("preview", "selected_for_card")
    readonly_fields = ("preview",)

    def preview(self, obj):
        if obj.preview_url:
            return format_html('<img src="{}" style="height:90px;border-radius:6px"/>', obj.preview_url)
        return "—"
    preview.short_description = "фото"


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ("id", "plant", "author_name", "status", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("author_name", "text", "plant__rus_name_unique")
    list_select_related = ("plant",)
    raw_id_fields = ("plant", "user")
    inlines = [ReviewPhotoInline]
    actions = ["approve", "reject"]

    @admin.action(description="Одобрить отзывы")
    def approve(self, request, queryset):
        n = queryset.update(status="approved")
        self.message_user(request, f"Одобрено: {n}.")

    @admin.action(description="Отклонить отзывы")
    def reject(self, request, queryset):
        n = queryset.update(status="rejected")
        self.message_user(request, f"Отклонено: {n}.")

    def save_related(self, request, form, formsets, change):
        # После сохранения: фото, отмеченные «в карточку», копируем в фото растения
        # (media.plant_photos, source_type="review"), если ещё не скопированы.
        super().save_related(request, form, formsets, change)
        review = form.instance
        for ph in review.photos.filter(selected_for_card=True):
            already = PlantPhoto.objects.filter(
                plant_id=review.plant_id, storage_key=ph.storage_key
            ).exists()
            if not already:
                PlantPhoto.objects.create(
                    plant_id=review.plant_id,
                    storage_key=ph.storage_key,
                    public_url=ph.public_url,
                    preview_url=ph.preview_url,
                    source_type="review",
                )
