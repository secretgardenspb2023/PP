# Документация структуры БД PoiskPlant

> Ведётся в git вместе с моделями Django, обновляется при каждом изменении схемы
> (ТЗ раздел 5). Заказчик имеет доступ с первого дня. Любые **изменения** схемы —
> только по согласованию.

Источник: дамп `dump-botany_db-202606041900.sql` (PostgreSQL 17.9), загружен в dev-БД.
Маппинг на Django — приложение `backend/apps/catalog` (всё `managed=False`: читаем
существующие таблицы, не создаём их).

## Схемы PostgreSQL

| Схема             | Назначение                                  |
|-------------------|---------------------------------------------|
| `plant`           | таксономия + карточки растений + синонимы    |
| `plant_info`      | характеристики растений (1:1 с карточкой)    |
| `media`           | фотографии растений                          |
| `user_info`       | пользователи + гео-справочники + роли        |
| `django_internal` | старые служебные таблицы Django (пересоздаются)|

## `plant` — ядро

**plant_families** (162) — `family_id` PK (identity), `family_rus` uniq, `family_lat` uniq.

**genera** (1 168) — `id` PK, `name` uniq (лат, nullable), `rus_name`, `family_id` → plant_families.

**species** (2 419) — `id` PK, `genus_id` → genera (CASCADE), `name` (лат), `rus_name`. uniq(genus_id, name).

**plants** (12 371) — карточка растения:

| Поле | Тип | Прим. |
|------|-----|-------|
| id_plant | int PK | |
| species_id | int → species (CASCADE, NOT NULL) | |
| variety | varchar(100) | сорт |
| lat_name_unique | varchar(100) | полное лат. имя |
| name_rus | varchar(255) | рус. название (часто пусто) |
| rus_name_unique | varchar(100) | |
| url_slug | varchar(100) | для URL/SEO |
| id_pp | int | ключ донорских фото → media.tmp_donor_photos.id_pp |
| usda_zone | int (CHECK 1..12) | |
| is_template | bool | один шаблон на вид (частичный uniq-индекс) |
| is_ishs_registered | bool | |
| created_at | timestamp | |

Индексы: PK, частичный uniq `(species_id) WHERE is_template`, btree по `id_pp`, `usda_zone`.
**Нет** полей статуса публикации, автора, `updated_at` (см. «Решения»).

**plant_synonyms** (106) — `synonym_name`, ровно один таргет из `genus_id`/`species_id`/`plant_id`
(CHECK ≤1), `is_binomial`, `synonym_lang` enum(Русский/Латинский/Оригинальный),
`synonym_type` enum(Альтернативное/Перевод/Транслит/Народное/Устаревшее/Торговое),
`full_name` (поддерживается триггером). PG-типы: `plant.synonym_lang_enum`, `plant.synonym_type_enum`.

**dict_colors** (12) — `id`, `color_name` uniq, `color_hex`.

## `plant_info` — характеристики (PK = `id_plant` = FK → plants, 1:1)

**plant_visual** (12 371) — числовые `height_max_cm`/`diameter_max_cm`/`annual_growth_cm`,
`is_thorny` bool, `flowering_duration` varchar(**100% NULL**), `flower_form` varchar;
**jsonb-массивы**: `leaf_shape`, `vegetation_periods`, `habit_forms`, `flower_colors`,
`leaf_colors`, `flowering_months`. Индексы: btree по размерам, GIN по части jsonb.

**plant_care** (12 371) — jsonb `sun`/`soil_acid`/`propagation`/`care_level`; bool
`soil_demanding`, `care_city`, `care_disease_resistant`, `care_pest_resistant`,
`care_no_shelter_boolean`, `care_no_digging_boolean`, `care_no_watering_boolean`.

**plant_design** (12 371) — jsonb `design_uses`/`garden_styles`/`designer`/`fruit_uses`/`fruiting_months`;
bool `is_toxic`, `has_aroma`, `is_self_fertile`, `is_allergen`, `has_decorative_bark`, `has_decorative_fruit`.

**plant_descriptions** (12 370) — text `content_text`, `requirements`, `problems`,
`diseases_pests`, `propagation`, `usage_info`, `interesting_facts`.

**dict_months** (13) — `id`, `month_name` uniq (12 месяцев + «Круглогодично»).

