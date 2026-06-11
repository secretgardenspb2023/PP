"""Catalog models — read-only mapping of the client's existing schema (ТЗ Этап 5).

All models are ``managed = False``: the tables already exist in the client's
database (schemas ``plant`` / ``plant_info`` / ``media``); Django reads/writes
them but does not create or alter them. Schema-qualified table names use the
``'schema"."table'`` quoting trick so Django emits ``"schema"."table"``.

Structure (real, from dump-botany_db, PG 17): families → genera → species →
plants; per-plant 1:1 characteristic tables in ``plant_info``; photos in
``media``. The jsonb array columns (leaf_shape, sun, design_uses, …) are kept
as JSONField for now; their normalization into dictionaries + M2M is a separate,
client-approved step (see docs/database.md).
"""
from django.db import models


# --------------------------------------------------------------------------- #
#  Dictionaries
# --------------------------------------------------------------------------- #
class Color(models.Model):
    color_name = models.CharField(max_length=30, unique=True)
    color_hex = models.CharField(max_length=7)

    class Meta:
        managed = False
        db_table = 'plant"."dict_colors'
        verbose_name = "цвет"
        verbose_name_plural = "цвета"

    def __str__(self):
        return self.color_name


class Month(models.Model):
    month_name = models.CharField(max_length=20, unique=True)

    class Meta:
        managed = False
        db_table = 'plant_info"."dict_months'
        verbose_name = "месяц"
        verbose_name_plural = "месяцы"

    def __str__(self):
        return self.month_name


# --------------------------------------------------------------------------- #
#  Taxonomy
# --------------------------------------------------------------------------- #
class Family(models.Model):
    family_id = models.AutoField(primary_key=True)
    family_rus = models.CharField("семейство (рус)", max_length=50, unique=True)
    family_lat = models.CharField("семейство (лат)", max_length=50, unique=True)

    class Meta:
        managed = False
        db_table = 'plant"."plant_families'
        verbose_name = "семейство"
        verbose_name_plural = "семейства"

    def __str__(self):
        return f"{self.family_rus} ({self.family_lat})"


class Genus(models.Model):
    name = models.CharField("род (лат)", max_length=50, unique=True, null=True, blank=True)
    rus_name = models.CharField("род (рус)", max_length=50, null=True, blank=True)
    family = models.ForeignKey(
        Family, db_column="family_id", on_delete=models.DO_NOTHING,
        null=True, blank=True, related_name="genera",
    )

    class Meta:
        managed = False
        db_table = 'plant"."genera'
        verbose_name = "род"
        verbose_name_plural = "роды"

    def __str__(self):
        return self.name or self.rus_name or f"род #{self.pk}"


class Species(models.Model):
    genus = models.ForeignKey(
        Genus, db_column="genus_id", on_delete=models.DO_NOTHING, related_name="species",
    )
    name = models.CharField("вид (лат)", max_length=50)
    rus_name = models.CharField("вид (рус)", max_length=50, null=True, blank=True)

    class Meta:
        managed = False
        db_table = 'plant"."species'
        verbose_name = "вид"
        verbose_name_plural = "виды"

    def __str__(self):
        return self.name


class Plant(models.Model):
    id_plant = models.AutoField(primary_key=True)
    species = models.ForeignKey(
        Species, db_column="species_id", on_delete=models.DO_NOTHING, related_name="plants",
    )
    variety = models.CharField("сорт", max_length=100, null=True, blank=True)
    lat_name_unique = models.CharField("латинское название", max_length=100, null=True, blank=True)
    url_slug = models.CharField(max_length=100, null=True, blank=True)
    name_rus = models.CharField("русское название", max_length=255, null=True, blank=True)
    rus_name_unique = models.CharField(max_length=100, null=True, blank=True)
    id_pp = models.IntegerField("ключ донорских фото", null=True, blank=True)
    usda_zone = models.IntegerField("зона USDA", null=True, blank=True)
    is_template = models.BooleanField("шаблон вида", default=False)
    is_ishs_registered = models.BooleanField("зарегистрирован ISHS", default=False, null=True)
    created_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        managed = False
        db_table = 'plant"."plants'
        verbose_name = "растение"
        verbose_name_plural = "растения"

    def __str__(self):
        return self.name_rus or self.lat_name_unique or f"растение #{self.pk}"


