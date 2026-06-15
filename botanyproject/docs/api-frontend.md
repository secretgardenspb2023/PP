# PoiskPlant — API для фронтенда

Контракт REST API для разработки клиента (Next.js, этап 6). Все примеры — реальные ответы.

## База

- **Base URL:** `http://5.101.0.240/api/v1` (прод сейчас, HTTP) → станет `https://staging.poiskplant.ru/api/v1` после домена.
  Локально: `http://localhost:8000/api/v1`.
- **Формат:** JSON (`Content-Type: application/json`).
- **Машинная схема (OpenAPI):** `GET /api/v1/schema/` — можно импортировать в Postman/Insomnia или сгенерировать типы/клиент.
- **CORS:** разрешённые origin фронта задаются на бэке (`CORS_ALLOWED_ORIGINS`). Локальный `http://localhost:3000` уже разрешён; для других — скажи origin, добавлю.

---

## Каталог

### `GET /plants/` — список карточек
Пагинация + фильтры + сортировка.

**Query-параметры:**

| Параметр | Пример | Что делает |
|----------|--------|------------|
| `page` | `2` | страница (по 24) |
| `sort` | `name` / `-name` / `new` / `old` / `id` | сортировка (name = по латинскому имени) |
| `q` | `абелия` | текстовый поиск (имя/таксономия) |
| `usda_zone` | `4,5,6` | зоны USDA (через запятую = ИЛИ) |
| `height_min` / `height_max` | `50` / `200` | высота, см (диапазон). Аналогично `diameter_*`, `growth_*` |
| **измерения** (мультивыбор) | `sun=Солнце,Полутень` | через запятую — **ИЛИ внутри**; разные параметры — **И между** |

**16 измерений-фильтров** (значения брать из `/facets/`):
`leaf_shape`, `habit_form`, `flower_form`, `sun`, `soil_acid`, `propagation`, `care_level`,
`design_use`, `garden_style`, `designer`, `fruit_use`, `flower_color`, `leaf_color`,
`vegetation_period`, `flowering_month`, `fruiting_month`.

Пример: `GET /plants/?sun=Солнце&height_min=50&height_max=200&flower_color=Белый&sort=name&page=1`

**Ответ:**
```json
{
  "count": 12371,
  "next": "http://.../api/v1/plants/?page=2&sort=name",
  "previous": null,
  "results": [
    {
      "id_plant": 12226,
      "url_slug": "abelia-chinensis-",
      "name": "Abelia chinensis ",
      "name_rus": "",
      "lat_name_unique": "Abelia chinensis ",
      "usda_zone": 5,
      "species": "chinensis",
      "genus": "Abelia",
      "family": "Caprifoliaceae",
      "main_photo": null
    }
  ]
}
```
> `main_photo` пока `null` — фото подключатся после миграции в S3 (этап 4). `name` = `name_rus` или латинское, если русского нет.

### `GET /plants/{id}/` — детальная карточка
`id` = `id_plant`.

**Ответ (сокращённо):**
```json
{
  "id_plant": 4,
  "url_slug": "abeliophyllum-distichum-",
  "name": "Abeliophyllum distichum ",
  "name_rus": "",
  "lat_name_unique": "Abeliophyllum distichum ",
  "variety": "",
  "rus_name_unique": "Абелиолистник двурядный",
  "usda_zone": 5,
  "is_template": true,
  "is_ishs_registered": false,
  "created_at": "2026-05-17T11:09:27+03:00",
  "taxonomy": {
    "species": "distichum", "species_rus": "двурядный",
    "genus": "Abeliophyllum", "genus_rus": "Абелиолистник",
    "family_lat": "Oleaceae", "family_rus": "Маслиновые"
  },
  "characteristics": {
    "leaf_shapes": ["овальный/яйцевидный"],
    "habit_forms": ["раскидистая"],
    "flower_forms": ["простой", "звезчатый"],
    "flower_colors": ["Белый"],
    "leaf_colors": ["Зеленый"],
    "vegetation_periods": ["Май","Июнь","Июль","Сентябрь","Октябрь"],
    "flowering_months": ["Апрель","Май"],
    "fruiting_months": [],
    "sun": ["Солнце"],
    "soil_acidity": ["Нейтральная","Кислая","Щелочная"],
    "propagation": ["Зеленый черенок","Одревесневший черенок"],
    "care_levels": ["Низкие"],
    "design_uses": ["весенний акцент"],
    "garden_styles": ["природный/пейзажный"],
    "designers": [],
    "fruit_uses": [],
    "height_max_cm": 150, "diameter_max_cm": 150, "annual_growth_cm": 20,
    "is_thorny": false,
    "soil_demanding": false, "disease_resistant": false, "pest_resistant": false, "no_shelter": false,
    "is_toxic": false, "has_aroma": true, "is_self_fertile": false,
    "is_allergen": false, "has_decorative_bark": false, "has_decorative_fruit": false
  },
  "descriptions": {
    "content": "…", "requirements": "…", "problems": "…",
    "diseases_pests": "…", "propagation": "…", "usage": "…", "interesting_facts": "…"
  },
  "synonyms": [
    {"synonym_name": "…", "full_name": "…", "synonym_lang": "Русский", "synonym_type": "Народное", "is_binomial": false}
  ],
  "photos": []
}
```

### `GET /plants/facets/` — значения и счётчики для фильтров
Возвращает по каждому из 16 измерений список `{value, count}` с учётом остальных активных фильтров
(маркетплейс-стиль: выбор значения не обнуляет соседей). Принимает те же query-параметры, что и `/plants/`.

