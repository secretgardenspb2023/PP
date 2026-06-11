# PoiskPlant

Электронный справочник растений (~12 371 карточка). Новая версия на современном
стеке взамен текущего WordPress/WooCommerce сайта.

Полное ТЗ: [plant_directory_tz_v2.2.md](plant_directory_tz_v2.2.md).
Анализ и план схемы БД: [poiskplant_db_schema_proposal_v2.md](poiskplant_db_schema_proposal_v2.md).

## Стек

| Слой        | Технология                                              |
|-------------|---------------------------------------------------------|
| Backend     | Django 5.2 (LTS) + Django REST Framework                |
| Frontend    | Next.js 15 (App Router) + TypeScript + Tailwind + shadcn |
| БД          | PostgreSQL 17                                           |
| Поиск       | Elasticsearch 8 (морфология русского)                   |
| Кэш/брокер  | Redis 7                                                 |
| Медиа       | S3 (Yandex Object Storage) + imgproxy                   |
| Деплой      | Docker Compose, Nginx, Let's Encrypt (VPS HandyHost)    |

## Структура репозитория

```
backend/      Django-проект (config/ + apps/)
frontend/     Next.js (этап 6)
infra/        nginx, конфиги деплоя
docs/         архитектура, документация БД, runbook
.github/      CI (GitHub Actions)
```

## Локальный запуск (dev)

Требуется Docker + Docker Compose.

```bash
cp .env.example .env          # значения по умолчанию подходят для локалки
docker compose up --build     # postgres, redis, elasticsearch, backend
```

После старта:

- API health-check: <http://localhost:8000/api/v1/health/>
- Каталог: `GET /api/v1/plants/` (список, фильтры, сортировка, пагинация),
  `GET /api/v1/plants/{id}/` (карточка), `GET /api/v1/plants/facets/` (счётчики фильтров)
- Поиск: `GET /api/v1/search/?q=…` (ES: морфология+опечатки+подсветка),
  `GET /api/v1/search/suggest/?q=…` (автоподсказки)
- Авторизация: `/api/v1/auth/` — `register` · `verify-email` · `login` · `token/refresh`
  · `logout` · `password/reset[/confirm]` · `me` · `2fa/{setup,confirm,disable,status}`
  · `google[/callback]` · `telegram` (JWT + refresh-cookie; axes-антиперебор; TOTP-2FA;
  Google redirect-flow; Telegram-подпись; SmartCaptcha на регистрации/сбросе)
- Django admin: <http://localhost:8000/admin/>
- OpenAPI/Swagger: <http://localhost:8000/api/v1/schema/swagger-ui/>

Данные каталога появляются после загрузки дампа клиента и нормализации — см.
[docs/runbook.md](docs/runbook.md).

Миграции и суперпользователь:

```bash
docker compose exec backend python manage.py migrate
docker compose exec backend python manage.py createsuperuser
```

## Этапы

Реализация ведётся поэтапно по разделу 2 ТЗ. Текущий прогресс — см. [docs/architecture.md](docs/architecture.md).
