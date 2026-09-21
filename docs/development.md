# Lokal ishga tushirish va sinash

Serverga chiqarish uchun [deployment.md](./deployment.md) ga qarang.
Tizim qanday ishlashi — [how-it-works.md](./how-it-works.md).

---

## 1. Baza

PostgreSQL **15 yoki undan yangi** bo'lishi shart: variantlar jadvalidagi
unikal cheklov `NULLS NOT DISTINCT` dan foydalanadi, u 15-versiyada
paydo bo'lgan. Eski versiyada migratsiya yiqiladi.

```bash
psql -U postgres -c "CREATE ROLE dokon_app LOGIN PASSWORD 'o'zingiz-tanlagan-parol' CREATEDB"
psql -U postgres -c "CREATE DATABASE dokon OWNER dokon_app ENCODING 'UTF8'"
```

`CREATEDB` huquqi testlar uchun kerak: Django test bazasini o'zi
yaratadi va o'chiradi.

Ulanish manzili `back/.env` da:

```
DATABASE_URL=postgres://dokon_app:PAROL@127.0.0.1:5432/dokon
```

`back/.env.example` dan nusxa oling. Bu fayl git'ga tushmaydi.

---

## 2. Ishga tushirish — eng oson yo'li

Repo ildizidagi ikkita faylni **ikki marta bosing**:

| Fayl | Nima qiladi |
|---|---|
| `backend.bat` | Migratsiyani tekshiradi va Django serverini ochadi — http://127.0.0.1:8000 |
| `frontend.bat` | Vue serverini ochadi — http://localhost:5173 |

`backend.bat` qo'llanmagan migratsiya borligini ko'rsa, serverni
ochmaydi va nima qilish kerakligini aytadi. Bu ataylab: eski sxema
ustida ishga tushsangiz, xato faqat birinchi sotuvda ko'rinadi.

---

## 3. Qo'lda

```powershell
cd back
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py runserver
```

> `Activate.ps1` "running scripts is disabled" xatosini bersa,
> yuqoridagi to'g'ridan-to'g'ri `python.exe` chaqiruvi hech qanday
> sozlama talab qilmaydi.

Frontend:

```bash
cd front
npm run dev
```

> **Eslatma:** tarmog'ingizda sertifikat MITM bor, shuning uchun
> `npm install` kabi tarmoqqa chiqadigan buyruqlarga
> `NODE_OPTIONS=--use-system-ca` prefiksi kerak. `npm run dev` va
> `npm run build` uchun kerak emas.

---

## 4. Namuna ma'lumot

```bash
.venv/Scripts/python.exe manage.py seed_demo
```

Buyruq do'kon, 4 ta mahsulot (22 variant), ta'minotchi, tasdiqlangan
kirim va ikkita sotuv yaratadi. Tugagach **login, parol va sinov uchun
shtrix-kodni o'zi chiqaradi**.

Bazada allaqachon ma'lumot bo'lsa, buyruq to'xtaydi. Hammasini
o'chirib qayta yaratish:

```bash
.venv/Scripts/python.exe manage.py seed_demo --force
```

> `seed_demo` **`DEBUG=False` bo'lganda umuman ishlamaydi**. Namuna
> xodimlarning paroli oddiy va hammaga ma'lum — ular ishlab chiqarish
> bazasiga tushmasligi kerak.

---

## 5. Skanersiz sinash

Skaner — oddiy klaviatura: kodni yozadi va Enter bosadi. Shuning uchun
**shtrix-kodni qo'lda yozib Enter bosish** aynan skaner kabi ishlaydi.

Sinab ko'ring:

- bir kodni **ikki marta** skanerlang — yangi qator qo'shilmaydi,
  miqdor oshadi;
- kod atrofida **bo'shliq** qoldiring — baribir topiladi;
- yo'q kodni kiriting — aniq xato chiqadi;
- qoldiqdan ko'p miqdor qo'ying — sotuvga qo'ymaydi.

Qaytarish sahifasida chek raqamini (`SOT-2026-000001`) yoki chekdagi
raqamli kodni (`2026000001`) kiriting — ikkalasi ham ishlaydi.

---

## 6. Testlar

```bash
# Backend — 81 ta
cd back
.venv/Scripts/python.exe manage.py test
.venv/Scripts/python.exe manage.py test apps.sales      # bitta ilova

# Frontend — 22 ta (pul hisobi va inventarizatsiya yordamchilari)
cd front
npm run test:unit
npm run build            # type-check + qurish
```

