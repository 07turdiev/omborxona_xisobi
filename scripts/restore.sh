#!/usr/bin/env bash
#
# Zaxira nusxadan tiklash.
#
# Foydalanish (loyiha papkasidan):
#   ./scripts/restore.sh backups/dokon-20260909-030000.dump
#
# Rasmlar arxivi (media-<sana>.tar.gz) shu papkada, o'sha sana bilan
# turgan bo'lsa — u ham tiklanadi. Boshqa faylni ko'rsatish mumkin:
#   ./scripts/restore.sh <dump> <media.tar.gz>
#
# DIQQAT: bu amal joriy bazani **butunlay almashtiradi**. Shuning uchun
# tasdiqlash so'raladi va avval joriy holatning nusxasi olinadi.
#
# Zaxira nusxa ishlashini yiliga bir marta sinab ko'ring. Tiklanmaydigan
# zaxira — zaxira emas, faqat xotirjamlik illyuziyasi.

set -euo pipefail

DUMP="${1:-}"
MEDIA="${2:-}"

if [[ -z "$DUMP" ]]; then
    echo "Foydalanish: $0 <zaxira-fayli.dump>" >&2
    exit 1
fi

if [[ ! -f "$DUMP" ]]; then
    echo "Fayl topilmadi: $DUMP" >&2
    exit 1
fi

# Rasmlar arxivi ko'rsatilmagan bo'lsa, dump bilan bir vaqtda
# olingani qidiriladi: `dokon-20260909-030000.dump` yonidagi
# `media-20260909-030000.tar.gz`
if [[ -z "$MEDIA" ]]; then
    STAMP="${DUMP%.dump}"
    STAMP="${STAMP##*/}"
    STAMP="${STAMP#*-}"

    CANDIDATE="$(dirname "$DUMP")/media-${STAMP}.tar.gz"

    [[ -f "$CANDIDATE" ]] && MEDIA="$CANDIDATE"
fi

# shellcheck source=scripts/db-env.sh
source "$(dirname "$0")/db-env.sh"

echo "Tiklanadi : $DUMP"
echo "Rasmlar   : ${MEDIA:-yo‘q}"
echo "Baza      : $POSTGRES_DB ${POSTGRES_HOST:+(server: $POSTGRES_HOST)}"
echo
echo "JORIY BAZA BUTUNLAY ALMASHTIRILADI."
read -r -p "Davom etilsinmi? 'ha' deb yozing: " CONFIRM

if [[ "$CONFIRM" != "ha" ]]; then
    echo "Bekor qilindi."
    exit 0
fi

# Joriy holatning nusxasi — tiklash noto'g'ri fayldan bo'lsa qaytish uchun
SAFETY="./backups/before-restore-$(date +%Y%m%d-%H%M%S).dump"
mkdir -p ./backups

echo "Joriy holat saqlanmoqda: $SAFETY"
db_dump > "$SAFETY"

# Bazaga yozadigan hamma to'xtatiladi — so'rov tiklash o'rtasida
# yarim jadvalga yozib qo'ymasin
echo "Ilova to'xtatilmoqda..."
docker compose stop backend

echo "Tiklanmoqda..."
db_restore < "$DUMP"

echo "Ilova ishga tushirilmoqda..."
docker compose start backend

if [[ -n "$MEDIA" ]]; then
    echo "Rasmlar tiklanmoqda: $MEDIA"

    # Konteyner ishga tushishini kutamiz: `exec` to'xtagan konteynerda
    # ishlamaydi
    until docker compose exec -T backend true 2>/dev/null; do sleep 1; done

    docker compose exec -T backend sh -c 'rm -rf /app/media/* && tar xzf - -C /app/media' < "$MEDIA"
fi

echo
echo "Tayyor. Tekshiring:"
echo "  docker compose exec backend python manage.py check --database default"