## `media`

**plant_photos** (**0 — пусто!**) — `id`, `plant_id` → plants (CASCADE), `storage_key` (под S3),
`public_url` NOT NULL, `preview_url`, `source_type` (def 'donor'), `is_main`, `created_at`. Целевая
таблица для миграции фото (этап 4).

**tmp_donor_photos** (13 116) — `id_pp`, `raw_urls` (ссылки вида poiskplant.ru/wp-content/...), `title`.
Исходные донорские фото; связь plants.id_pp → id_pp.

## `user_info`

**users** (1) — `id` PK, `first_name` NOT NULL, `email` uniq NOT NULL, `login` uniq NOT NULL,
`password_hash` NOT NULL, `nickname` uniq, `phone` uniq, `social_provider`
(CHECK: VK/TG/Гугл/Макс), `social_id`, `store_name` (торговец, Фаза 2), `role_id` →
dict_roles (RESTRICT, NOT NULL), `created_at`/`updated_at` tz, `city_id`/`district_id`.

**dict_roles** (5), **dict_regions** / **dict_cities** / **dict_districts** — гео-иерархия
(регион → город → район; FK с CASCADE/SET NULL).

## Нормализация jsonb → справочники + связи (✅ выполнено, согласовано)

jsonb-массивы вынесены в новые **Django-managed** таблицы в схеме `plant_info`
(существующие таблицы и jsonb-колонки не тронуты — оставлены для отката до релиза).
Создаются миграцией `catalog/0002`, наполняются идемпотентной командой
`manage.py normalize_catalog`.

Новые справочники: `dict_leaf_shapes` (12), `dict_habit_forms` (9), `dict_flower_forms`
(18), `dict_sun_types` (3, +«Тень» на будущее), `dict_soil_acidity` (3),
`dict_propagation_methods` (7), `dict_care_levels` (3), `dict_design_uses` (26),
`dict_garden_styles` (6), `dict_designers` (3), `dict_fruit_uses` (7). Цвета и месяцы
переиспользуют существующие `plant.dict_colors` / `plant_info.dict_months`.

Связующие таблицы (plant ↔ значение, `id_plant` + `*_id`, uniq):
`plant_leaf_shapes`, `plant_habit_forms`, `plant_flower_forms`, `plant_sun_types`,
`plant_soil_acidity`, `plant_propagation_methods`, `plant_care_levels`,
`plant_design_uses`, `plant_garden_styles`, `plant_designers`, `plant_fruit_uses`,
`plant_flower_colors`, `plant_leaf_colors`, `plant_vegetation_periods`,
`plant_flowering_months`, `plant_fruiting_months`.

**Чистка при переносе (выполнена):** объединены дубли `garden_styles` («природный»,
«природный, пейзажный» → «природный/пейзажный»); опечатки `flower_form`
(«асимметричый» → «асимметричный») и `design_uses` («для укрепление склона» →
«…укрепления…»); slash-строки `flower_form` разбиты на канонические формы; аномалия
`leaf_colors` (`id_plant=11594` = int 1) → «Белый». Все значения сконвертированы (0
потерь). Фасетные счётчики проверены: освещение Солнце 10 939 / Полутень 8 110.

> Оригинальные jsonb-колонки остаются в `plant_visual/care/design` до релиза (откат),
> после релиза удаляются отдельной миграцией.

## Решения (статус)

Заказчик делегировал решения исполнителю; принято:

- ✅ Нормализация jsonb → справочники + связи — **выполнена** (см. выше).
- ✅ `sun` — «Тень» добавлена в справочник (на будущее, данных нет).
- ✅ `designer` — заведён `dict_designers`, будет фильтром на фронте.
- ✅ `care_level` — оставлены значения «Низкие/Средние/Высокие».
- ✅ `fruit_uses` — название поля сохранено; в UI подписывается «практическое применение».
- ⏳ `flowering_duration` — поле сохранено, **но в дампе пусто у всех карточек**; ждём
  от заказчика: значения где-то есть (перевыгрузить) или пока не заполнялись.
- ⏳ Новые колонки `plants`: `status` (draft/published), `author_id` → `user_info.users`,
  `updated_at` — сделать вместе с интеграцией пользователей (этап 3). На фильтры не влияют.
