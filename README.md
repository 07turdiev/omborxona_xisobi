# Do'kon — sotuv va ombor tizimi

Bitta kiyim do'koni uchun kassa va ombor hisobi. Kassir skaner bilan
sotadi, administrator kirim, qoldiq, foyda va xodimlarni boshqaradi.

| Qism | Texnologiya |
|---|---|
| Backend | Django 5.2, DRF, SimpleJWT, PostgreSQL 15+ |
| Frontend | Vue 3, TypeScript, Vite, Pinia, oddiy CSS |

---

## Nima kerak

| Nima | Versiya | Nega |
|---|---|---|
| Python | 3.13 | |
| Node.js | 22+ | |
| PostgreSQL | **15+** | Variantlar cheklovi `NULLS NOT DISTINCT` dan foydalanadi — u 15-versiyada paydo bo'lgan |

---

## Ishga tushirish

```bash
# Backend
cd back
cp .env.example .env                       # DATABASE_URL ni to'g'rilang
.venv/Scripts/python.exe manage.py migrate
.venv/Scripts/python.exe manage.py seed_demo   # namuna ma'lumot (ixtiyoriy)
.venv/Scripts/python.exe manage.py runserver

# Frontend (boshqa oynada)
cd front
npm install
npm run dev
```

Interfeys: http://localhost:5173 — `/api` so'rovlari backendga uzatiladi.

Windows'da repo ildizidagi `backend.bat` va `frontend.bat` ni ikki marta
bosish ham yetarli.

Batafsil: [docs/development.md](docs/development.md).

---

## Struktura

```
back/
  config/            sozlamalar, urls
  apps/
    core/            pul maydoni, hujjat raqami, sana, ruxsat,
                     kassirdan yashirish, Excel, do'kon sozlamalari
    accounts/        xodim va rol
    catalog/         kategoriya, o'lcham, rang, mahsulot, variant
    inventory/       ombor jurnali, inventarizatsiya, hisobdan chiqarish
    purchases/       ta'minotchi, kirim, to'lov
    sales/           chek, qaytarish, almashtirish, fiskal ulash nuqtasi
    expenses/        do'kon xarajatlari
    reports/         hisobotlar va Excel

front/src/
  api/               server bilan aloqa
  stores/            auth, kassa savati, chop etish agenti
  views/             ekranlar
  components/        skaner maydoni, chek, yorliq, qobiq
  utils/             pul, sana, chop etish

agent/               chop etish agenti (Node, bog'liqliksiz)
  src/               ESC/POS (chek), TSPL (yorliq), HTTP, sozlama
```

Har ilovada bir xil tartib: `models.py` → `services.py` → `serializers.py`
→ `api.py`. Biznes qoidalari **faqat `services.py` da**.

---

## Hujjatlar

| Fayl | Nima |
|---|---|
| [docs/how-it-works.md](docs/how-it-works.md) | Tizim qanday ishlaydi — kodni o'qishdan oldin shuni o'qing |
| [docs/development.md](docs/development.md) | Lokal ishga tushirish, testlar, skanersiz sinash |
| [docs/deployment.md](docs/deployment.md) | Serverga chiqarish, HTTPS, zaxira nusxa |
| [docs/roadmap.md](docs/roadmap.md) | Nima tayyor, nima ataylab qilinmagan, nima qoldi |
| [docs/hardware.md](docs/hardware.md) | Printer va skanerni ulash, sinash, tez-tez uchraydigan muammolar |
| [agent/README.md](agent/README.md) | Chop etish agenti: o'rnatish, sozlash, avtomatik ishga tushirish |

---

## Testlar

```bash
cd back && .venv/Scripts/python.exe manage.py test    # 95 ta
cd front && npm run test:unit                         # 44 ta
cd front && npm run build                             # type-check + build
cd agent && npm test                                  # 85 ta
```

### Chop etish testi

Chek va yorliq **qog'ozga to'g'ri tushishini** tekshiradi: sahifalar
soni, qog'oz o'lchami va chizg'ich uzunligi chiqqan PDF dan o'lchanadi
(203 dpi da rasterlanadi). Brauzerdagi o'lcham yolg'on xotirjamlik
beradi — sahifa sig'masa, Chromium chizmani jimgina kichraytiradi.

```bash
# Bir marta: test brauzerini o'rnatish
cd front && npx playwright install chromium

# Backend ishlab tursin (boshqa oynada)
cd back && .venv/Scripts/python.exe manage.py runserver
cd back && .venv/Scripts/python.exe manage.py seed_demo   # namuna ma'lumot

# Testni yurgizish
cd front && npm run test:print
```

Test ilovani o'zi quradi va `vite preview` bilan ko'taradi. Backend
standart holatda `http://127.0.0.1:8000` da kutiladi; boshqa portda
bo'lsa manzilni bering:

```bash
VITE_API_TARGET=http://127.0.0.1:8004 npm run test:print
```

Boshqa brauzerda sinash uchun: `PLAYWRIGHT_CHANNEL=msedge npm run test:print`.
