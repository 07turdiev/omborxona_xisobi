#!/usr/bin/env bash
#
# backup.sh va restore.sh uchun umumiy qism: baza sozlamalari va
# pg_dump / pg_restore ni to'g'ri joyda ishga tushirish.
#
# Baza ikki xil joyda bo'lishi mumkin:
#   - konteynerda (standart) — `docker compose exec db ...`
#   - serverning o'zida — `.env.production` da POSTGRES_HOST berilgan
#
# `.env.production` `source` qilinmaydi: SECRET_KEY dagi `(`, `&`, `$`
# belgilari bash uchun buyruq bo'lib, skript jimgina buzilardi. Faqat
# kerakli qatorlar o'qiladi.

ENV_FILE="${ENV_FILE:-.env.production}"
COMPOSE_SERVICE="${COMPOSE_SERVICE:-db}"

env_value() {
    [[ -f "$ENV_FILE" ]] || return 0
    grep -E "^$1=" "$ENV_FILE" | tail -n 1 | cut -d= -f2- | tr -d "\"'" || true
}

POSTGRES_DB="${POSTGRES_DB:-$(env_value POSTGRES_DB)}"
POSTGRES_USER="${POSTGRES_USER:-$(env_value POSTGRES_USER)}"
POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-$(env_value POSTGRES_PASSWORD)}"
POSTGRES_HOST="${POSTGRES_HOST:-$(env_value POSTGRES_HOST)}"

: "${POSTGRES_DB:?POSTGRES_DB berilmagan}"
: "${POSTGRES_USER:?POSTGRES_USER berilmagan}"

# Chiqish — stdout ga (siqilgan ikkilik format)
db_dump() {
    if [[ -n "$POSTGRES_HOST" ]]; then
        PGPASSWORD="$POSTGRES_PASSWORD" pg_dump \
            -h "$POSTGRES_HOST" -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc
    else
        docker compose exec -T "$COMPOSE_SERVICE" \
            pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc
    fi
}

# Kirish — stdin dan. `--clean --if-exists`: mavjud obyektlarni o'chirib,
# qaytadan yaratadi. `--no-owner`: egalik ilova roliga moslashadi.
db_restore() {
    if [[ -n "$POSTGRES_HOST" ]]; then
        PGPASSWORD="$POSTGRES_PASSWORD" pg_restore \
            -h "$POSTGRES_HOST" -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
            --clean --if-exists --no-owner
    else
        docker compose exec -T "$COMPOSE_SERVICE" \
            pg_restore -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
            --clean --if-exists --no-owner
    fi
}
