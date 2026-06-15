# Промпт для генерации фронтенда PoiskPlant

> Скопируйте всё, что ниже разделителя, и вставьте в другую ИИ.

---

Ты — senior frontend-инженер. Построй современный, production-ready фронтенд для **PoiskPlant** — электронного справочника растений (~12 000 карточек). Дизайн в Figma сейчас черновой — улучшай и модернизируй внешний вид, но строго придерживайся брендовых токенов и структуры данных ниже. Язык интерфейса — **русский**. Маркетплейс/объявления — **вне scope** (только справочник).

## 1. Стек и архитектура (обязательно)

- **Next.js 16 (App Router) + TypeScript + Tailwind CSS v4** (CSS-first: токены в `@theme` в `globals.css`, без `tailwind.config.js`).
- Шрифты через `next/font/google`: **Rubik** (заголовки) и **Noto Sans** (текст), `subsets: ["latin","cyrillic"]`.
- Данные тянуть **на сервере** (Server Components, SSR/streaming) для SEO; интерактив (фильтры, поиск, авторизация) — Client Components.
- Состояние фильтров/поиска/пагинации — **в URL** (searchParams), чтобы страницы шарились и индексировались.
- Сборка под контейнер: `output: "standalone"`, Dockerfile (multi-stage Node 20-alpine).
- Доступность (a11y), адаптив mobile-first (брейкпоинты ~360 / 768 / 1024 / 1440), skeleton-загрузки, аккуратные пустые состояния и состояния ошибок, микро-анимации.
- Цель производительности: PageSpeed Mobile 90+ на главной, каталоге, карточке.

### Доступ к API
- Базовый путь API: **`/api/v1`** (относительный — браузер и SSR ходят на тот же origin через nginx; так же работает auth-cookie).
- Для SSR используйте серверную переменную `API_BASE` (внутренний адрес, напр. `http://backend:8000/api/v1`); для браузера — `NEXT_PUBLIC_API_BASE=/api/v1`.
- ⚠️ В серверных fetch добавляйте заголовок `X-Forwarded-Proto: https` (иначе backend сделает 302-редирект на https внутри сети).

## 2. Брендовые дизайн-токены (из Figma UI-kit)

Цвета (имена → HEX):
- brand `#56B76B` (основной зелёный), brand-light `#70E68A` (hover), brand-dark `#30623B` (pressed/акценты)
- disabled `#A9C2AF`, danger/red `#F63131` (ошибки, «краснокнижный»), warning/yellow `#D6D801`
- ink (основной текст) `#303030`, muted (вторичный) `#898989`, accent-ink `#616161`
- grey-20 `#C8C8C8`, surface (фон секций) `#F7F7F7`, line (границы) `#D9D9D9`, white `#FFFFFF`

Типографика (Rubik — заголовки H1/H2; Noto Sans — остальное):
- H1 40/47 w700, H2 32/38 w700, H3 28/38 w600, H4 20/27 w600
- mobile: H1 32/38, H2 26/31, H3 24/33
- body 16/22 w400, primary 18/25 w500, accent 20/27 w500/600, tertiary 14/19 w400
- letter-spacing 0 везде

Сетка/контейнер: десктоп контейнер **1140px**, 12 колонок, gutter 20px. Радиусы: 8/12 (карточки), 25 (кнопки/пилюли), pill (круглые). Мягкие тени на hover карточек.

Стиль: чистый «ботанический», много воздуха, крупные фото, зелёные акценты, скруглённые кнопки-пилюли, аккуратные чипы для тегов/характеристик. Сделай красиво и современно (не как черновик).

## 3. API-контракт (точные формы ответов)

**Каталог (список):** `GET /plants/?q=&sort=&page=&<фильтры>`
```
{ count, next, previous, results: [
  { id_plant, url_slug, name, name_rus, lat_name_unique, usda_zone,
    species, genus, family, main_photo } ] }
```
- `name` — готовое отображаемое имя (рус, с фолбэком). `main_photo` — URL (imgproxy, может быть null → плейсхолдер-лист). Деталь открывать по **`id_plant`**: `/plant/{id_plant}`.
- `sort`: `name` | `-name` | `new` | `old`. Пагинация — по `next`/`previous` (или `page`).

**Фильтры (query-параметры, мультизначения через запятую):** `sun, soil_acid, care_level, habit_form, flower_form, leaf_shape, flower_color, leaf_color, propagation, design_use, garden_style, fruit_use, vegetation_period, flowering_month, fruiting_month, designer`; диапазоны `height_min/height_max, diameter_min/diameter_max, growth_min/growth_max`; `usda_zone` (через запятую); булевы `is_thorny, is_toxic, has_aroma`.

**Фасеты (счётчики, учитывают активные фильтры):** `GET /plants/facets/?<фильтры>`
```
{ "<dim>": [ { value, count }, ... ], ... }   // 16 измерений как выше
```
Рисуй сайдбар фильтров из фасетов (чекбоксы со счётчиками; на мобиле — выезжающая панель). Диапазонные фильтры (высота/диаметр/прирост) — со слайдером и, если возможно, гистограммой распределения.

