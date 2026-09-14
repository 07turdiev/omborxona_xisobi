"""
Django sozlamalari — omborxona_xisobi loyihasi.
"""

from datetime import timedelta
from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env(
    DEBUG=(bool, False),
    ALLOWED_HOSTS=(list, ["localhost", "127.0.0.1"]),
    CORS_ALLOWED_ORIGINS=(list, ["http://localhost:5173", "http://127.0.0.1:5173"]),
)
environ.Env.read_env(BASE_DIR / ".env")

SECRET_KEY = env("SECRET_KEY", default="django-insecure-CHANGE-ME-in-.env")
DEBUG = env("DEBUG")
ALLOWED_HOSTS = env("ALLOWED_HOSTS")


# --- Ilovalar -------------------------------------------------------------

DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

THIRD_PARTY_APPS = [
    "rest_framework",
    "rest_framework_simplejwt",
    "corsheaders",
    "drf_spectacular",
]

LOCAL_APPS = [
    "apps.core",
    "apps.tenants",
    "apps.users",
    "apps.units",
    "apps.catalog",
    "apps.warehouse",
    "apps.stock",
    "apps.pricing",
    "apps.partners",
    "apps.documents",
    "apps.reports",
    "apps.audit",
    "apps.debts",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    # Statik fayllarni Django o'zi beradi — nginx uchun alohida volume
    # kerak emas. SecurityMiddleware dan keyin turishi shart.
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    # Tenant kontekstini o'rnatadi va so'rovni tranzaksiyaga o'raydi.
    # AuthenticationMiddleware dan keyin turishi shart.
    "apps.core.middleware.TenantMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"


# --- Ma'lumotlar bazasi ---------------------------------------------------

DATABASES = {
    "default": env.db("DATABASE_URL", default="postgres://postgres:postgres@localhost:5432/omborxona_xisobi"),
}


# --- Kesh -----------------------------------------------------------------

REDIS_URL = env("REDIS_URL", default="")

CACHES = {
    "default": (
        {
            "BACKEND": "django.core.cache.backends.redis.RedisCache",
            "LOCATION": REDIS_URL,
        }
        if REDIS_URL
        else {
            # Redis yo'q bo'lsa jarayon xotirasi. Bir nechta process bo'lganda
            # o'lchov birligi keshi ular orasida sinxronlanmaydi — ishlab
            # chiqarishda REDIS_URL berilishi kerak.
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        }
    )
}


# --- Fon vazifalari (Celery) ----------------------------------------------

from celery.schedules import crontab  # noqa: E402

CELERY_BROKER_URL = REDIS_URL or "memory://"
CELERY_RESULT_BACKEND = None  # natija kerak emas: vazifalar bazaga yozadi
CELERY_TIMEZONE = "Asia/Tashkent"
CELERY_TASK_SERIALIZER = "json"
CELERY_ACCEPT_CONTENT = ["json"]

# Redis yo'q bo'lsa vazifa chaqirilgan joyda sinxron bajariladi. Bu lokal
# ishlab chiqish uchun: worker ishga tushirmasdan ham hamma narsa ishlaydi.
# Ishlab chiqarishda REDIS_URL berilgani uchun bu avtomatik o'chadi.
CELERY_TASK_ALWAYS_EAGER = not REDIS_URL
CELERY_TASK_EAGER_PROPAGATES = True

# Vazifa worker o'lib qolganda yo'qolmasin: tugagandan keyin tasdiqlanadi.
# Kurs sinxronlash qayta ishga tushirishga xavfsiz, shuning uchun bu mumkin.
CELERY_TASK_ACKS_LATE = True
CELERY_WORKER_PREFETCH_MULTIPLIER = 1

CELERY_BEAT_SCHEDULE = {
    # Markaziy bank kursni odatda ish kuni boshida e'lon qiladi. Kuniga
    # uch marta: birinchisi o'tib ketsa (tarmoq, bank sayti), keyingisi
    # to'ldiradi. Takroriy chaqiruv hech narsa yozmaydi.
    "sync-cbu-exchange-rates": {
        "task": "apps.pricing.tasks.sync_cbu_rates",
        "schedule": crontab(hour="8,12,17", minute=5),
    },
}


# --- Autentifikatsiya -----------------------------------------------------

AUTH_USER_MODEL = "users.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]


# --- Til va vaqt ----------------------------------------------------------

LANGUAGE_CODE = "uz"
TIME_ZONE = "Asia/Tashkent"
USE_I18N = True
USE_TZ = True


# --- Statik va media fayllar ----------------------------------------------

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {
        # Fayl nomiga hash qo'shadi va siqadi — brauzer keshi
        # eskirmasligi uchun.
        #
        # `DEBUG=True` da xavfsiz: Django `ManifestFilesMixin._url()`
        # ichida hashlashni o'tkazib yuboradi, ya'ni `collectstatic`
        # bajarilmagan bo'lsa ham ishlab chiqish rejimi buzilmaydi.
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# --- DRF ------------------------------------------------------------------

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 25,
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=env.int("JWT_ACCESS_MINUTES", default=60)),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=env.int("JWT_REFRESH_DAYS", default=7)),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": False,
    "AUTH_HEADER_TYPES": ("Bearer",),
}

