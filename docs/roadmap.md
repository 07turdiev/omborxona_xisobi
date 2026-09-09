# Qolgan ish rejasi

Holat: **2026-09-08**. Dizayn manbasi — `store/` (StoreFlow WMS prototipi),
arxitektura qarorlari — [extraction-plan.md](./extraction-plan.md).

---

## Tayyor bo'lgan qism

| Modul | Nima ishlaydi |
|---|---|
| **Poydevor** | Tenant + PostgreSQL RLS izolyatsiyasi, `Decimal` maydonlari, a'zolikka asoslangan ruxsatlar, `manage.py check` da RLS tekshiruvi |
| **Kirish** | JWT login, token yangilash, `/me` (tashkilot va rol bilan) |
| **O'lchov birliklari** | Tenant bo'yicha ajratilgan `pint` registri, `Decimal` konversiya |
| **Omborlar** | CRUD, tovar turi + vazifa (tranzit sotuvga chiqmaydi), ixtiyoriy kirish cheklovi |
| **Katalog** | `ltree` kategoriya daraxti, JSONB atributlar (jonli meros), variantlar, «1 qop = 50 kg», shtrix-kodlar |
| **Qoldiq** | Append-only jurnal (baza triggeri bilan), partiya va yaroqlilik muddati, band qilish, ikki bosqichli ko'chirish, inventarizatsiya |
| **Narx va tannarx** | FIFO qatlamlari, kurs tarixi, ko'chirishda tannarx tovar bilan yuradi |
| **Hujjatlar** | Ko'p qatorli kirim va sotuv, FEFO partiya tanlash, tasdiqlash/bekor qilish, avtomatik foyda |
| **Kontragentlar** | Yetkazib beruvchi va mijoz (bitta modelda, ikki bayroq) |
| **Hisobotlar** | Davr jamlanmasi, kategoriya/ombor kesimi, yo'qotishlar ajratilgan, sof foyda, qoldiq qiymati |
| **Interfeys** | Dizayn CSS si, sidebar, topbar, tungi rejim, login, boshqaruv paneli, omborlar, mahsulotlar, qoldiqlar, kirim, sotuv, hisobotlar |

| **Ko'chirish** | Ikki bosqichli hujjat, kamomad alohida yoziladi, tannarx tovar bilan yuradi |
| **Xodimlar** | Rollar, ombor darajasidagi ixtiyoriy cheklov |
| **Sozlamalar** | Tashkilot rekvizitlari, hujjat prefikslari, valyuta kurslari |

Testlar: **208 ta**, hammasi o'tadi.

**Dizayndagi 10 bo'limning hammasi ulangan.** Qolgan ish: chek va yorliq
shablonlari, tashkilot almashtirish, Celery, ishlab chiqarishga chiqarish.

---

## Qolgan ish — bajarilish tartibida

Tartib tasodifiy emas: har bir bosqich o'zidan oldingisiga tayanadi.
Masalan sotuvda foydani hisoblash uchun avval FIFO qatlamlari, ular uchun
esa kirim hujjati va qoldiq jurnali kerak.

### 1. Mahsulotlar katalogi — `apps/catalog`

Eng katta va eng muhim bo'lak. Qolgan hamma narsa shunga tayanadi.

- Kategoriya daraxti (`ltree`) — dizaynda 2 daraja qattiq yozilgan, bizda cheksiz
- `Product` va `Variant` — kiyimda bir modelning o'lcham/rang variantlari
- `attribute_definitions` + JSONB atributlar, kategoriya bo'ylab **jonli meros**
- Har atribut qiymati `{raw, num}` juftligi sifatida — `"10 mm"` va `"1 sm"` bir xil songa keltiriladi, aks holda filtrlash ishlamaydi
- `ProductUnit` — **"1 qop = 50 kg"**. Bu konversiya mahsulotga bog'liq (sement 50 kg, gips 30 kg), shuning uchun global registrda bo'lolmaydi
- `Barcode` — bir mahsulotga bir nechta kod, normalizatsiyalangan qidiruv kaliti bilan
- Interfeys: mahsulotlar ro'yxati, forma (kategoriyaga qarab atribut maydonlari o'zgaradi), shtrix-kod

### 2. Kontragentlar — `apps/partners`

Kichik va mustaqil, shuning uchun erta bajarilishi mumkin.

- Yetkazib beruvchi / mijoz (bitta model, ikki bayroq — dizayndagidek)
- INN, telefon, aloqa shaxsi, manzil, bank
- Interfeys: ro'yxat, forma, filtr

### 3. Qoldiq yadrosi — `apps/stock`

Tizimning yuragi. Dizayndan **eng ko'p farq qiladigan** joy.

- `stock_movements` — faqat qo'shiladigan jurnal. Dizaynda qoldiq mahsulotdagi o'zgaruvchan maydon (`stockByWarehouse`), bizda esa jurnal haqiqat manbai
- `stock_balances` keshi: `variant × ombor × partiya`, ustunlari `quantity` va `reserved_quantity`
- `Batch` — partiya kodi va **yaroqlilik muddati**. Sement 3-6 oy, quruq aralashmalar 6-12 oy; muddati o'tgan tovarni sotib yuborish real risk
- Poyga holatidan himoya (`SELECT FOR UPDATE`) — kod tayyor, `apps/core` da
- Interfeys: qoldiqlar jadvali, ombor/kategoriya/holat filtri, kam qolgan tovarlar