class PlantSynonym(models.Model):
    LANG_CHOICES = [("Русский", "Русский"), ("Латинский", "Латинский"), ("Оригинальный", "Оригинальный")]
    TYPE_CHOICES = [
        ("Альтернативное", "Альтернативное"), ("Перевод", "Перевод"), ("Транслит", "Транслит"),
        ("Народное", "Народное"), ("Устаревшее", "Устаревшее"), ("Торговое", "Торговое"),
    ]
    synonym_name = models.CharField(max_length=50)
    genus = models.ForeignKey(
        Genus, db_column="genus_id", on_delete=models.DO_NOTHING, null=True, blank=True, related_name="synonyms",
    )
    species = models.ForeignKey(
        Species, db_column="species_id", on_delete=models.DO_NOTHING, null=True, blank=True, related_name="synonyms",
    )
    plant = models.ForeignKey(
        Plant, db_column="plant_id", on_delete=models.DO_NOTHING, null=True, blank=True, related_name="synonyms",
    )
    is_binomial = models.BooleanField(default=False)
    synonym_lang = models.CharField(max_length=20, choices=LANG_CHOICES, null=True, blank=True)
    synonym_type = models.CharField(max_length=20, choices=TYPE_CHOICES, null=True, blank=True)
    full_name = models.CharField(max_length=255, null=True, blank=True)

    class Meta:
        managed = False
        db_table = 'plant"."plant_synonyms'
        verbose_name = "синоним"
        verbose_name_plural = "синонимы"

    def __str__(self):
        return self.full_name or self.synonym_name


# --------------------------------------------------------------------------- #
#  Per-plant characteristics (1:1 on id_plant)
# --------------------------------------------------------------------------- #
class PlantVisual(models.Model):
    plant = models.OneToOneField(
        Plant, primary_key=True, db_column="id_plant", on_delete=models.DO_NOTHING, related_name="visual",
    )
    height_max_cm = models.IntegerField(null=True, blank=True)
    diameter_max_cm = models.IntegerField(null=True, blank=True)
    annual_growth_cm = models.IntegerField(null=True, blank=True)
    is_thorny = models.BooleanField(default=False)
    leaf_shape = models.JSONField(null=True, blank=True)
    flowering_duration = models.CharField(max_length=100, null=True, blank=True)
    flower_form = models.CharField(max_length=100, null=True, blank=True)
    vegetation_periods = models.JSONField(default=list)
    habit_forms = models.JSONField(default=list)
    flower_colors = models.JSONField(default=list, null=True, blank=True)
    leaf_colors = models.JSONField(default=list, null=True, blank=True)
    flowering_months = models.JSONField(default=list, null=True, blank=True)

    class Meta:
        managed = False
        db_table = 'plant_info"."plant_visual'
        verbose_name = "характеристики (вид)"
        verbose_name_plural = "характеристики (вид)"

    def __str__(self):
        return f"характеристики (вид) растения #{self.plant_id}"


class PlantCare(models.Model):
    plant = models.OneToOneField(
        Plant, primary_key=True, db_column="id_plant", on_delete=models.DO_NOTHING, related_name="care",
    )
    sun = models.JSONField(default=list, null=True, blank=True)
    soil_acid = models.JSONField(default=list, null=True, blank=True)
    soil_demanding = models.BooleanField(default=False, null=True)
    propagation = models.JSONField(default=list, null=True, blank=True)
    care_level = models.JSONField(default=list, null=True, blank=True)
    care_city = models.BooleanField(default=False, null=True)
    care_disease_resistant = models.BooleanField(default=False, null=True)
    care_pest_resistant = models.BooleanField(default=False, null=True)
    care_no_shelter_boolean = models.BooleanField(default=False, null=True)
    care_no_digging_boolean = models.BooleanField(default=False, null=True)
    care_no_watering_boolean = models.BooleanField(default=False, null=True)

    class Meta:
        managed = False
        db_table = 'plant_info"."plant_care'
        verbose_name = "характеристики (уход)"
        verbose_name_plural = "характеристики (уход)"

    def __str__(self):
        return f"характеристики (уход) растения #{self.plant_id}"


class PlantDesign(models.Model):
    plant = models.OneToOneField(
        Plant, primary_key=True, db_column="id_plant", on_delete=models.DO_NOTHING, related_name="design",
    )
    design_uses = models.JSONField(default=list, null=True, blank=True)
    garden_styles = models.JSONField(default=list, null=True, blank=True)
    designer = models.JSONField(default=list, null=True, blank=True)
    fruit_uses = models.JSONField(default=list, null=True, blank=True)
    fruiting_months = models.JSONField(null=True, blank=True)
    is_toxic = models.BooleanField(default=False, null=True)
    has_aroma = models.BooleanField(default=False, null=True)
    is_self_fertile = models.BooleanField(default=False, null=True)
    is_allergen = models.BooleanField(default=False, null=True)
    has_decorative_bark = models.BooleanField(default=False, null=True)
    has_decorative_fruit = models.BooleanField(default=False, null=True)

    class Meta:
        managed = False
        db_table = 'plant_info"."plant_design'
        verbose_name = "характеристики (дизайн)"
        verbose_name_plural = "характеристики (дизайн)"

    def __str__(self):
        return f"характеристики (дизайн) растения #{self.plant_id}"


