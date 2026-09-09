#!/usr/bin/env bash
#
# Zaxira nusxadan tiklash.
#
# Foydalanish:
#   ./scripts/restore.sh backups/omborxona_xisobi-20260909-030000.dump
#
# DIQQAT: bu amal joriy bazani **butunlay almashtiradi**. Shuning uchun
# tasdiqlash so'raladi va avval joriy holatning nusxasi olinadi.
#
# Zaxira nusxa ishlashini yiliga bir marta sinab ko'ring. Tiklanmaydigan
# zaxira — zaxira emas, faqat xotirjamlik illyuziyasi.

set -euo pipefail

DUMP="${1:-}"
COMPOSE_SERVICE="${COMPOSE_SERVICE:-db}"

if [[ -z "$DUMP" ]]; then
    echo "Foydalanish: $0 <zaxira-fayli.dump>" >&2
    exit 1
fi

if [[ ! -f "$DUMP" ]]; then
    echo "Fayl topilmadi: $DUMP" >&2
    exit 1
fi

if [[ -f .env.production ]]; then
    set -a
    # shellcheck disable=SC1091
    source .env.production
    set +a
fi

: "${POSTGRES_DB:?POSTGRES_DB berilmagan}"
: "${POSTGRES_USER:?POSTGRES_USER berilmagan}"

echo "Tiklanadi : $DUMP"
echo "Baza      : $POSTGRES_DB"
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
docker compose exec -T "$COMPOSE_SERVICE" \
    pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc > "$SAFETY"

echo "Ilova to'xtatilmoqda..."
docker compose stop backend

echo "Tiklanmoqda..."
# `--clean --if-exists`: mavjud obyektlarni o'chirib, qaytadan yaratadi.
# `--no-owner`: egalik konteynerdagi rolga moslashtiriladi.
docker compose exec -T "$COMPOSE_SERVICE" \
    pg_restore -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
    --clean --if-exists --no-owner < "$DUMP"

echo "Ilova ishga tushirilmoqda..."
docker compose start backend

echo
echo "Tayyor. Tekshiring:"
echo "  docker compose exec backend python manage.py check --database default"