### 4. Kirim — `apps/documents` (purchase)

- **Ko'p qatorli** hujjat. Dizaynda bitta hujjat = bitta mahsulot; real yetkazmada 20-30 pozitsiya bo'ladi
- Har qator o'z kirim narxi va valyutasini olib yuradi — FIFO shundan hisoblanadi
- Qabul qilinganda jurnalga yozuv tushadi va qoldiq keshi yangilanadi
- Interfeys: hujjat formasi, ro'yxat, chop etish

### 5. Narx va tannarx — `apps/pricing`

Sotuvdan **oldin** kerak, aks holda foyda hisoblanmaydi.

- `Currency` va `ExchangeRate` — **kurs tarixi bilan**. `django-money` faqat joriy kursni saqlaydi, bizga tarix kerak
- `cost_layers` — FIFO qatlamlari
- Sotuvda qatlamlarni ketma-ket yechish → tannarx (COGS)
- InvenTree'da bu **umuman yo'q** — u faqat min/max narx oralig'ini beradi, tannarx emas. Noldan yoziladi

### 6. Sotuv — `apps/documents` (sale)

- Ko'p qatorli hujjat, chegirma bilan
- FIFO qatlamlarini yechib, aniq tannarx va foyda
- Band qilish (`reserved_quantity`) — "100 qop bor, 80 tasi buyurtmaga band"
- Interfeys: sotuv formasi, tez qidiruv (shtrix-kod bilan), chek

### 7. Omborlararo ko'chirish

Promptingizning 6-bandi. Dizaynda **umuman yo'q**.

- Ikki bosqich: jo'natildi → qabul qilindi
- Oraliqda tovar tranzit omborda turadi — qoldiqdan yo'qolmaydi, lekin sotuvga chiqmaydi
- Kamomad (`qty_sent` > `qty_received`) alohida yozuv sifatida ko'rinadi

### 8. Hisobotlar

- Aylanma, tushum, tannarx, foyda — davr bo'yicha
- Kategoriya va ombor kesimida
- Qoldiq qiymati (kirim va chakana narxda)
- Chop etish
- **Barcha hisobotlar barcha foydalanuvchilarga ochiq** — siz shunday xohlagansiz; cheklov kerak bo'lsa `WarehouseAccess` orqali qo'shiladi

### 9. Inventarizatsiya

- Fizik sanash va hisoblangan qoldiq farqi
- Farq alohida sabab bilan jurnalga tushadi (`STOCKTAKE_CORRECTION`)
- Bu **yo'qotish**, savdo emas — foyda hisobotida alohida ko'rinishi kerak

### 10. Foydalanuvchilar va sozlamalar

- Xodim qo'shish, rol berish, omborga kirish huquqi
- Tashkilot sozlamalari: nomi, INN, valyuta, hujjat prefikslari, kam qoldiq chegarasi
- Dizayndagi ikkita bo'lim

### 11. Hujjat shablonlari

- Chek va narx yorlig'i
- `model_type` + `filters` + `revision` arxitekturasi (InvenTree'dan olinadi)
- **Ochiq savol:** chek printeringiz qanday? `weasyprint` (PDF) og'ir, termal printer uchun ESC/POS yengilroq

### 12. Yakuniy ishlar

- Interfeysda tashkilot almashtirish (hozir birinchi a'zolik olinadi)
- Celery + Redis — og'ir hisobotlar va kesh yangilash fonda
- Ishlab chiqarishga chiqarish: server, domen, HTTPS, zaxira nusxa
- Demo parollarni almashtirish

---

## Taxminiy hajm

Aniq muddat bermayman — u sizning tasdiqlash tezligingizga ham bog'liq.
Nisbiy hajm esa shunday:

| Bosqich | Nisbiy hajm |
|---|---|
| 1. Katalog | ████████ katta |
| 3. Qoldiq yadrosi | ███████ katta |
| 5. Narx va FIFO | █████ o'rta |
| 6. Sotuv | █████ o'rta |
| 4. Kirim | ████ o'rta |
| 8. Hisobotlar | ████ o'rta |
| 7. Ko'chirish | ███ kichik |
| 2. Kontragentlar | ██ kichik |
| 9. Inventarizatsiya | ██ kichik |
| 10. Foydalanuvchi/sozlama | ██ kichik |
| 11. Shablonlar | ██ kichik |
| 12. Yakuniy | ███ kichik |

Bajarilgan qism butun ishning taxminan **oltidan biri**. Lekin poydevor
(tenant izolyatsiyasi, `Decimal`, ruxsatlar, dizayn qobig'i) eng qiyin va
eng ko'p qayta yozishga sabab bo'ladigan qismi edi — u tayyor.

---

## Tezroq natija kerak bo'lsa

Agar boshliqqa tezroq ko'rsatish kerak bo'lsa, tartibni o'zgartirish mumkin:

**Qisqa yo'l:** 1 (katalog, atributsiz) → 3 (qoldiq, partiyasiz) → 4 (kirim) →
6 (sotuv, o'rtacha narx bilan) → 8 (oddiy hisobot).

Bu ~2 barobar tez ishlaydigan demo beradi, lekin keyin partiya, yaroqlilik
muddati va FIFO ni qo'shish **migratsiya bilan** bo'ladi — ya'ni bir marta
qayta ishlash kerak. Qaysi biri ma'qulligini ayting.
