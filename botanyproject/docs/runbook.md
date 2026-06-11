# Runbook PoiskPlant

Типовые операции и реакция на инциденты. Растёт по ходу проекта.

## Локальная разработка

```bash
docker compose up --build           # поднять стек
docker compose logs -f backend      # логи backend
docker compose exec backend bash    # шелл в контейнере
docker compose down                 # остановить (данные в volume сохраняются)
docker compose down -v              # снести вместе с данными
```

## Частые команды Django

```bash
docker compose exec backend python manage.py migrate
docker compose exec backend python manage.py makemigrations
docker compose exec backend python manage.py createsuperuser
docker compose exec backend python manage.py shell
docker compose exec backend pytest
```

## Загрузка дампа клиента в dev-БД

Дамп лежит в корне (`dump-*.sql`, gitignored — данные заказчика). Залить в dev-БД:

```bash
docker compose exec -T postgres psql -U poiskplant -d poiskplant < dump-botany_db-202606041900.sql
```

Ошибки `schema ... already exists` и `role "postgres" does not exist` — безобидны
(схемы предсозданы init-скриптом; GRANT/OWNER на чужую роль пропускаются). Проверка:
`docker compose exec -T backend python manage.py shell -c "from apps.catalog.models import Plant; print(Plant.objects.count())"` → 12371.

## Elasticsearch-индекс

```bash
docker compose exec backend python manage.py es_reindex   # пересобрать индекс из БД
```

Поиск: `GET /api/v1/search/?q=…` (морфология + опечатки + подсветка),
`GET /api/v1/search/suggest/?q=…` (автоподсказки). При недоступности ES — авто-fallback
на PostgreSQL. Встроенный русский стеммер; для полноценной лемматизации можно поставить
плагин `analysis-morphology` в образ ES (не входит в сток).

## Нормализация характеристик (jsonb → справочники + связи)

Идемпотентно (можно гонять повторно). `--flush` пересобирает с нуля:

```bash
docker compose exec backend python manage.py normalize_catalog          # дозаполнить
docker compose exec backend python manage.py normalize_catalog --flush  # пересобрать
```

Команда чистит опечатки/дубли и логирует всё, что не сконвертировалось.

## Тесты и БД

`pytest` создаёт тестовую БД только если тест запрашивает БД-фикстуру. Тесты, читающие
каталог, требуют **загруженного дампа** (таблицы `plant.*`/`plant_info.*` — `managed=False`,
создаются дампом, а не миграциями). На чистой БД миграция `catalog/0002` не накатится
(`schema "plant_info" does not exist`) — это by design dump-based workflow из ТЗ; staging/prod
и dev работают на копии дампа, где схемы есть. CI гоняет `check` + `makemigrations --check` +
pytest (health-тест без БД).

## Health-check

`GET /api/v1/health/` — возвращает статус БД, Redis, Elasticsearch, S3.
HTTP 200 — всё ок; 503 — есть деградировавшая зависимость (см. тело ответа).

## Инциденты (заполняется по мере появления prod-окружения)

- Контейнер не стартует → `docker compose logs <service>`.
- ES не отвечает → поиск падает в fallback на `pg_trgm` (этап 5), индекс перестроить
  `python manage.py search_index --rebuild` (после настройки ES).
- Восстановление БД из бэкапа → раздел появится после настройки бэкапов (этап 1, сервер).
