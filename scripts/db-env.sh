#!/usr/bin/env bash
#
# backup.sh va restore.sh uchun umumiy qism: baza sozlamalari va
# pg_dump / pg_restore chaqiruvi.
#
# Baza serverning o'zida turadi (docker-compose.yml da `db` xizmati yo'q),
# shuning uchun skriptlar to'g'ridan-to'g'ri PostgreSQL ga ulanadi.
#
# `.env.production` `source` qilinmaydi: SECRET_KEY dagi `(`, `&`, `$`
# belgilari bash uchun buyruq bo'lib, skript jimgina buzilardi. Faqat
# kerakli qatorlar o'qiladi.

ENV_FILE="${ENV_FILE:-.env.production}"

env_value() {
    [[ -f "$ENV_FILE" ]] || return 0
    grep -E "^$1=" "$ENV_FILE" | tail -n 1 | cut -d= -f2- | tr -d "\"'" || true
}

POSTGRES_DB="${POSTGRES_DB:-$(env_value POSTGRES_DB)}"
POSTGRES_USER="${POSTGRES_USER:-$(env_value POSTGRES_USER)}"
POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-$(env_value POSTGRES_PASSWORD)}"
POSTGRES_HOST="${POSTGRES_HOST:-$(env_value POSTGRES_HOST)}"
POSTGRES_HOST="${POSTGRES_HOST:-127.0.0.1}"

: "${POSTGRES_DB:?POSTGRES_DB berilmagan}"
: "${POSTGRES_USER:?POSTGRES_USER berilmagan}"

# Chiqish — stdout ga (siqilgan ikkilik format)
db_dump() {
    PGPASSWORD="$POSTGRES_PASSWORD" pg_dump \
        -h "$POSTGRES_HOST" -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc
}

# Kirish — stdin dan. `--clean --if-exists`: mavjud obyektlarni o'chirib,
# qaytadan yaratadi. `--no-owner`: egalik ilova roliga moslashadi.
db_restore() {
    PGPASSWORD="$POSTGRES_PASSWORD" pg_restore \
        -h "$POSTGRES_HOST" -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
        --clean --if-exists --no-owner
}
