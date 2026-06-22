#!/usr/bin/env bash
#
# Encrypted PostgreSQL backups to S3 with rotation (ТЗ Этап 1.10).
#   ./backup.sh backup        # dump → gzip → gpg → S3 (daily, +weekly Sun, +monthly 1st)
#   ./backup.sh prune         # keep 7 daily / 4 weekly / 12 monthly
#   ./backup.sh restore-test  # download latest, decrypt, restore into a throwaway DB, sanity-check
#
# Cron (on the VPS):
#   30 3 * * *  /opt/poiskplant/infra/backup/backup.sh backup  >> /var/log/poiskplant-backup.log 2>&1
#   0  4 1 * *  /opt/poiskplant/infra/backup/backup.sh restore-test >> /var/log/poiskplant-backup.log 2>&1
#
# Required env (from ../../.env): POSTGRES_DB/USER/PASSWORD, AWS_* , and
# BACKUP_S3_BUCKET, BACKUP_GPG_PASSPHRASE.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMPOSE="docker compose -f ${HERE}/../docker-compose.prod.yml --env-file ${HERE}/../../.env"
# Load only the simple vars we need (avoid `source`: .env has space/special values
# like ES_JAVA_OPTS and DEFAULT_FROM_EMAIL that break shell parsing).
while IFS= read -r _line; do
  case "$_line" in
    POSTGRES_USER=*|POSTGRES_DB=*|POSTGRES_PASSWORD=*|AWS_ACCESS_KEY_ID=*|\
AWS_SECRET_ACCESS_KEY=*|AWS_S3_ENDPOINT_URL=*|AWS_S3_REGION_NAME=*|\
BACKUP_S3_BUCKET=*|BACKUP_GPG_PASSPHRASE=*) export "${_line?}" ;;
  esac
done < "${HERE}/../../.env"

: "${BACKUP_S3_BUCKET:?set BACKUP_S3_BUCKET}"
: "${BACKUP_GPG_PASSPHRASE:?set BACKUP_GPG_PASSPHRASE}"
PREFIX="s3://${BACKUP_S3_BUCKET}/backups"
STAMP="$(date +%Y%m%d-%H%M)"
NAME="poiskplant-${STAMP}.sql.gz.gpg"
ENDPOINT_OPT="--endpoint-url ${AWS_S3_ENDPOINT_URL:-https://storage.yandexcloud.net}"

aws_s3() { aws ${ENDPOINT_OPT} s3 "$@"; }

backup() {
  echo "[backup] dumping ${POSTGRES_DB} → ${PREFIX}/daily/${NAME}"
  ${COMPOSE} exec -T postgres pg_dump -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" \
    | gzip \
    | gpg --batch --yes --symmetric --cipher-algo AES256 \
          --passphrase "${BACKUP_GPG_PASSPHRASE}" \
    | aws_s3 cp - "${PREFIX}/daily/${NAME}"

  # Weekly copy on Sundays, monthly copy on the 1st.
  [ "$(date +%u)" = "7" ] && aws_s3 cp "${PREFIX}/daily/${NAME}" "${PREFIX}/weekly/${NAME}"
  [ "$(date +%d)" = "01" ] && aws_s3 cp "${PREFIX}/daily/${NAME}" "${PREFIX}/monthly/${NAME}"
  prune
}

# keep <tier> <count>: delete all but the newest <count> objects in a tier
keep() {
  local tier="$1" count="$2"
  aws_s3 ls "${PREFIX}/${tier}/" | awk '{print $4}' | sort | head -n "-${count}" \
    | while read -r obj; do
        [ -n "${obj}" ] && aws_s3 rm "${PREFIX}/${tier}/${obj}" && echo "[prune] removed ${tier}/${obj}"
      done
}

prune() {
  keep daily 7
  keep weekly 4
  keep monthly 12
}

restore_test() {
  local latest
  latest="$(aws_s3 ls "${PREFIX}/daily/" | awk '{print $4}' | sort | tail -n1)"
  : "${latest:?no backups found}"
  echo "[restore-test] verifying ${latest}"
  ${COMPOSE} exec -T postgres psql -U "${POSTGRES_USER}" -d postgres \
    -c "DROP DATABASE IF EXISTS restore_test;" -c "CREATE DATABASE restore_test;"
  aws_s3 cp "${PREFIX}/daily/${latest}" - \
    | gpg --batch --yes --decrypt --passphrase "${BACKUP_GPG_PASSPHRASE}" \
    | gunzip \
    | ${COMPOSE} exec -T postgres psql -U "${POSTGRES_USER}" -d restore_test >/dev/null
  local n
  n="$(${COMPOSE} exec -T postgres psql -U "${POSTGRES_USER}" -d restore_test -tAc \
        "SELECT count(*) FROM plant.plants;")"
  ${COMPOSE} exec -T postgres psql -U "${POSTGRES_USER}" -d postgres \
    -c "DROP DATABASE restore_test;" >/dev/null
  echo "[restore-test] OK — restored plant.plants rows: ${n}"
}

case "${1:-backup}" in
  backup)       backup ;;
  prune)        prune ;;
  restore-test) restore_test ;;
  *) echo "usage: $0 {backup|prune|restore-test}"; exit 1 ;;
esac
