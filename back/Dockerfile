# Backend uchun konteyner.
#
# Ikki bosqichli emas: Python paketlari kompilyatsiya talab qilmaydi
# (psycopg[binary] tayyor g'ildirak bilan keladi), shuning uchun
# qo'shimcha bosqich hajmni kamaytirmaydi, faqat murakkablashtiradi.

FROM python:3.13-slim

# Python konteynerda bufersiz yozsin — log darhol ko'rinadi
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Paketlar alohida qatlamda: kod o'zgarganda ular qayta o'rnatilmaydi
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Statik fayllar qurilish paytida yig'iladi — konteyner ishga
# tushganda vaqt ketmasin. SECRET_KEY bu yerda ahamiyatsiz: u faqat
# sozlamalar yuklanishi uchun kerak.
RUN SECRET_KEY=build-only DEBUG=False \
    DATABASE_URL=postgres://build:build@localhost/build \
    python manage.py collectstatic --noinput

# Ildiz huquqisiz ishlaydi
RUN useradd --create-home --uid 1000 app && chown -R app /app
USER app

EXPOSE 8000

# Ishchilar soni: (2 × CPU) + 1 odatiy tavsiya. Konteyner nechta CPU
# olishini oldindan bilmaymiz, shuning uchun muhit o'zgaruvchisi bilan
# sozlanadi.
CMD ["sh", "-c", "gunicorn config.wsgi:application \
    --bind 0.0.0.0:8000 \
    --workers ${GUNICORN_WORKERS:-3} \
    --timeout ${GUNICORN_TIMEOUT:-60} \
    --access-logfile - \
    --error-logfile -"]
