"""Celery ilovasi — fon va jadvaldagi vazifalar.

Ishga tushirish (Redis kerak):

    celery -A config worker -l info      # vazifalarni bajaradi
    celery -A config beat -l info        # jadval bo'yicha yuboradi

`REDIS_URL` berilmagan bo'lsa (lokal ishlab chiqish), vazifalar
chaqirilgan joyning o'zida sinxron bajariladi — settings.py dagi
`CELERY_TASK_ALWAYS_EAGER` ga qarang. Ya'ni lokalda Redis va worker
ishga tushirmasdan ham hamma narsa ishlaydi, faqat jadval (beat) yo'q.
Jadvaldagi ishlarni qo'lda boshqaruv buyruqlari bilan chaqirish mumkin.
"""

import os

from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

app = Celery('omborxona')

# Sozlamalar Django settings'dan, `CELERY_` prefiksi bilan
app.config_from_object('django.conf:settings', namespace='CELERY')

# Har ilovadagi tasks.py avtomatik topiladi
app.autodiscover_tasks()
