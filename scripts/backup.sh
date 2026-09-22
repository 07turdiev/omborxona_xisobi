#!/usr/bin/env bash
#
# Baza zaxira nusxasi.
#
# Foydalanish (loyiha papkasidan):
#   ./scripts/backup.sh
#   BACKUP_DIR=/mnt/backup ./scripts/backup.sh
#
# Baza konteynerda ham, serverning o'zida ham ishlaydi (scripts/db-env.sh).
#
# Cron bilan har kuni soat 3 da:
#   0 3 * * * cd /srv/omborxona && ./scripts/backup.sh >> /var/log/ombor-backup.log 2>&1
#
# Nima uchun `pg_dump -Fc`: siqilgan ikkilik format. Oddiy SQL matndan
# ~5 barobar kichik va `pg_restore` bilan tanlab tiklash mumkin —
# masalan faqat bitta jadvalni.
#
# Rasmlar alohida arxivga tushadi: ular bazada emas, konteyner
# volume'ida yotadi. Har tovarga rasm majburiy, ya'ni ularsiz tiklangan
# baza bo'sh ramkalar bilan ochiladi.

set -euo pipefail

# shellcheck source=scripts/db-env.sh
source "$(dirname "$0")/db-env.sh"

BACKUP_DIR="${BACKUP_DIR:-./backups}"
KEEP_DAYS="${KEEP_DAYS:-30}"

mkdir -p "$BACKUP_DIR"

STAMP="$(date +%Y%m%d-%H%M%S)"
TARGET="$BACKUP_DIR/${POSTGRES_DB}-${STAMP}.dump"

echo "Zaxira olinmoqda: $TARGET"

db_dump > "$TARGET"

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

# --- Rasmlar -------------------------------------------------------------

MEDIA_TARGET="$BACKUP_DIR/media-${STAMP}.tar.gz"

if docker compose ps --services --status running 2>/dev/null | grep -qx backend; then
    echo
    echo "Rasmlar zaxirasi: $MEDIA_TARGET"

    docker compose exec -T backend tar czf - -C /app/media . > "$MEDIA_TARGET"

    echo "Tayyor: $MEDIA_TARGET ($(du -h "$MEDIA_TARGET" | cut -f1))"

    find "$BACKUP_DIR" -name 'media-*.tar.gz' -mtime "+$KEEP_DAYS" -delete
else
    echo "OGOHLANTIRISH: backend ishlamayapti, rasmlar zaxiralanmadi." >&2
fi
