#!/usr/bin/env bash
#
# Baza zaxira nusxasi.
#
# Foydalanish:
#   ./scripts/backup.sh                 # docker compose ichidagi bazadan
#   BACKUP_DIR=/mnt/backup ./scripts/backup.sh
#
# Cron bilan har kuni soat 3 da:
#   0 3 * * * cd /srv/omborxona && ./scripts/backup.sh >> /var/log/ombor-backup.log 2>&1
#
# Nima uchun `pg_dump -Fc`: siqilgan ikkilik format. Oddiy SQL matndan
# ~5 barobar kichik va `pg_restore` bilan tanlab tiklash mumkin —
# masalan faqat bitta jadvalni.

set -euo pipefail

BACKUP_DIR="${BACKUP_DIR:-./backups}"
KEEP_DAYS="${KEEP_DAYS:-30}"
COMPOSE_SERVICE="${COMPOSE_SERVICE:-db}"

# .env.production dan baza sozlamalarini olamiz
if [[ -f .env.production ]]; then
    set -a
    # shellcheck disable=SC1091
    source .env.production
    set +a
fi

: "${POSTGRES_DB:?POSTGRES_DB berilmagan}"
: "${POSTGRES_USER:?POSTGRES_USER berilmagan}"

mkdir -p "$BACKUP_DIR"

STAMP="$(date +%Y%m%d-%H%M%S)"
TARGET="$BACKUP_DIR/${POSTGRES_DB}-${STAMP}.dump"

echo "Zaxira olinmoqda: $TARGET"

docker compose exec -T "$COMPOSE_SERVICE" \
    pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc > "$TARGET"

SIZE="$(du -h "$TARGET" | cut -f1)"
echo "Tayyor: $TARGET ($SIZE)"

# Bo'sh yoki juda kichik fayl — zaxira olinmagan degani.
# Buni sezmasdan qolish eng xavfli holat: "zaxira bor" deb o'ylab
# yurish, aslida esa bo'sh fayl saqlanayotgan bo'lishi.
MIN_BYTES=1024
ACTUAL_BYTES="$(wc -c < "$TARGET")"

if (( ACTUAL_BYTES < MIN_BYTES )); then
    echo "XATO: zaxira juda kichik ($ACTUAL_BYTES bayt). Tekshiring." >&2
    exit 1
fi

# Eski nusxalarni tozalash
DELETED="$(find "$BACKUP_DIR" -name "${POSTGRES_DB}-*.dump" -mtime "+$KEEP_DAYS" -print -delete | wc -l)"

if (( DELETED > 0 )); then
    echo "$DELETED ta eski nusxa o'chirildi (${KEEP_DAYS} kundan eski)"
fi

echo "Jami nusxalar: $(find "$BACKUP_DIR" -name "${POSTGRES_DB}-*.dump" | wc -l)"
