# Omborxona xisobi

Omborxona hisob-kitob tizimi. Backend — Django + DRF, frontend — Vue 3 + Vite.

## Texnologiyalar

| Qism     | Stack                                                                      |
| -------- | -------------------------------------------------------------------------- |
| Backend  | Django 5.2, Django REST Framework, SimpleJWT, drf-spectacular, PostgreSQL   |
| Frontend | Vue 3, TypeScript, Vite, Vue Router, Pinia, Tailwind CSS v4, Axios          |

## Struktura

```
omborxona_xisobi/
├── back/                 # Django loyihasi
│   ├── config/           # settings, urls, wsgi/asgi
│   ├── apps/
│   │   ├── users/        # maxsus User modeli + JWT auth API
│   │   └── warehouse/    # omborxona domeni (bo'sh, router tayyor)
│   ├── .env              # maxfiy sozlamalar (git'ga tushmaydi)
│   └── requirements.txt
└── front/                # Vue 3 SPA
    └── src/
        ├── api/          # axios client + token refresh
        ├── stores/       # Pinia (auth)
        ├── router/       # auth guard bilan
        └── views/
```

## Hujjatlar

| Fayl | Nima |
|---|---|
| [docs/development.md](docs/development.md) | Lokal ishga tushirish, testlar, tenant izolyatsiyasini sinash |
| [docs/inventree-analysis.md](docs/inventree-analysis.md) | InvenTree tahlili — qaysi dizayn qarorlari olindi va nega |
| [docs/extraction-plan.md](docs/extraction-plan.md) | Ko'chirish rejasi — nusxa olingan kod, qayta yozilgani, rad etilgani |
| [NOTICE](NOTICE) | InvenTree'dan olingan kod uchun MIT atributi |

## Ishga tushirish

### Backend

```bash
cd back
cp .env.example .env          # va DATABASE_URL'ni to'g'rilang
.venv/Scripts/activate        # Windows (Linux/Mac: source .venv/bin/activate)
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Backend: http://127.0.0.1:8000

### Frontend

```bash
cd front
npm install
npm run dev
```

Frontend: http://localhost:5173 (`/api` so'rovlari backendga proxy qilinadi)

## API

| Endpoint             | Tavsif                        |
| -------------------- | ----------------------------- |
| `POST /api/auth/register/` | Ro'yxatdan o'tish       |
| `POST /api/auth/login/`    | JWT access + refresh    |
| `POST /api/auth/refresh/`  | Access tokenni yangilash|
| `GET  /api/auth/me/`       | Joriy foydalanuvchi     |
| `GET  /api/docs/`          | Swagger UI              |
| `GET  /api/redoc/`         | ReDoc                   |
| `GET  /admin/`             | Django admin            |

## Foydali buyruqlar

```bash
# Backend
python manage.py makemigrations
python manage.py spectacular --file schema.yml

# Frontend
npm run type-check
npm run lint
npm run build
```
