#!/bin/sh
# Konteyner ishga tushganda bajariladigan tartib.
#
# Migratsiya har safar avval qo'llanadi. Aks holda yangi versiya eski
# sxema ustida ishga tushadi va xatolik faqat birinchi sotuvda —
# mijoz kassada turganda — ko'rinadi.

set -e

echo "Migratsiyalar qo'llanmoqda..."
python manage.py migrate --noinput

echo "Backend ishga tushmoqda (port 8000)..."

# Ishchilar soni: (2 × CPU) + 1 odatiy tavsiya. Konteyner nechta CPU
# olishini oldindan bilmaymiz, shuning uchun muhit o'zgaruvchisi bilan
# sozlanadi.
exec gunicorn config.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers "${GUNICORN_WORKERS:-3}" \
    --timeout "${GUNICORN_TIMEOUT:-60}" \
    --access-logfile - \
    --error-logfile -