**Карточка (деталь):** `GET /plants/{id_plant}/`
```
{ id_plant, url_slug, name, name_rus, lat_name_unique, variety, rus_name_unique,
  usda_zone, is_template, is_ishs_registered, created_at,
  taxonomy: { species, species_rus, genus, genus_rus, family_lat, family_rus },
  characteristics: {
    // массивы строк:
    habit_forms[], leaf_shapes[], flower_forms[], flower_colors[], leaf_colors[],
    sun[], soil_acidity[], care_levels[], propagation[],
    vegetation_periods[], flowering_months[], fruiting_months[],
    design_uses[], garden_styles[], fruit_uses[], designers[],
    // числа:
    height_max_cm, diameter_max_cm, annual_growth_cm,
    // булевы (показывать как чип, если true):
    is_thorny, is_toxic, is_allergen, has_aroma, is_self_fertile,
    has_decorative_bark, has_decorative_fruit, soil_demanding,
    disease_resistant, pest_resistant, no_shelter, city_tolerant, no_digging, no_watering },
  descriptions: { requirements, problems, diseases_pests, propagation, usage },
  synonyms: [ { synonym_name, full_name, synonym_lang, synonym_type, is_binomial,
               level: "genus"|"species"|"plant" } ],
  photos: [ { id, public_url, preview_url, is_main, source_type } ] }
```

**Поиск (морфология/опечатки/синонимы):** `GET /search/?q=&page=`
```
{ count, engine, results: [ { id_plant, url_slug, name, lat_name, family, score,
                              highlight } ] }
```
**Автоподсказки:** `GET /search/suggest/?q=` → `[ { id_plant, url_slug, name } ]` (вызывать с дебаунсом ≥2 символов; выпадающий список под строкой поиска).

**Авторизация:** база `/api/v1/auth/`
- `POST /login/` `{email,password}` → `{access}` + ставит HttpOnly refresh-cookie. `POST /token/refresh/` → `{access}`. `GET /me/` (заголовок `Authorization: Bearer <access>`). `POST /logout/`.
- `POST /register/` `{email,full_name,password}` → письмо с подтверждением (аккаунт неактивен до verify). `POST /verify-email/` `{token}` (токен из ссылки письма).
- OAuth: кнопка Google → редирект на `/api/v1/auth/google/`; Telegram-виджет (по желанию).
- Паттерн: access в памяти; на старте приложения вызвать `token/refresh` → если ок, подтянуть `me`. Все fetch — `credentials: "include"`.

## 4. Экраны (реализовать все)

1. **Главная** — герой с крупным поиском (с автоподсказками), краткое описание (12 000+ карточек, поиск по рус/лат с морфологией), блок-витрина растений из API, быстрый вход в каталог и в алфавитный навигатор. Шапка: лого PoiskPlant (листик + вордмарк), поиск, выбор города (пресентационно), меню (Каталог, Алфавит, О проекте), Вход/Регистрация (или имя/Выход, если залогинен — динамически). Подвал.
2. **Каталог** `/catalog` — слева фасетные фильтры (16 измерений со счётчиками, мультивыбор; диапазоны со слайдером/гистограммой; сброс), сверху строка поиска + сортировка + счётчик «Найдено N», сетка карточек (фото/плейсхолдер, имя рус + латынь курсивом, семейство, зона USDA, бейдж «Краснокнижный» если применимо), пагинация. На мобиле фильтры — в выезжающей панели (кнопка «Фильтры»). Состояние — в URL.
3. **Карточка растения** `/plant/[id]` — галерея фото (главное + миниатюры; форматы отдаёт imgproxy — просто `<img>`), заголовок (рус-имя) + латынь, чипы-флаги (Ядовито, Ароматное, Краснокнижный и т.д.), блок таксономии (семейство рус+лат, род, вид), **«матрица характеристик»** сгруппированная по смыслу: Общие/Визуал (форма роста, листа, цветка, цвета, размеры, месяцы цветения/плодоношения, вегетация), Уход (освещение, почва, кислотность, размножение, уровень ухода, зимостойкость/город/полив), Дизайн (использование, стили сада, плоды). Затем текстовые блоки `descriptions` (Требования, Проблемы, Болезни и вредители, Размножение, Использование). Затем **синонимы**, сгруппированные по уровню (Род / Вид / Растение). Хлебные крошки, кнопка «назад в каталог», блок похожих растений (того же рода/семейства — можно через `/plants/?q=` или фильтр).
4. **Алфавитный навигатор** — выбор буквы (рус/лат) → список растений, начинающихся на букву (через каталог с параметром или поиск). Был в Figma.
5. **Авторизация:** `/login` (email+пароль, кнопка Google, ссылки на регистрацию и сброс пароля), `/register` (имя, email, пароль; экран «проверьте почту»), `/verify-email` (по токену из URL), сброс пароля, `/profile` (личный кабинет: данные пользователя, выход; защищён — редирект на /login для гостя).

## 5. SEO и качество
- Уникальные `<title>`/`<meta description>`/Open Graph на каждой странице (карточка — по имени растения).
- Schema.org разметка карточки растения. Хлебные крошки (BreadcrumbList).
- Семантическая разметка, alt у изображений, фокус-стейты, контраст ≥ AA.
- `loading.tsx`/Suspense со skeleton, `not-found.tsx`, обработка ошибок API (дружелюбные сообщения).
- Чистый, типизированный код; переиспользуемые компоненты (PlantCard, Chip, FacetGroup, SearchBar, Pagination и т.п.); единый слой API-клиента с типами.

## 6. Что отдать
- Полная структура `src/app` (роуты) + `src/components` + `src/lib/api.ts` (типы по контракту выше) + `globals.css` с токенами в `@theme` + `layout.tsx` со шрифтами.
- Dockerfile (standalone) и краткий README: как запустить локально (`npm run dev`, переменные `API_BASE`/`NEXT_PUBLIC_API_BASE`).
- Адаптив проверить на 360/768/1440.

Сделай дизайн заметно лучше черновика: продуманная типографика, сетка, отступы, карточки с тенями, аккуратные фильтры, приятные ховеры — но в рамках брендовых токенов (зелёная палитра, Rubik+Noto, скругления).