class PlantDescription(models.Model):
    plant = models.OneToOneField(
        Plant, primary_key=True, db_column="id_plant", on_delete=models.DO_NOTHING, related_name="description",
    )
    content_text = models.TextField(null=True, blank=True)
    requirements = models.TextField(null=True, blank=True)
    problems = models.TextField(null=True, blank=True)
    diseases_pests = models.TextField(null=True, blank=True)
    propagation = models.TextField(null=True, blank=True)
    usage_info = models.TextField(null=True, blank=True)
    interesting_facts = models.TextField(null=True, blank=True)

    class Meta:
        managed = False
        db_table = 'plant_info"."plant_descriptions'
        verbose_name = "описание"
        verbose_name_plural = "описания"

    def __str__(self):
        return f"описание растения #{self.plant_id}"


# --------------------------------------------------------------------------- #
#  Media
# --------------------------------------------------------------------------- #
class PlantPhoto(models.Model):
    plant = models.ForeignKey(
        Plant, db_column="plant_id", on_delete=models.DO_NOTHING, related_name="photos",
    )
    storage_key = models.TextField(null=True, blank=True)
    public_url = models.TextField()
    preview_url = models.TextField(null=True, blank=True)
    source_type = models.CharField(max_length=50, null=True, blank=True, default="donor")
    is_main = models.BooleanField(default=False, null=True)
    created_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        managed = False
        db_table = 'media"."plant_photos'
        verbose_name = "фото"
        verbose_name_plural = "фото"

    def __str__(self):
        return self.public_url


# =========================================================================== #
#  NORMALIZATION (ТЗ Этап 5) — NEW Django-managed tables.
#
#  The jsonb array columns on plant_visual/care/design are normalized into
#  dictionaries + plant↔dict link tables so faceted filters with counts and
#  Elasticsearch indexing work. These tables are created by migrations and
#  populated by `manage.py normalize_catalog` (idempotent). The original jsonb
#  columns are kept until release for rollback (proposal §6.9). Colors and
#  months reuse the existing Color / Month dictionaries.
# =========================================================================== #
class AbstractDict(models.Model):
    name = models.CharField(max_length=255, unique=True)

    class Meta:
        abstract = True
        ordering = ["name"]

    def __str__(self):
        return self.name


class DictLeafShape(AbstractDict):
    class Meta(AbstractDict.Meta):
        managed = True
        db_table = 'plant_info"."dict_leaf_shapes'
        verbose_name = "форма листа"
        verbose_name_plural = "формы листа"


class DictHabitForm(AbstractDict):
    class Meta(AbstractDict.Meta):
        managed = True
        db_table = 'plant_info"."dict_habit_forms'
        verbose_name = "жизненная форма"
        verbose_name_plural = "жизненные формы"


class DictFlowerForm(AbstractDict):
    class Meta(AbstractDict.Meta):
        managed = True
        db_table = 'plant_info"."dict_flower_forms'
        verbose_name = "форма цветка"
        verbose_name_plural = "формы цветка"


class DictSunType(AbstractDict):
    class Meta(AbstractDict.Meta):
        managed = True
        db_table = 'plant_info"."dict_sun_types'
        verbose_name = "освещение"
        verbose_name_plural = "освещение"


class DictSoilAcidity(AbstractDict):
    class Meta(AbstractDict.Meta):
        managed = True
        db_table = 'plant_info"."dict_soil_acidity'
        verbose_name = "кислотность почвы"
        verbose_name_plural = "кислотность почвы"


class DictPropagation(AbstractDict):
    class Meta(AbstractDict.Meta):
        managed = True
        db_table = 'plant_info"."dict_propagation_methods'
        verbose_name = "способ размножения"
        verbose_name_plural = "способы размножения"


class DictCareLevel(AbstractDict):
    class Meta(AbstractDict.Meta):
        managed = True
        db_table = 'plant_info"."dict_care_levels'
        verbose_name = "уровень ухода"
        verbose_name_plural = "уровни ухода"


class DictDesignUse(AbstractDict):
    class Meta(AbstractDict.Meta):
        managed = True
        db_table = 'plant_info"."dict_design_uses'
        verbose_name = "применение в дизайне"
        verbose_name_plural = "применение в дизайне"


