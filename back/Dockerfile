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
# Media papka oldindan yaratiladi: aks holda Docker volume uni root egaligida
# ochadi va backend (ildiz huquqisiz) rasm va logotipni saqlay olmaydi
RUN useradd --create-home --uid 1000 app && mkdir -p /app/media && chown -R app /app
USER app

EXPOSE 8000

# Avval migratsiya, keyin gunicorn — tartib entrypoint.sh da.
# `sh` orqali chaqiriladi: shunda Windows'da nusxa ko'chirilgan faylning
# bajarish huquqi bo'lmasa ham ishlaydi.
CMD ["sh", "/app/entrypoint.sh"]
