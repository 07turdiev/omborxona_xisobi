#!/usr/bin/env bash
#
# Zaxira nusxadan tiklash.
#
# Foydalanish (loyiha papkasidan):
#   ./scripts/restore.sh backups/omborxona_xisobi-20260909-030000.dump
#
# DIQQAT: bu amal joriy bazani **butunlay almashtiradi**. Shuning uchun
# tasdiqlash so'raladi va avval joriy holatning nusxasi olinadi.
#
# Zaxira nusxa ishlashini yiliga bir marta sinab ko'ring. Tiklanmaydigan
# zaxira — zaxira emas, faqat xotirjamlik illyuziyasi.

set -euo pipefail

DUMP="${1:-}"

if [[ -z "$DUMP" ]]; then
    echo "Foydalanish: $0 <zaxira-fayli.dump>" >&2
    exit 1
fi

if [[ ! -f "$DUMP" ]]; then
    echo "Fayl topilmadi: $DUMP" >&2
    exit 1
fi

# shellcheck source=scripts/db-env.sh
source "$(dirname "$0")/db-env.sh"

echo "Tiklanadi : $DUMP"
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

# Bazaga yozadigan hamma to'xtatiladi — fon vazifasi ham tiklash
# o'rtasida yarim jadvalga yozib qo'ymasin
echo "Ilova to'xtatilmoqda..."
docker compose stop backend worker beat

echo "Tiklanmoqda..."
db_restore < "$DUMP"

echo "Ilova ishga tushirilmoqda..."
docker compose start backend worker beat

echo
echo "Tayyor. Tekshiring:"
echo "  docker compose exec backend python manage.py check --database default"