class DictGardenStyle(AbstractDict):
    class Meta(AbstractDict.Meta):
        managed = True
        db_table = 'plant_info"."dict_garden_styles'
        verbose_name = "стиль сада"
        verbose_name_plural = "стили сада"


class DictDesigner(AbstractDict):
    class Meta(AbstractDict.Meta):
        managed = True
        db_table = 'plant_info"."dict_designers'
        verbose_name = "ландшафтный дизайнер"
        verbose_name_plural = "ландшафтные дизайнеры"


class DictFruitUse(AbstractDict):
    class Meta(AbstractDict.Meta):
        managed = True
        db_table = 'plant_info"."dict_fruit_uses'
        verbose_name = "практическое применение"
        verbose_name_plural = "практическое применение"


class AbstractPlantLink(models.Model):
    """Base for plant↔dictionary link tables (the `plant`/`value` FKs are per child)."""

    class Meta:
        abstract = True

    def __str__(self):
        return f"{self.plant_id} → {self.value_id}"


class PlantLeafShape(AbstractPlantLink):
    plant = models.ForeignKey(Plant, db_column="id_plant", on_delete=models.CASCADE, related_name="leaf_shapes")
    value = models.ForeignKey(DictLeafShape, db_column="leaf_shape_id", on_delete=models.CASCADE, related_name="+")

    class Meta:
        managed = True
        db_table = 'plant_info"."plant_leaf_shapes'
        constraints = [models.UniqueConstraint(fields=["plant", "value"], name="uq_plant_leaf_shape")]


class PlantHabitForm(AbstractPlantLink):
    plant = models.ForeignKey(Plant, db_column="id_plant", on_delete=models.CASCADE, related_name="habit_forms")
    value = models.ForeignKey(DictHabitForm, db_column="habit_form_id", on_delete=models.CASCADE, related_name="+")

    class Meta:
        managed = True
        db_table = 'plant_info"."plant_habit_forms'
        constraints = [models.UniqueConstraint(fields=["plant", "value"], name="uq_plant_habit_form")]


class PlantFlowerForm(AbstractPlantLink):
    plant = models.ForeignKey(Plant, db_column="id_plant", on_delete=models.CASCADE, related_name="flower_forms")
    value = models.ForeignKey(DictFlowerForm, db_column="flower_form_id", on_delete=models.CASCADE, related_name="+")

    class Meta:
        managed = True
        db_table = 'plant_info"."plant_flower_forms'
        constraints = [models.UniqueConstraint(fields=["plant", "value"], name="uq_plant_flower_form")]


class PlantSunType(AbstractPlantLink):
    plant = models.ForeignKey(Plant, db_column="id_plant", on_delete=models.CASCADE, related_name="sun_types")
    value = models.ForeignKey(DictSunType, db_column="sun_type_id", on_delete=models.CASCADE, related_name="+")

    class Meta:
        managed = True
        db_table = 'plant_info"."plant_sun_types'
        constraints = [models.UniqueConstraint(fields=["plant", "value"], name="uq_plant_sun_type")]


class PlantSoilAcidity(AbstractPlantLink):
    plant = models.ForeignKey(Plant, db_column="id_plant", on_delete=models.CASCADE, related_name="soil_acidity")
    value = models.ForeignKey(DictSoilAcidity, db_column="soil_acidity_id", on_delete=models.CASCADE, related_name="+")

    class Meta:
        managed = True
        db_table = 'plant_info"."plant_soil_acidity'
        constraints = [models.UniqueConstraint(fields=["plant", "value"], name="uq_plant_soil_acidity")]


class PlantPropagation(AbstractPlantLink):
    plant = models.ForeignKey(Plant, db_column="id_plant", on_delete=models.CASCADE, related_name="propagation_methods")
    value = models.ForeignKey(DictPropagation, db_column="propagation_id", on_delete=models.CASCADE, related_name="+")

    class Meta:
        managed = True
        db_table = 'plant_info"."plant_propagation_methods'
        constraints = [models.UniqueConstraint(fields=["plant", "value"], name="uq_plant_propagation")]


class PlantCareLevel(AbstractPlantLink):
    plant = models.ForeignKey(Plant, db_column="id_plant", on_delete=models.CASCADE, related_name="care_levels")
    value = models.ForeignKey(DictCareLevel, db_column="care_level_id", on_delete=models.CASCADE, related_name="+")

    class Meta:
        managed = True
        db_table = 'plant_info"."plant_care_levels'
        constraints = [models.UniqueConstraint(fields=["plant", "value"], name="uq_plant_care_level")]


