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
cd back && .venv/Scripts/python.exe manage.py test    # 165 ta
cd front && npm run test:unit                         # 93 ta
cd front && npm run build                             # type-check + build
cd agent && npm test                                  # 87 ta
```

### Interfeys testlari — alohida bazada

Playwright haqiqiy brauzerda ilovani tekshiradi (76 ta): navigatsiya va
tuzilma, tovarlar sahifasi, sotish, tovar qabul qilish (uch qadam: yangi
tovar, o'lcham × rang katakchasi, yorliq), ombordan zalga chiqarish,
telefon o'lchami, chop etish (sahifalar soni va o'lchami chiqqan PDF dan
o'lchanadi) va chop etish agenti.

`tests/screens.spec.ts` to'qqizta asosiy ekranni ikki o'lchamda ochadi
(1366x768 va 390x844) va ikki narsani tekshiradi: sahifa yon tomonga
surilmaydi va konsolda xato yo'q. O'zgaruvchi berilsa, o'sha yurishda
hujjat uchun rasm ham oladi:

```bash
cd front && SCREENSHOTS=after npm run test:ui tests/screens.spec.ts
```

Rasmlar `docs/screenshots/<nom>/` ichiga tushadi.

Bu testlar ilovaga haqiqiy so'rovlar yuboradi — mahsulot, kirim va sotuv
yaratadi. Shuning uchun ular **o'z bazasida** ishlaydi: `npm run test:ui`
ishlab chiqish bazangiz nomiga `_test_ui` qo'shib, o'sha bazani qaytadan
yaratadi (migratsiya va namuna ma'lumot bilan), backendni 8010-portda
ko'taradi va testlarni faqat o'shanga qarshi yurgizadi.
**Ishlab chiqish bazasiga tegilmaydi.**

```bash
# Bir marta: test brauzerini o'rnatish
cd front && npx playwright install chromium

# Hamma UI testlari — baza, backend va brauzerni skript o'zi ko'taradi
cd front && npm run test:ui

# Faqat chop etish testlari
cd front && npm run test:print

# Bitta fayl
cd front && npm run test:ui tests/products.spec.ts
```

Baza yaratish uchun baza foydalanuvchisida `CREATEDB` huquqi bo'lishi
kerak (`ALTER ROLE <foydalanuvchi> CREATEDB;`). Boshqa bazani ko'rsatish
mumkin: `UI_TEST_DATABASE_URL=… npm run test:ui`, portni almashtirish:
`UI_TEST_PORT=8011`.

To'g'ridan-to'g'ri `npx playwright test` yurgizilmaydi — u ishlab chiqish
bazasiga yozib yuborardi, shuning uchun ataylab to'xtatiladi.

Boshqa brauzerda sinash uchun: `PLAYWRIGHT_CHANNEL=msedge npm run test:ui`.