```json
{
  "sun": [{"value": "Солнце", "count": 10939}, {"value": "Полутень", "count": 8110}],
  "care_level": [{"value": "Средние", "count": 5239}, {"value": "Низкие", "count": 4956}, {"value": "Высокие", "count": 2146}],
  "leaf_shape": [ ... ], "flower_color": [ ... ], "...": []
}
```
> Используй для построения панели фильтров: ключ объекта = имя параметра фильтра, `value` = что слать в `/plants/`.

### `GET /plants/histograms/` — распределения для диапазонных фильтров (слайдеры)
По каждому диапазону (`height`, `diameter`, `growth`) — `min`/`max` и 8 столбиков `{from, to, count}`
с учётом остальных активных фильтров (своя ось не учитывается, чтобы движение слайдера не ломало
его собственную гистограмму). Принимает те же query-параметры, что и `/plants/`.
```json
{
  "height": {"min": 10, "max": 2000, "buckets": [{"from": 10.0, "to": 258.8, "count": 10312}, ...]},
  "diameter": {"min": 3, "max": 1500, "buckets": [ ... ]},
  "growth": {"min": 5, "max": 70, "buckets": [ ... ]}
}
```
> Слать в `/plants/` как `height_min`/`height_max` и т.д.

---

## Поиск

### `GET /search/?q=…&page=1` — полнотекстовый (Elasticsearch)
Морфология, опечатки, подсветка. Fallback на PostgreSQL, если ES недоступен.
```json
{
  "engine": "elasticsearch",
  "count": 3047,
  "results": [
    {
      "id_plant": 10099,
      "url_slug": "ribes-uva-crispa-белые-ночи",
      "name": "Белые ночи",
      "lat_name": "Ribes uva-crispa Белые ночи",
      "family": "Grossulariaceae",
      "score": 28.04,
      "highlight": {"name_rus": ["<mark>Белые</mark> ночи"]}
    }
  ]
}
```

### `GET /search/suggest/?q=…` — автоподсказки (edge-ngram, debounce 200мс на фронте)
```json
[
  {"id_plant": 10847, "url_slug": "syringa-vulgaris-abel-carriere", "name": "Abel Carriere"},
  {"id_plant": 4, "url_slug": "abeliophyllum-distichum-", "name": "Abeliophyllum distichum "}
]
```

---

## Авторизация `/auth/`

**Схема (ТЗ 3.4):** при логине бэк возвращает **`access`-токен в теле** + ставит **`refresh` в HttpOnly-cookie**
(на путь `/api/v1/auth/`). Фронт:
- хранит `access` в памяти (не в localStorage), шлёт в заголовке `Authorization: Bearer <access>`;
- для эндпоинтов с cookie (`login`/`token/refresh`/`logout`) — `fetch(..., { credentials: 'include' })`;
- при `401` зовёт `POST /auth/token/refresh/` (cookie сам подставится) → получает новый `access`.

| Метод | Путь | Тело / примечание | Ответ |
|-------|------|-------------------|-------|
| POST | `/auth/register/` | `{email, password, full_name, captcha_token?}` | `201 {detail}` (письмо с подтверждением) |
| POST | `/auth/verify-email/` | `{uid, token}` (из ссылки в письме) | `200 {detail}` |
| POST | `/auth/login/` | `{email, password, otp?}` | `200 {access, user}` + cookie. `401 {otp_required:true}` если включена 2FA |
| POST | `/auth/token/refresh/` | — (refresh из cookie) | `200 {access}` |
| POST | `/auth/logout/` | — | `200`, чистит cookie |
| GET | `/auth/me/` | `Authorization: Bearer` | `{id, email, full_name, is_active, is_staff, date_joined, social_provider}` |
| PATCH | `/auth/me/` | `Bearer` + `{full_name?, phone?}` | `200` обновлённый профиль |
| GET / DELETE | `/auth/me/socials/` | `Bearer` | список привязок `{linked:[{provider, social_id}], has_password}`; DELETE — отвязать |
| GET / DELETE | `/auth/me/sessions/` | `Bearer` | активные сессии `{sessions:[{jti, created_at, expires_at}]}`; DELETE — завершить все |
| POST | `/auth/password/reset/` | `{email, captcha_token?}` | `200` (всегда, без раскрытия) |
| POST | `/auth/password/reset/confirm/` | `{uid, token, new_password}` | `200 {detail}` |
| GET | `/auth/google/` | — | `302` редирект на Google → callback вернёт на фронт `…/auth/callback?status=ok` (cookie уже стоит, зови `token/refresh`) |
| POST | `/auth/telegram/` | данные Telegram Login Widget (`id, first_name, …, hash`) | `200 {access, user}` |
| GET | `/auth/vk/` | — | `302` редирект на VK → callback вернёт на фронт `…/auth/callback?status=ok` (cookie уже стоит, зови `token/refresh`); `503` если VK не настроен |
| POST | `/auth/2fa/setup/` · `/confirm/` · `/disable/` · `/status/` | `Bearer` (+ `{otp}` где нужно) | настройка TOTP |

**SmartCaptcha:** сейчас выключена (`SMARTCAPTCHA_ENABLED=false`) — поле `captcha_token` можно не слать. На проде включим; client key для виджета: `ysc1_…` (дам отдельно).

---

## На заметку фронту
- Изображения (`main_photo`, `photos`) — пусто, пока фото не мигрированы в S3 (этап 4); рендери плейсхолдер.
- Telegram-кнопка и Google-редирект полноценно заработают на **живом домене** (не localhost).
- Числовые диапазоны для слайдеров/гистограмм: `height_max_cm`, `diameter_max_cm`, `annual_growth_cm`, `usda_zone`.
- Полный перечень полей и схем — в OpenAPI (`/api/v1/schema/`).
