#!/usr/bin/env bash
# PoiskPlant liveness probe -> /var/log/poiskplant-health.log
# Telegram alert sent if TELEGRAM_ALERT_CHAT_ID is set in /opt/PP/botanyproject/.env
# Креды читаем построчно из .env (источать весь .env нельзя — там docker-значения,
# не все валидны для shell). Секреты остаются только в .env (gitignored).
ENV=/opt/PP/botanyproject/.env
_env(){ grep -E "^$1=" "$ENV" 2>/dev/null | head -1 | cut -d= -f2-; }
HEALTHCHECK_AUTH=$(_env HEALTHCHECK_AUTH)
TELEGRAM_BOT_TOKEN=$(_env TELEGRAM_BOT_TOKEN)
TELEGRAM_ALERT_CHAT_ID=$(_env TELEGRAM_ALERT_CHAT_ID)
LOG=/var/log/poiskplant-health.log
CODE=$(curl -sk -o /dev/null -w "%{http_code}" --resolve staging.poiskplant.ru:443:127.0.0.1 \
       -u "${HEALTHCHECK_AUTH}" https://staging.poiskplant.ru/api/v1/health/ 2>/dev/null)
TS=$(date "+%F %T")
if [ "$CODE" = "200" ]; then
  echo "$TS OK" >> "$LOG"
else
  echo "$TS DOWN http=$CODE" >> "$LOG"
  if [ -n "${TELEGRAM_ALERT_CHAT_ID:-}" ] && [ -n "${TELEGRAM_BOT_TOKEN:-}" ]; then
    curl -s "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
      -d chat_id="${TELEGRAM_ALERT_CHAT_ID}" \
      --data-urlencode text="PoiskPlant DOWN (http=$CODE) $TS" >/dev/null || true
  fi
fi