Testlar orasida ikkitasi alohida e'tiborga loyiq:

- `ConcurrentSaleTests` va `ConcurrentReturnTests` — ikkita so'rovni
  haqiqiy oqimlarda bir vaqtda yuboradi va faqat bittasi o'tishini
  tekshiradi;
- `MigrationStateTests` — model bilan migratsiya ajralib qolmaganini
  tekshiradi (`makemigrations --check`).

---

## 7. Foydali buyruqlar

```bash
# Qoldiq keshi jurnaldan ajralib qolganini tekshirish
.venv/Scripts/python.exe manage.py recompute_stock
.venv/Scripts/python.exe manage.py recompute_stock --fix

# Model o'zgargandan keyin
.venv/Scripts/python.exe manage.py makemigrations
.venv/Scripts/python.exe manage.py migrate

# Administrator qo'shish
.venv/Scripts/python.exe manage.py createsuperuser
```

---

## 8. Ko'rinish: ranglar, shrift va rasmlar

Butun interfeysning ko'rinishi ikki faylda:

| Fayl | Nima |
|---|---|
| `front/src/assets/app.css` | Ilova: ranglar (`:root`), yon panel, topbar, tugma, karta, jadval |
| `front/src/assets/login.css` | Faqat kirish sahifasi — to'q fon va shisha forma |

Qoidalar:

- **Rang faqat ma'no uchun.** Fon qog'oz rangida (`--bg`), matn to'q
  jigarrang (`--text`), urg'u — bitta oltin (`--accent`). Yangi rang
  qo'shishdan oldin tayyor `--` o'zgaruvchilarni qarang.
- **Kontrast.** Matn ranglari o'z foni ustida WCAG AA (4.5:1) dan
  o'tadi. Oltin gradientli tugmaning yozuvi shuning uchun oq emas, to'q
  jigarrang (`--gradient-text`): oq yozuv 2.7:1 bo'lib qolardi.
- **Serif faqat sarlavha uchun** (`--font-display`): sahifa sarlavhasi,
  mahsulot nomi, kirish sahifasi. Raqam, narx, jadval, forma va kassa —
  sans-serif va `font-variant-numeric: tabular-nums`, aks holda ustundagi
  raqamlar turli kenglikda bo'lib "titraydi".
- **Shrift tizimniki.** Internetdan hech qanday shrift yuklanmaydi —
  do'konda internet uzilsa ham interfeys o'zgarmaydi.
- **O'lchamlar.** Asosiy matn 15px, eng kichigi 12px; tugma va maydon
  balandligi `--control-height` (40px), jadval qatori 46px. Ekran
  do'konda turib, bir qadam narida ishlatiladi — mayda yozuv yaramaydi.
- **Kichik o'rgatuvchi yozuvlar qo'shilmaydi.** Maydon nomi va tugma
  yozuvi o'zini tushuntirsin. Izoh faqat oqibati bor joyda qoladi
  (masalan: «Sanoq boshlangach kategoriyani o'zgartirib bo'lmaydi»).
- **Rasmlar** `front/src/assets/` ichida, WebP formatida va ko'rsatiladigan
  o'lchamdan ikki barobar katta (Retina uchun): `logo.webp` (560 px),
  `boutique.webp` (1536 px, kirish foni va boshqaruv panelidagi lenta),
  `magnolia.webp` (480 px, bezak). Mahsulotning rasmi bo'lmasa neytral
  belgi ko'rsatiladi — boshqa tovarning surati kassirni chalg'itadi.
- **Chop etish uslublariga tegilmaydi** (`main.css`, `ReceiptPrint.vue`,
  `LabelPrint.vue`): chek va yorliq oq qog'ozda qora rangda chiqadi,
  o'lchamlari testlar bilan qulflangan.

---

## 9. API hujjatlari

| Manzil | Nima |
|---|---|
| http://127.0.0.1:8000/api/docs/ | Swagger UI |
| http://127.0.0.1:8000/api/schema/ | OpenAPI sxemasi |
| http://127.0.0.1:8000/admin/ | Django admin |

**Ikkala hujjat manzili `DEBUG=False` bo'lganda butunlay o'chadi** —
serverda API tuzilishi ochiq turmasligi kerak.
