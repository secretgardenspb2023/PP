# Деплой PoiskPlant (production)

Серверная обвязка готова к развёртыванию, как только будет VPS + домен + S3.
Всё внутреннее (PG/Redis/ES/backend/imgproxy) не публикуется наружу — порты 80/443
открывает только Nginx.

## 0. Подготовка сервера (ТЗ 1.1–1.3)
Ubuntu 24.04: sudo-пользователь, SSH по ключу, отключить root/парольный вход,
нестандартный SSH-порт, автообновления безопасности. Firewall (UFW): только SSH/80/443.
Fail2ban для SSH/Nginx. Установить Docker + Docker Compose.

## 1. Конфигурация
```bash
git clone <repo> /opt/poiskplant && cd /opt/poiskplant
cp .env.example .env && nano .env          # заполнить секреты (см. ниже)
```
В `.env` для прода: `DJANGO_SECRET_KEY`, `DJANGO_ALLOWED_HOSTS`, `DOMAIN`,
`STAGING_DOMAIN`, `DATABASE_URL`/`POSTGRES_*`, `AWS_*` (S3), `IMGPROXY_KEY/SALT`,
SMTP, OAuth-ключи, `SENTRY_DSN`, `BACKUP_S3_BUCKET`, `BACKUP_GPG_PASSPHRASE`.

## 2. SSL (Let's Encrypt, ТЗ 1.5)
```bash
mkdir -p infra/certbot/www infra/certbot/conf
# поднять nginx по 80, затем выпустить сертификат:
docker compose -f infra/docker-compose.prod.yml --env-file .env run --rm certbot \
  certonly --webroot -w /var/www/certbot -d "$DOMAIN" -d "$STAGING_DOMAIN"
```

## 3. Basic Auth для staging (ТЗ 1.12)
```bash
htpasswd -c infra/nginx/.htpasswd reviewer
```

## 4. Запуск
```bash
cd infra
docker compose -f docker-compose.prod.yml --env-file ../.env up -d --build
docker compose -f docker-compose.prod.yml exec backend python manage.py createsuperuser
```
Бэкенд сам прогоняет `migrate` и `collectstatic` (entrypoint `prod`).

## 5. Данные каталога
```bash
# загрузить дамп заказчика, затем:
docker compose -f docker-compose.prod.yml exec backend python manage.py normalize_catalog
docker compose -f docker-compose.prod.yml exec backend python manage.py es_reindex
```

## 6. Бэкапы (ТЗ 1.10)
`infra/backup/backup.sh` — шифрованный pg_dump → S3, ротация 7/4/12, тест-восстановление.
Cron:
```
30 3 * * *  /opt/poiskplant/infra/backup/backup.sh backup       >> /var/log/poiskplant-backup.log 2>&1
0  4 1 * *  /opt/poiskplant/infra/backup/backup.sh restore-test  >> /var/log/poiskplant-backup.log 2>&1
```

## Что осталось вне этой обвязки
- VPS/домен/S3-доступы — от заказчика.
- Frontend (этап 6) — раскомментировать сервис `frontend` и переключить `location /` в nginx.
- Мониторинг (UptimeRobot/Sentry/алерты в Telegram) — этап 1.11.