class PlantDesignUse(AbstractPlantLink):
    plant = models.ForeignKey(Plant, db_column="id_plant", on_delete=models.CASCADE, related_name="design_uses_m2m")
    value = models.ForeignKey(DictDesignUse, db_column="design_use_id", on_delete=models.CASCADE, related_name="+")

    class Meta:
        managed = True
        db_table = 'plant_info"."plant_design_uses'
        constraints = [models.UniqueConstraint(fields=["plant", "value"], name="uq_plant_design_use")]


class PlantGardenStyle(AbstractPlantLink):
    plant = models.ForeignKey(Plant, db_column="id_plant", on_delete=models.CASCADE, related_name="garden_styles_m2m")
    value = models.ForeignKey(DictGardenStyle, db_column="garden_style_id", on_delete=models.CASCADE, related_name="+")

    class Meta:
        managed = True
        db_table = 'plant_info"."plant_garden_styles'
        constraints = [models.UniqueConstraint(fields=["plant", "value"], name="uq_plant_garden_style")]


class PlantDesigner(AbstractPlantLink):
    plant = models.ForeignKey(Plant, db_column="id_plant", on_delete=models.CASCADE, related_name="designers")
    value = models.ForeignKey(DictDesigner, db_column="designer_id", on_delete=models.CASCADE, related_name="+")

    class Meta:
        managed = True
        db_table = 'plant_info"."plant_designers'
        constraints = [models.UniqueConstraint(fields=["plant", "value"], name="uq_plant_designer")]


class PlantFruitUse(AbstractPlantLink):
    plant = models.ForeignKey(Plant, db_column="id_plant", on_delete=models.CASCADE, related_name="fruit_uses_m2m")
    value = models.ForeignKey(DictFruitUse, db_column="fruit_use_id", on_delete=models.CASCADE, related_name="+")

    class Meta:
        managed = True
        db_table = 'plant_info"."plant_fruit_uses'
        constraints = [models.UniqueConstraint(fields=["plant", "value"], name="uq_plant_fruit_use")]


# Links that reuse the existing Color / Month dictionaries.
class PlantFlowerColor(AbstractPlantLink):
    plant = models.ForeignKey(Plant, db_column="id_plant", on_delete=models.CASCADE, related_name="flower_colors_m2m")
    value = models.ForeignKey(Color, db_column="color_id", on_delete=models.CASCADE, related_name="+")

    class Meta:
        managed = True
        db_table = 'plant_info"."plant_flower_colors'
        constraints = [models.UniqueConstraint(fields=["plant", "value"], name="uq_plant_flower_color")]


class PlantLeafColor(AbstractPlantLink):
    plant = models.ForeignKey(Plant, db_column="id_plant", on_delete=models.CASCADE, related_name="leaf_colors_m2m")
    value = models.ForeignKey(Color, db_column="color_id", on_delete=models.CASCADE, related_name="+")

    class Meta:
        managed = True
        db_table = 'plant_info"."plant_leaf_colors'
        constraints = [models.UniqueConstraint(fields=["plant", "value"], name="uq_plant_leaf_color")]


class PlantVegetationPeriod(AbstractPlantLink):
    plant = models.ForeignKey(Plant, db_column="id_plant", on_delete=models.CASCADE, related_name="vegetation_periods_m2m")
    value = models.ForeignKey(Month, db_column="month_id", on_delete=models.CASCADE, related_name="+")

    class Meta:
        managed = True
        db_table = 'plant_info"."plant_vegetation_periods'
        constraints = [models.UniqueConstraint(fields=["plant", "value"], name="uq_plant_vegetation_period")]


class PlantFloweringMonth(AbstractPlantLink):
    plant = models.ForeignKey(Plant, db_column="id_plant", on_delete=models.CASCADE, related_name="flowering_months_m2m")
    value = models.ForeignKey(Month, db_column="month_id", on_delete=models.CASCADE, related_name="+")

    class Meta:
        managed = True
        db_table = 'plant_info"."plant_flowering_months'
        constraints = [models.UniqueConstraint(fields=["plant", "value"], name="uq_plant_flowering_month")]


class PlantFruitingMonth(AbstractPlantLink):
    plant = models.ForeignKey(Plant, db_column="id_plant", on_delete=models.CASCADE, related_name="fruiting_months_m2m")
    value = models.ForeignKey(Month, db_column="month_id", on_delete=models.CASCADE, related_name="+")

    class Meta:
        managed = True
        db_table = 'plant_info"."plant_fruiting_months'
        constraints = [models.UniqueConstraint(fields=["plant", "value"], name="uq_plant_fruiting_month")]
