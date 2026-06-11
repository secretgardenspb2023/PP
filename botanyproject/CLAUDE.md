# PoiskPlant — гайд для Claude Code

Электронный справочник растений (~12 371 карточка), коммерческая разработка по этапам.
ТЗ: [plant_directory_tz_v2.2.md](plant_directory_tz_v2.2.md). Прогресс: [docs/architecture.md](docs/architecture.md).

## Стек и раскладка

- `backend/` — Django 5.2 + DRF (config/ + apps/{core,accounts,catalog}); venv для тулинга в `backend/.venv`.
- `frontend/` — Next.js 15 (этап 6, ещё нет).
- `infra/` — postgres init, nginx (деплой). `docs/` — архитектура, БД, runbook.
- PostgreSQL 17, Elasticsearch 8, Redis 7, S3 (Yandex) + imgproxy — всё в Docker.

## Команды (dev)

```bash
docker compose up --build                         # поднять стек
docker compose exec backend python manage.py ...  # manage-команды
docker compose exec backend pytest                # тесты
backend/.venv/Scripts/python.exe manage.py check  # быстрый чек без Docker (нужен DATABASE_URL в env)
```

Точки: health `/api/v1/health/`, admin `/admin/`, swagger `/api/v1/schema/swagger-ui/`.

## Окружение и правила

- Windows 11 + PowerShell 5.1 (Bash тоже есть). Shell-скрипты — LF (см. .gitattributes).
- Общаться по-русски. Временные файлы — в `scratch/`, не в корне.
- **Секреты только в `.env`** (gitignored), шаблон — `.env.example`. Реальные ключи даёт заказчик.
- Изменения схемы БД — только по согласованию с заказчиком, через миграции, с обновлением docs/database.md (ТЗ раздел 5).
- Блокеры (дамп `plant.plants`, VPS, OAuth, S3, Figma) — см. docs/architecture.md.
- Долгосрочные факты — в моей памяти (`~/.claude/projects/c--ractenie/memory/MEMORY.md`).