SPECTACULAR_SETTINGS = {
    "TITLE": "Omborxona xisobi API",
    "DESCRIPTION": "Omborxona hisob-kitob tizimi uchun REST API",
    "VERSION": "0.1.0",
    "SERVE_INCLUDE_SCHEMA": False,
}


# --- CORS -----------------------------------------------------------------

CORS_ALLOWED_ORIGINS = env("CORS_ALLOWED_ORIGINS")
CORS_ALLOW_CREDENTIALS = True

# Tashkilotni tanlash sarlavhasi — frontend har so'rovda yuboradi
CORS_ALLOW_HEADERS = [
    "accept",
    "authorization",
    "content-type",
    "origin",
    "user-agent",
    "x-csrftoken",
    "x-requested-with",
    "x-tenant-id",
]


# --- Xavfsizlik -----------------------------------------------------------
#
# Bu sozlamalar faqat DEBUG=False bo'lganda yoqiladi. Ishlab chiqishda
# HTTPS yo'q, ya'ni ularni doim yoqib qo'yish lokal ishni buzardi.
#
# To'g'ri sozlanganini `manage.py check --deploy` tekshiradi.

if not DEBUG:
    # HTTPS ga majburiy yo'naltirish. Reverse proxy (nginx) orqasida
    # Django so'rov HTTPS ekanini o'zi bilmaydi — sarlavha orqali
    # bildiriladi.
    SECURE_SSL_REDIRECT = env.bool("SECURE_SSL_REDIRECT", default=True)
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

    # HSTS: brauzer shu domenga faqat HTTPS orqali murojaat qiladi.
    #
    # DIQQAT: bu sozlamani qaytarib olish qiyin — brauzer qiymatni
    # eslab qoladi va muddat tugagunicha HTTP ga tushmaydi. Shuning
    # uchun boshida kichik qiymat (masalan 3600) bilan sinab ko'ring,
    # sertifikat barqaror ishlaganiga ishonch hosil qilgach oshiring.
    SECURE_HSTS_SECONDS = env.int("SECURE_HSTS_SECONDS", default=3600)
    SECURE_HSTS_INCLUDE_SUBDOMAINS = env.bool(
        "SECURE_HSTS_INCLUDE_SUBDOMAINS", default=False
    )
    SECURE_HSTS_PRELOAD = env.bool("SECURE_HSTS_PRELOAD", default=False)

    # Cookie'lar faqat HTTPS orqali yuboriladi
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True

    # Cookie'ni JavaScript o'qiy olmaydi (XSS da token o'g'irlanmasin)
    SESSION_COOKIE_HTTPONLY = True

    # Boshqa saytdan yuborilgan so'rovda cookie ketmasin
    SESSION_COOKIE_SAMESITE = "Lax"
    CSRF_COOKIE_SAMESITE = "Lax"

    # Sahifani begona saytda iframe ichida ochib bo'lmaydi
    X_FRAME_OPTIONS = "DENY"

    # Brauzer Content-Type ni o'zi taxmin qilmasin
    SECURE_CONTENT_TYPE_NOSNIFF = True

    # Formalarni qaysi domendan yuborish mumkin (Django 4+ talab qiladi)
    CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=[])


# --- Loglash --------------------------------------------------------------
#
# Ishlab chiqarishda xatolar konsolga chiqadi va systemd/Docker jurnaliga
# tushadi. Alohida fayl ishlatilmadi: konteynerda fayl yozish qo'shimcha
# hajm va rotatsiya muammosini keltiradi.

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {
            "format": "{levelname} {asctime} {name} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "standard",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": env("LOG_LEVEL", default="INFO"),
    },
    "loggers": {
        "django.db.backends": {
            # SQL so'rovlarini ko'rish uchun LOG_LEVEL=DEBUG yetarli emas —
            # bu logger ataylab alohida, chunki u juda shovqinli
            "level": env("SQL_LOG_LEVEL", default="WARNING"),
            "propagate": True,
        },
    },
}
