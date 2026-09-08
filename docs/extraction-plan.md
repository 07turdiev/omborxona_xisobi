# Ko'chirish rejasi — InvenTree'dan nima olinadi va qanday

**Manba:** InvenTree **1.6.0 dev**, MIT litsenziya. Yo'llar `InvenTree-master/src/backend/InvenTree/` ga nisbatan.
**Kirish hujjati:** [inventree-analysis.md](./inventree-analysis.md)

## 0. Bosqich 1 dan keyin qabul qilingan qarorlar

Hisobotning 8-bo'limidagi savollardan to'rttasiga javob olindi. Ular rejaning shaklini butunlay o'zgartirdi:

| # | Savol | Javob | Rejaga ta'siri |
|---|---|---|---|
| 1 | `pint` sonli tipi | **`Decimal`** (`non_int_type=Decimal`) | `conversion.py` **nusxa olinmaydi** — qayta yoziladi. Nusxa ro'yxati keskin qisqardi. |
| 2 | "1 qop = 50 kg" | **Alohida `product_units` jadvali** | Yangi `apps/units` ilovasi; `SupplierPart.pack_quantity` naqshi olinmaydi. |
| 3 | Kategoriya atributlari | **Jonli meros** | `copy_category_parameters()` olinmaydi; `ltree` ajdodlari bo'ylab o'qishda yig'iladi. |
| 4 | Qoldiq kesimi | **`variant × ombor × partiya` + `reserved`** | `stock_balances` to'rt o'lchovli; partiya MVP ga kiradi. |

Qolgan uchtasiga tavsiya bilan javob 6-bo'limda.

> **Rejaning bosh xulosasi:** `Decimal` tanlovi, multi-tenancy va JSONB birgalikda **haqiqiy nusxa olish hajmini juda kichik qildi** — jami ~250 qator, 8 ta parcha, 6 ta fayldan. Qolgan hamma narsa g'oya darajasida olinadi. Bu yomon natija emas, aksincha: MIT atribut yuki yengil, va kodning 100% i sizning arxitekturangizga qurilgan bo'ladi. Agar bu ro'yxat kattaroq bo'lganida, bu InvenTree'ning yechimlarini o'ylamasdan takrorlayotganimizni bildirardi.

---

## 1. MIT litsenziya talabini bajarish rejasi

MIT litsenziya bitta narsani talab qiladi: **"The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software."** Ya'ni nusxa olingan har bir parcha uchun mualliflik xabari va litsenziya matni sizning repongizda bo'lishi shart.

### 1.1. Repo ildizida `NOTICE` fayli

Bitta fayl, ikki qismdan iborat. **Bu fayl repoga commit qilinadi** (`InvenTree-master/` esa `.gitignore` da qoladi).

```
NOTICE
├── 1-qism: har bir ko'chirilgan parcha uchun jadval (manba fayl:qator → bizdagi fayl)
└── 2-qism: MIT litsenziyaning to'liq matni + "Copyright (c) 2017 - InvenTree Developers"
```

Jadval ustunlari: `Bizdagi fayl` | `Manba fayl:qator` | `Xarakteri` (aynan nusxa / o'zgartirilgan nusxa) | `Nima o'zgartirilgan`.

### 1.2. Har bir hosila faylda sarlavha izohi

Nusxa olingan kod joylashgan har bir `.py` fayl boshida:

```python
"""...

Bu modulda InvenTree loyihasidan (MIT) olingan kod bor.
Manba: InvenTree 1.6.0 dev — <fayl>:<qatorlar>
Litsenziya va to'liq atribut: repo ildizidagi NOTICE faylida.
"""
```

Funksiya darajasidagi parchalar uchun funksiya docstring'ida bitta qator: `Manba: InvenTree <fayl>:<qatorlar> (MIT, NOTICE ga qarang).`

### 1.3. Versiyani qanday qayd etamiz — 7-savolga javob

**Muammo:** `InvenTree-master/` — zip-arxiv, `.git` yo'q, shuning uchun commit hash mavjud emas. `version.py:18` faqat `1.6.0 dev` beradi, bu esa harakatlanuvchi nishon (dev branch).

**Tavsiyam — uchinchi yo'l, `git clone` qilmasdan:** arxivning o'zini kriptografik jihatdan qotirish.

1. `InvenTree-master/` ni bir marta `.tar` ga yig'ib, SHA-256 hisoblanadi.
2. `NOTICE` da qayd etiladi: versiya `1.6.0 dev`, olingan sana `2026-09-07`, arxiv SHA-256, fayllar soni `2770`.
3. Har bir `fayl:qator` havolasi shu arxivga nisbatan aniq bo'ladi.

Bu yetarli va tekshiriluvchan atribut beradi. Agar keyinchalik aniq commit kerak bo'lsa (masalan yuridik tekshiruv paytida), upstream repodan `git log --before=2026-09-07 master -1` bilan topib, `NOTICE` ga qo'shib qo'yiladi — bu retroaktiv qilinsa ham muammo emas.

**Nima uchun `git clone` qilmayapman:** promptingiz manba papkani qat'iy read-only deb belgilagan va men u yerga hech narsa yozmayman; qolaversa 2770 faylli reponing to'liq tarixini yuklab olish faqat bitta hash uchun oqlanmaydi.

> **Ochiq savol qoladi:** SHA-256 yondashuvi sizga yetarlimi, yoki `NOTICE` da haqiqiy commit hash turishini xohlaysizmi? Ikkinchisi bo'lsa, men upstream'ni alohida vaqtinchalik papkaga clone qilib, hash topib, papkani o'chiraman.

---

## 2. A ro'yxati — HAQIQATAN NUSXA OLINADI

Sakkiz parcha. Har biri uchun: manba, sabab, maqsad fayl, o'zgartirish, va qaysi arxitektura qaroringiz ta'sir qilishi.

### A1. Standart o'lchovsiz birlik ta'riflari

| | |
|---|---|
| **Manba** | `InvenTree/conversion.py:104-117` (~14 qator) |
| **Bizda** | `apps/units/registry.py` → `BASE_UNIT_DEFINITIONS` |
| **Xarakteri** | Aynan nusxa + kengaytirish |

```python
reg.define('piece = 1')
reg.define('each = 1 = ea')
reg.define('dozen = 12 = dz')
reg.define('hundred = 100')
reg.define('thousand = 1000')
```

**Nega nusxa:** bu kod emas, **ma'lumot** — `pint` ga sanoq birliklarini o'lchovsiz miqdor sifatida qanday tanishtirish kerakligi. O'zimiz yozsak ham xuddi shu qatorlar chiqadi, shuning uchun halol yo'l — nusxa deb e'lon qilish.

**O'zgartirish:** temperatura aliaslari va `R = ohm` (elektronika) olib tashlanadi. Qurilish birliklari qo'shiladi:

```python
reg.define('dona = 1 = ea')
reg.define('qop = 1')
reg.define('palet = 1')
reg.define('rulon = 1')
reg.define('m2 = meter ** 2')
reg.define('m3 = meter ** 3')
reg.define('pogonmetr = meter = pm')
```

**Ta'sir qiluvchi qaror:** #6 (`Decimal`) — registr `non_int_type=Decimal` bilan yaratiladi, ta'riflarning o'zi o'zgarmaydi.

---

### A2. `CustomUnit.fmt_string()` va `clean()` validatsiyasi

| | |
|---|---|
| **Manba** | `common/models.py:1812-1857` (~45 qator) |
| **Bizda** | `apps/units/models.py` → `CustomUnit` |
| **Xarakteri** | O'zgartirilgan nusxa |

**Nega nusxa:** `pint` ta'rif satrini (`nom = ta'rif = simvol`) yig'ish va uni **saqlashdan oldin** `registry.define()` bilan sinab ko'rish mantiqi — noaniq emas, lekin uni mustaqil yozganda oson o'tkazib yuboriladigan uchta tekshiruv bor: `name.isidentifier()`, ta'rifning o'zini alohida `Quantity()` bilan sinash, va faqat shundan keyin to'liq satrni `define()` qilish. Bu ketma-ketlik tajriba mahsuli.

**O'zgartirish:**
- `tenant_id` qo'shiladi; `unique=True` → `UniqueConstraint(['tenant_id', 'name'])` va `['tenant_id', 'symbol']`.
- `validate_unique()` ichidagi global `CustomUnit.objects.filter(symbol=...)` tenant bo'yicha cheklanadi.
- `registry.define()` chaqiruvi **shu tenantning registriga** yo'naltiriladi (B2 ga qarang).

**Ta'sir qiluvchi qarorlar:** #1 (multi-tenancy) — global unikallik tenant ichidagi unikallikka aylanadi, aks holda bir mijoz "qop" ni band qilsa, boshqasi yarata olmaydi. #6 (`Decimal`).

---

### A3. `StockItem.lock_quantity()` — qator darajasidagi qulf

| | |
|---|---|
| **Manba** | `stock/models.py:3149-3178` (~30 qator) |
| **Bizda** | `apps/stock/services.py` → `lock_balance_row()` |
| **Xarakteri** | O'zgartirilgan nusxa (struktura aynan) |

```python
quantity = (
    StockItem.objects
    .select_for_update()
    .filter(pk=self.pk)
    .values_list('quantity', flat=True)
    .first()
)
```

**Nega nusxa:** `select_for_update()` + `values_list().first()` kombinatsiyasi ataylab tanlangan — u qatorni qulflaydi, **lekin butun obyektni qayta yuklamaydi**, ya'ni xotiradagi boshqa maydonlarni bosib ketmaydi. `refresh_from_db()` bilan qilsangiz, boshqa tranzaksiyada o'zgargan maydonlar jimgina ustiga yoziladi. Bu nozik farq va uni mustaqil topish qiyin.

**O'zgartirish:** nishon `StockItem` emas, **`stock_balances` qatori** (`variant × ombor × partiya`). Qaytish qiymati `bool` emas, qulflangan balans obyekti. `tenant_id` filtrga qo'shiladi.

**Ta'sir qiluvchi qarorlar:** #3 (append-only) — qulf `stock_movements` ga emas, undan hosila bo'lgan **kesh jadvaliga** qo'yiladi. Jurnalning o'zi faqat `INSERT` qabul qilgani uchun qulflanmaydi; poyga holati faqat keshni yangilashda yuzaga keladi. #1 (RLS) — `select_for_update` RLS policy ostida ham ishlaydi, lekin `tenant_id` ni aniq berish kerak, aks holda qulf begona qatorga tushishi mumkin emas, lekin so'rov sekinlashadi.

---

### A4. `StockHistoryCode` — harakat turlari taksonomiyasi

| | |
|---|---|
| **Manba** | `stock/status_codes.py:44-140` (~95 qator, shundan ~30 tasi olinadi) |
| **Bizda** | `apps/stock/enums.py` → `MovementReason` |
| **Xarakteri** | O'zgartirilgan nusxa (ro'yxatning o'zi) |

**Nega nusxa:** bu **ma'lumot, mantiq emas** — sakkiz yillik ekspluatatsiyada to'plangan "ombor harakatining qancha turi bor" ro'yxati. Uni noldan yozsak, `MERGED_STOCK_ITEMS`, `RETURNED_FROM_CUSTOMER`, `CONVERTED_TO_VARIANT` kabi holatlar bir yildan keyin bittalab qo'shila boshlaydi, har biri migratsiya bilan.

**Ayniqsa qimmatli detal:** ular har bir ikki tomonlama amal uchun **ikki alohida kod** ajratgan — `SPLIT_FROM_PARENT` / `SPLIT_CHILD_ITEM`. Ya'ni bitta amal jurnalda ikki yozuv qoldiradi, har biri o'z tomonidan. Bu sizning append-only jurnalingizda **majburiy** naqsh: ko'chirish `TRANSFER_OUT` + `TRANSFER_IN` bo'ladi, aks holda bir harakat ikki omborning qoldig'ini o'zgartirishi kerak bo'lib qoladi va jurnal qatori "bir ombor, bir o'zgarish" invariantini buzadi.

**O'zgartirish:** ~30 koddan quyidagilar olinadi va o'zbekchalashtiriladi — `CREATED`, `STOCK_COUNT`, `STOCK_ADD`, `STOCK_REMOVE`, `RECEIVED_AGAINST_PURCHASE_ORDER`, `SHIPPED_AGAINST_SALES_ORDER`, `RETURNED_FROM_CUSTOMER`, `SENT_TO_CUSTOMER`. Tashlanadi — barcha `BUILD_*` (ishlab chiqarish yo'q), `INSTALLED_*`/`REMOVED_*_ASSEMBLY` (yig'ma tovar yo'q), `ASSIGNED_SERIAL`/`STOCK_SERIALIZED` (seriya MVP da yo'q), `DISASSEMBLED`, `CONVERTED_TO_VARIANT`.

Qo'shiladi (InvenTree'da yo'q, sizga kerak): `TRANSFER_OUT`, `TRANSFER_IN`, `TRANSIT_LOSS` (yo'lda yo'qolgan — 6-bandingiz), `STOCKTAKE_CORRECTION` (inventarizatsiya farqi), `WRITE_OFF_DAMAGED`, `WRITE_OFF_EXPIRED` (yaroqlilik muddati).

**Ta'sir qiluvchi qarorlar:** #3 (append-only) — kod `stock_movements.reason` ustuni bo'ladi, `StockItemTracking.tracking_type` emas.

---

### A5. `LabelTemplate.generate_page_style()`

| | |
|---|---|
| **Manba** | `report/models.py:736-750` (~15 qator) |
| **Bizda** | `apps/documents/models.py` → `LabelTemplate.page_style()` |
| **Xarakteri** | Aynan nusxa |

```python
@page {
    size: {width}mm {height}mm;
    margin: {margin}mm;
}
```

**Nega nusxa:** yorliq printerga o'lchamni yetkazishning yagona ishonchli yo'li — CSS `@page size`. Bu kichik, lekin "nega mening 58mm yorlig'im A4 da chiqyapti" muammosining tayyor yechimi.

**O'zgartirish:** `width`/`height` `FloatField` → `DecimalField(max_digits=6, decimal_places=1)`. Bu pul emas, lekin #6 qaroringizning izchilligi uchun.

**Ta'sir qiluvchi qarorlar:** #6 (`float` yo'q), #5 (Vue) — HTML shablon serverda render qilinadi va PDF sifatida qaytadi; Vue faqat "chop et" tugmasini beradi.

---

### A6. `validateFilterString()`

| | |
|---|---|
| **Manba** | `InvenTree/helpers.py:802-860` (~55 qator) + `report/validators.py` (~20 qator) |
| **Bizda** | `apps/documents/validators.py` |
| **Xarakteri** | Aynan nusxa |

`"category=6, status=[10,20]"` ko'rinishidagi satrni queryset filtriga aylantiradi. Qavs ichidagi vergulni e'tiborsiz qoldiruvchi regex — `re.split(r',(?![^\[]*\])', value)` — mustaqil yozganda birinchi urinishda to'g'ri chiqmaydi.

**Nega kerak:** shablonning `filters` maydoni — "bu chek shabloni faqat naqd to'lovli sotuvlarga taklif qilinsin" degan qoidani foydalanuvchiga kod yozdirmasdan berish usuli.

**O'zgartirish:** ruxsat etilgan maydonlar **oq ro'yxati** qo'shiladi. InvenTree'da foydalanuvchi ixtiyoriy `filters` satri yozib, `tenant_id` bo'yicha filtrni chetlab o'tishi mumkin bo'lgan yuza bor. Multi-tenant tizimda bu **xavfsizlik masalasi**, shuning uchun har model uchun filtrlash mumkin bo'lgan maydonlar aniq sanab o'tiladi.

**Ta'sir qiluvchi qarorlar:** #1 (multi-tenancy) — oq ro'yxat majburiy, aksi holda ma'lumot sizishi mumkin.

---

### A7. `round_decimal()` va `RoundingDecimalField`

| | |
|---|---|
| **Manba** | `InvenTree/fields.py:231-244`, `:262-270` (~25 qator) |
| **Bizda** | `apps/core/fields.py` |
| **Xarakteri** | O'zgartirilgan nusxa |

**Nega kerak:** `Decimal(18,3)` maydoniga 5 kasrli qiymat kelganda Django `InvalidOperation` beradi yoki jimgina kesadi — versiyaga bog'liq. Maydon darajasida `to_python()` da yaxlitlash bu noaniqlikni yo'q qiladi va xatoni `ValidationError` ga aylantiradi.

**O'zgartirish:** `if type(value) in [Decimal, float]` dan `float` **olib tashlanadi** — #6 qaroringiz bo'yicha `float` maydonga umuman yetib kelmasligi kerak, kelsa bu xato va u ko'rinishi kerak, jimgina yaxlitlanmasligi kerak.

**Ta'sir qiluvchi qarorlar:** #6 — aynan shu qaror uchun mavjud.

---

### A8. `Parameter.validate_uniqueness()` — normalizatsiyalangan taqqoslash

| | |
|---|---|
| **Manba** | `common/models.py:2949-2985` (~35 qator) |
| **Bizda** | `apps/catalog/validators.py` → `validate_attribute_uniqueness()` |
| **Xarakteri** | O'zgartirilgan nusxa (mantiq aynan) |

**Nega nusxa:** qoida — **birlik berilgan bo'lsa normalizatsiyalangan son bo'yicha, aks holda registrga sezgir bo'lmagan matn bo'yicha** taqqoslash. Ya'ni `"1000 mm"` va `"1 m"` dublikat, `"Oq"` va `"oq"` ham dublikat. Bu ikki qatorli shart, lekin uni o'ylab topish uchun mijoz shikoyati kerak bo'ladi.

**O'zgartirish:** `Parameter.objects.filter(data_numeric=...)` EAV so'rovi → JSONB so'rovi:

```sql
WHERE attributes -> 'artikul' ->> 'num' = %s
```

**Ta'sir qiluvchi qarorlar:** #2 (JSONB + GIN) — EAV qatorlari o'rniga JSONB kaliti bo'yicha so'rov; GIN indeks `jsonb_path_ops` bilan qurilishi kerak. #1 — unikallik tenant ichida.

---

### A ro'yxati yakuni

| Parcha | Qator | Xarakteri |
|---|---:|---|
| A1 Birlik ta'riflari | ~14 | aynan + kengaytirish |
| A2 `CustomUnit` validatsiyasi | ~45 | o'zgartirilgan |
| A3 `lock_quantity()` | ~30 | o'zgartirilgan |
| A4 `StockHistoryCode` | ~30 | o'zgartirilgan |
| A5 `generate_page_style()` | ~15 | aynan |
| A6 `validateFilterString()` | ~55 | aynan |
| A7 `round_decimal()` | ~25 | o'zgartirilgan |
| A8 `validate_uniqueness()` | ~35 | o'zgartirilgan |
| **Jami** | **~250** | 8 parcha, 6 fayldan |

---

## 3. B ro'yxati — QAYTA YOZILADI (g'oyasi olinadi, kodi emas)

### B1. Birlik registrining tenant bo'yicha keshlanishi

**Manba g'oya:** `InvenTree/conversion.py:26-140` — registr modul darajasida keshlanadi, custom birliklardan MD5 hash hisoblanadi, hash o'zgarsa qayta yuklanadi.

**Nega nusxa emas — bu eng muhim moslashtirish:** InvenTree'da registr **global o'zgaruvchi** (`_unit_registry`). Multi-tenant tizimda bu **to'g'ridan-to'g'ri ma'lumot sizishi**: A tenant `qop = 50 * kg` deb ta'riflasa, bu ta'rif jarayon xotirasida qoladi va B tenantning hisob-kitobiga tushadi. Ikki mijozning sementi turli og'irlikda bo'lishi mumkin, natijada B tenantning qoldig'i jimgina noto'g'ri hisoblanadi — bu **hech qanday xato bermaydi**, faqat noto'g'ri raqam beradi. Eng yomon turdagi bug.

**Bizda qanday bo'ladi:**
- Registr `dict[tenant_id, (registry, hash)]` LRU keshida, ~50 ta tenantga cheklangan.
- Hash `(tenant_id, custom_units) → MD5` — InvenTree'dagidek, lekin kalit tenantga bog'langan.
- Registr `non_int_type=Decimal` bilan yaratiladi.
- Kesh Redis'da emas, **process xotirasida** — `pint` registri picklable emas. Redis'da faqat hash turadi, invalidatsiya signali sifatida.

**Ta'sir qiluvchi qarorlar:** #1 (multi-tenancy) — asosiy sabab. #6 (`Decimal`).

---

### B2. `convert_physical_value()` — qiymatni birlikka keltirish

**Manba g'oya:** `conversion.py:212-320` — "urinishlar ro'yxati" naqshi: xom qiymat, keyin muqobil talqinlar, birinchi muvaffaqiyatlisi olinadi; hech biri ishlamasa `ValidationError`.

**Nega nusxa emas:** funksiyaning oxirgi uchdan biri `float` ga qurilgan (`conversion.py:307`). `Decimal` ga o'tganda bu qism butunlay boshqacha yoziladi, qolgan qismi esa 15 qatorlik `try/except` sikli — uni nusxa deb atash sun'iy bo'lardi.

**Olinadigan g'oyalar:**
1. **Birlikni oldindan registrda borligini tekshirish** (`unit in ureg`), so'ngra qiymatni konvertatsiya qilish. Aks holda `pint` tushunarsiz `UndefinedUnitError` beradi.
2. **O'lchovsiz qiymat maxsus ishlanadi:** foydalanuvchi `"12"` yozsa va shablon `mm` talab qilsa, bu `12 mm` deb qabul qilinadi, xato emas (`conversion.py:196-201`). Amalda foydalanuvchilar birlikni kamdan-kam yozadi.
3. **`ValidationError` ni maydonga bog'lash** — `raise ValidationError({'data': ...})`, umumiy xato emas, shunda Vue formasi xatoni to'g'ri maydon ostida ko'rsatadi.

**Tashlanadi:** muhandislik notatsiyasi va imperial o'lchovlar (C1, C2 ga qarang).

**Ta'sir qiluvchi qarorlar:** #6, #5 (maydonga bog'langan xatolar — API kontrakti).

---

### B3. Atribut qiymatlari: EAV → JSONB

**Manba g'oya:** `common/models.py:2810` — `Parameter` da `data` (xom matn) **va** `data_numeric` (normalizatsiyalangan son) yonma-yon saqlanadi.

**Nega nusxa emas:** `Parameter` — GenericForeignKey'li alohida jadval, ya'ni aynan siz rad etgan EAV. Model butunlay boshqa.

**Olinadigan g'oya — ikki tomonlama saqlash, JSONB ichida:**

```json
{
  "qalinlik":  {"raw": "12 mm",  "num": 0.012},
  "material":  {"raw": "Yog'och", "num": null},
  "namligi":   {"raw": "8%",     "num": 0.08}
}
```

`raw` — foydalanuvchi kiritgani, ko'rsatish uchun. `num` — bazaviy SI birlikdagi `Decimal`, filtrlash va taqqoslash uchun. Bularsiz `"10 mm"` va `"1 sm"` turli qiymat bo'lib qoladi va filtr ishlamaydi.

**JSONB'ga xos qo'shimchalar (InvenTree'da yo'q):**
- GIN indeks `jsonb_path_ops` bilan — `attributes @> '{"material": {"raw": "Yog'och"}}'` so'rovi uchun.
- Sonli diapazon filtri (`qalinlik 10..15 mm`) GIN bilan ishlamaydi. Eng ko'p filtrlanadigan 3-5 atribut uchun **generated column + B-tree indeks** kerak bo'ladi. Buni Bosqich 3 da o'lchash bilan hal qilamiz — oldindan qilish erta optimizatsiya.
- `Decimal` JSON'da saqlanmaydi. `num` **satr sifatida** yoziladi (`"0.012"`), o'qishda `Decimal(str)` bilan tiklanadi. `float` ga aylantirilsa #6 qaroringiz buziladi.

**Ta'sir qiluvchi qarorlar:** #2 (asosiy), #6 (`num` satr sifatida).

---

### B4. Kategoriya atributlarining jonli merosi

**Manba g'oya:** `part/models.py:2349` — `get_ancestors(include_self=True)` bo'ylab shablonlar yig'iladi, `order_by('-category__level')` bilan **eng chuqur kategoriya ustun** bo'ladi.

**Nega nusxa emas:** ikki farq. Birinchisi — ular MPTT ishlatadi, siz `ltree`. Ikkinchisi va muhimrog'i — ular **yaratish paytida bir marta nusxa oladi**, siz **jonli meros** tanladingiz.

**Bizda qanday bo'ladi:**

```sql
SELECT * FROM attribute_definitions
WHERE tenant_id = %s
  AND category_path @> (SELECT path FROM categories WHERE id = %s)
ORDER BY nlevel(category_path) DESC
```

`@>` — `ltree` ning "ajdodmi" operatori, `nlevel()` — chuqurlik. Ya'ni InvenTree'ning `get_ancestors()` + `order_by('-level')` mantig'i **bitta SQL so'roviga** siqiladi, ORM sikli ham, `bulk_create` ham kerak emas.

**Ustuvorlik qoidasi (InvenTree'dan olinadi):** chuqurroq kategoriya ustun. `Qurilish → Sement → Portlandsement` zanjirida `Portlandsement` darajasidagi default `Sement` darajasidagini bosadi.

**Jonli merosning narxi:** har o'qishda ajdodlar bo'yicha qo'shimcha so'rov. Yechim — kategoriya daraxti kam o'zgargani uchun tenant+kategoriya kaliti bilan Redis'da keshlash, kategoriya yoki atribut ta'rifi o'zgarganda invalidatsiya.

**InvenTree'dan olinadigan nozik detal:** unikallik sharti bor atributlar kategoriya default'idan **chetlab o'tiladi** (`part/models.py:2379`). Bir xil default qiymatni butun kategoriyaga qo'yish unikallikni darhol buzadi. Jonli merosda bu yanada muhim — default qiymat o'nlab mahsulotda bir vaqtda "paydo bo'lib qoladi".

**Ta'sir qiluvchi qarorlar:** #4 (`ltree` — asosiy), #2 (JSONB), #1.

---

### B5. Qoldiq: mutable ustun → append-only jurnal + kesh

**Manba g'oya:** `stock/models.py:3716` — `StockItemTracking.deltas` erkin JSON maydoni; harakat turi kod bilan, tafsilot JSON bilan.

**Nega nusxa emas:** InvenTree'da jurnal — audit, qoldiq — `StockItem.quantity` ustuni. Sizda teskari. Model butunlay boshqa.

**Olinadigan g'oyalar:**
1. **`deltas` JSON naqshi** → `stock_movements.meta JSONB`. Har harakat turining o'z qo'shimcha maydonlari bo'ladi (`transfer_id`, `stocktake_id`, `document_id`) va ularni ustun sifatida qo'shib borish sxemani shishiradi.
2. **`float` xatosini takrorlamaslik:** `add_tracking_entry()` da `deltas['quantity'] = float(quantity)` (`stock/models.py:2373`). Bizda `meta` ichidagi barcha sonlar **satr sifatida** (`str(Decimal)`).
3. **Ikki tomonlama yozuv** (A4 dan) — har ko'chirish ikki qator.

**Yangi (InvenTree'da yo'q):** `stock_balances` keshi `(tenant_id, variant_id, warehouse_id, batch_id)` kaliti bilan, ustunlari `quantity`, `reserved_quantity`, `last_movement_id`. Kesh `stock_movements` ga `INSERT` bo'lganda **shu tranzaksiya ichida** yangilanadi (A3 qulfi ostida), fon vazifasida emas — aks holda "sotish mumkinmi" tekshiruvi eskirgan ma'lumot ustida ishlaydi.

**Ta'sir qiluvchi qarorlar:** #3 (asosiy), #6, #1.

---

### B6. Ajratilgan miqdor (`reserved_quantity`)

**Manba g'oya:** `part/filters.py:465-482` — `available = total − allocated_to_sales − allocated_to_builds`, `Greatest(..., Decimal(0))` bilan o'ralgan.

**Nega nusxa emas:** ular buni **har so'rovda annotatsiya sifatida** hisoblaydi, ya'ni har `available_stock` so'rovi ikki `Subquery` agregatsiyasini ishga tushiradi. Savdo nuqtasida bu har chek uchun takrorlanadi.

**Bizda:** `stock_balances.reserved_quantity` — materiallashgan ustun, `stock_reservations` jadvaliga yozilganda yangilanadi. `available` esa `quantity - reserved_quantity` — arzon.

**Olinadigan g'oyalar:** (a) `Greatest(..., 0)` — manfiy "mavjud" ko'rsatilmaydi; (b) ortiqcha ajratish **alohida bayroq** sifatida chiqadi (`is_overallocated`), miqdor sifatida yashirilmaydi.

**Ta'sir qiluvchi qarorlar:** #3, #6.

---

### B7. Ikki bosqichli ko'chirish

**Manba g'oya:** `TransferOrder` **emas** (u ikki bosqichli emas — hisobotning 6-bo'limi). Naqsh `order/models.py:2354`, `:2415` dan olinadi — `PurchaseOrderLineItem` ning `quantity` / `received` ikki ustuni va `remaining()`.

**Bizda:** `transfer_lines` da `qty_sent` va `qty_received`. Jo'natishda `TRANSFER_OUT` yoziladi, qabulda `TRANSFER_IN`. Farq bo'lsa uchinchi yozuv — `TRANSIT_LOSS`, o'z sababi bilan. Oraliqda tovar `transit` turidagi omborda turadi (2-bandingiz), ya'ni qoldiq **yo'qolmaydi**, faqat sotuvga chiqmaydigan omborga o'tadi.

**Olinadigan qo'shimcha:** `Q(received__lt=F('quantity'))` filtri (`order/models.py:2261`) — "hali to'liq kelmagan qatorlar" bitta so'rovda. Bizda "yo'lda qolgan ko'chirishlar" paneli shu bo'ladi.

**Ta'sir qiluvchi qarorlar:** #3 (uch harakat), #6.

---

### B8. Shtrix-kod: ustun → alohida jadval

**Manba g'oya:** `InvenTree/models.py:1495` — xom qiymat (`barcode_data`) va indekslangan qidiruv kaliti (`barcode_hash`) yonma-yon.

**Nega nusxa emas:** ularda bu **modeldagi ikki ustun**, ya'ni bir obyektga bitta kod. Sizga bir nechta kerak.

**Bizda:** `barcodes (id, tenant_id, variant_id, code, code_normalized, code_type, created_at)`, `UNIQUE (tenant_id, code_normalized)`.

**Olinadigan g'oyalar:** (a) xom va normalizatsiyalangan qiymatni birga saqlash — qidiruv normalizatsiyalangani bo'yicha, ko'rsatish xomi bo'yicha; (b) kod turini alohida ustunda saqlash (EAN-13, Code128, ichki); (c) `BarcodeScanResult` (`common/models.py:3414`) — skanerlash urinishlari jurnali, "skaner ishlamayapti" shikoyatlarini tekshirish uchun.

**Normalizatsiya bizda:** bo'shliqlarni olib tashlash, katta harfga keltirish, EAN-13 uchun yetakchi nolni qotirish. InvenTree'da bu yo'q — ular `barcode_hash` ni xom qiymatdan hisoblaydi, ya'ni `" 12345 "` va `"12345"` turli kod bo'lib qoladi.

**Ta'sir qiluvchi qarorlar:** #1 (unikallik tenant ichida).

---

### B9. O'ram konversiyasi — `product_units`

**Manba g'oya:** `company/models.py:604` — `SupplierPart.pack_quantity` (matn) + `pack_quantity_native` (bazaviy birlikka keltirilgan son). Narx hisobida narx `pack_quantity_native` ga bo'linadi (`part/models.py:2985`).

**Nega nusxa emas:** ularda o'ram **yetkazib beruvchi bilan bog'langan** (`SupplierPart`), ya'ni "shu yetkazib beruvchi shu tovarni shunday o'ramda sotadi". Sizning tanlovingiz bo'yicha o'ram **mahsulotning o'z xususiyati** va bir nechta bo'la oladi.

**Bizda:** `product_units (tenant_id, variant_id, unit, factor_to_base, is_default_sale, is_default_purchase)`. Sement uchun: `qop → 50 kg`, `palet → 1500 kg`, `tonna → 1000 kg`. Kirim paletda, sotuv qopda, qoldiq kilogrammda.

**Olinadigan g'oya:** **bazaviy birlikka keltirilgan koeffitsientni saqlab qo'yish**, har safar `pint` bilan qayta hisoblamaslik. `pint` konversiyasi validatsiya paytida bir marta ishlaydi, keyin `factor_to_base` `Decimal` sifatida jadvalda yotadi.

**Ta'sir qiluvchi qarorlar:** #6 (`factor_to_base` — `Decimal(18,6)`), #1.

---

### B10. Hujjat shablonlari

**Manba g'oya:** `report/models.py:195` — `model_type` + `filters` + `revision` + `attach_to_model` + har model uchun `TypedDict` kontekst.

**Nega nusxa emas:** model maydonlari sodda, ularni yozish qiyin emas; qiymati arxitekturada. Ichida A5 va A6 nusxa sifatida o'tiradi.

**Olinadigan g'oyalar:** (a) `model_type` matn sifatida, `ContentType` FK emas — migratsiyalar orasida barqarorroq; (b) `revision` avtomatik oshadi, eski shablon bilan chiqarilgan hujjat qayta chiqarilganda o'zgarmasligi uchun; (c) **tipli kontekst** — har model `report_context()` da `TypedDict` qaytaradi, shunda shablonda qaysi o'zgaruvchi borligi kodda ko'rinadi.

**O'zgartirish:** shablon fayllari tenant bo'yicha ajratiladi (`templates/{tenant_id}/...`), aks holda bir mijoz ikkinchisining chek shablonini ko'radi.

**Ochiq masala — PDF dvigateli:** InvenTree `weasyprint` ishlatadi (`report/models.py:283`). U kuchli, lekin og'ir (~50 MB bog'liqlik) va termal chek printerlari uchun ortiqcha. Tavsiyam: chek uchun `weasyprint` emas, to'g'ridan-to'g'ri ESC/POS yoki oddiy HTML; A4 hisobotlar uchun `weasyprint`. Buni Bosqich 3 da printerlaringizni bilib hal qilamiz.

**Ta'sir qiluvchi qarorlar:** #1 (shablon izolyatsiyasi), #5 (server render, Vue faqat chaqiradi).

---

### B11. Ombor turi va strukturaviy tugunlar

**Manba g'oya:** `stock/models.py:206` `structural` bayrog'i (tugunga to'g'ridan-to'g'ri tovar tushmaydi) va `:200` `external` bayrog'i.

**Bizda:** `warehouses.type` enum (asosiy / savdo nuqtasi / tranzit — 2-bandingiz) **va** alohida `locations.is_structural` bayrog'i (7-bandingiz).

**Olinadigan g'oya:** `clean()` da ichida tovar bo'lgan tugunni strukturaviy qilishga yo'l qo'ymaslik (`stock/models.py:292`). Bizda bu `stock_balances` da nolga teng bo'lmagan qator borligini tekshirish.

**Ular bayroq qilgani sizga tur bo'ladi** — bu ongli farq: sizda tranzit ombor **qoldiq mantiqiga ta'sir qiladi** (sotuvga chiqmaydi), ularda `external` faqat belgi.

---

## 4. C ro'yxati — ko'rib chiqildi va ATAYLAB RAD ETILDI

Bu ro'yxat A va B dan kam ahamiyatli emas: u "nima uchun ko'proq olmadik" degan savolga javob beradi.

| # | Nima | Nega rad etildi |
|---|---|---|
| C1 | `from_engineering_notation()` (`conversion.py:145`) | `1K2 → 1.2K` — elektronika komponentlari notatsiyasi (rezistor, kondensator). Qurilish materiallarida umuman ishlatilmaydi. **Bu — "shunchaki takrorlayapmanmi?" tekshiruvining eng aniq misoli:** funksiya chiroyli va tayyor, lekin sizning domeningizda ma'nosiz. |
| C2 | Imperial o'lchov ishlovi (`conversion.py:252-256`) | `6'` → `feet`, `6"` → `inches`. O'zbekiston metrik. Bundan tashqari `"` belgisi o'zbek matnida qo'shtirnoq sifatida uchraydi — bu funksiya foyda emas, xato manbai bo'lardi. |
| C3 | Butun `PartPricing` (`part/models.py:2606`, ~800 qator) | min/max oralig'i — BOM kalkulyatsiyasi, tannarx emas. FIFO ham, o'rtacha vaznli ham yo'q. Sizga COGS kerak — noldan (6-bo'lim). |
| C4 | `StockLocation.owner` + `check_ownership()` | Kod faqat testlardan chaqiriladi, API'da ishlamaydi; modeli ham mos emas (bir-ko'pga, sizga ko'p-ko'pga kerak). Hisobotning 3-bo'limi. |
| C5 | `users.RuleSet` (`users/models.py:197`) | Django `Group` ustiga qurilgan, **model tipi** darajasida ishlaydi. Sizga `user × tenant × ombor` kesimi kerak. |
| C6 | `TransferOrder` (`order/models.py:3668`) | Ikki bosqichli emas: tovar `COMPLETE` gacha manba omborda turadi, kamomad `min()` bilan jimgina yutiladi. Hisobotning 6-bo'limi. |
| C7 | `InvenTreeTree` / MPTT (`InvenTree/models.py:882`) | Siz `ltree` tanladingiz (4-qaror). MPTT yozuvlari qimmat (har qo'shishda `lft`/`rght` qayta hisoblanadi) va daraxt buzilganda `rebuild()` kerak bo'ladi. |
| C8 | `delete_on_deplete` (`stock/models.py:1324`) | Append-only jurnalda "nol qoldiqli yozuv" tushunchasi yo'q. Bu ularning mutable `quantity` ustunining oqibati. |
| C9 | `serial` / `serial_int` / `_lock_serial_numbers()` | Qurilish materiallarida seriya raqami kerak emas. **Lekin `serial_int` naqshi eslab qolinadi** — hujjat raqamlari (`SF-2026-00042`) uchun aynan shu kerak bo'ladi, va `_lock_serial_numbers()` dagi poyga muammosi kassa chek raqamida takrorlanadi. |
| C10 | `Parameter.clean()` ichidagi plugin chaqiruvlari (`common/models.py:2907-2915`) | Plugin tizimi tashlanadi, lekin validatsiya kodi unga bog'langan. A8 ni ko'chirganda bu bloklar **olib tashlanishi** kerak — aks holda import xatosi chiqadi. |
| C11 | `django-money` + `djmoney.contrib.exchange` | `Rate` jadvali faqat **joriy** kursni saqlaydi, har yangilanishda ustiga yoziladi. Sizga kurs tarixi kerak (6-qaror) — o'z `exchange_rates (currency, rate, valid_from)` jadvalingiz. |
| C12 | `InvenTreeSetting` global sozlamalar (`common/models.py:1239`) | Single-tenant faraziga qurilgan — bitta qator, butun tizim uchun. Sizda har sozlama `tenant_id` ga bog'lanishi kerak. |

---

## 5. Bosqich 3 uchun ilova strukturasi (dastlabki)

```
back/apps/
├── core/          # round_decimal (A7), tenant-aware baza modellari, RLS yordamchilari
├── tenants/       # Tenant, Membership (user × tenant × rol)
├── users/         # ⚠️ mavjud — qayta ko'rib chiqiladi (pastga qarang)
├── units/         # UnitRegistry (B1), CustomUnit (A2), ProductUnit (B9)
├── catalog/       # Category (ltree), Product, Variant, AttributeDefinition (B3, B4, A8)
├── warehouse/     # ⚠️ mavjud, bo'sh — Warehouse, Location, WarehouseAccess
├── stock/         # StockMovement (append-only), StockBalance, Batch, Reservation (A3, A4, B5, B6, B7)
├── barcodes/      # Barcode, BarcodeScanResult (B8)
├── pricing/       # Currency, ExchangeRate, CostLayer (FIFO) — InvenTree'dan hech narsa
└── documents/     # DocumentTemplate, LabelTemplate (A5, A6, B10)
```

### ⚠️ Bosqich 0 skaffoldidagi qarama-qarshilik

Loyihani boshlashda yaratilgan [back/apps/users/models.py](../back/apps/users/models.py) da `User.role` maydoni bor (`admin` / `manager` / `storekeeper`). **Bu single-tenant fikrlash** va sizning 1-qaroringizga zid: bir foydalanuvchi bir nechta tenantda turli rolda bo'lishi mumkin.

Bosqich 3 ning birinchi ishi — `role` ni `User` dan olib, `tenants.Membership` ga ko'chirish. Hozircha migratsiya qo'llanilmagani uchun (baza hali yaratilmagan) buni **migratsiyasiz**, modelni tahrirlash bilan qilish mumkin. Buni oldindan aytib qo'yaman, chunki keyin topilsa qimmatroq tushadi.

---

## 6. Qolgan uchta savolga tavsiya

### 6.1. Tannarx: FIFO yoki o'rtacha vaznli? — **FIFO tavsiya qilaman**

InvenTree'da ikkalasi ham yo'q, ya'ni bu qaror butunlay sizniki.

**Nega FIFO:**
- Sizning append-only jurnalingiz FIFO uchun **allaqachon tayyor** — har kirim yozuvi o'z `unit_cost` ini olib yuradi, FIFO shunchaki eng eski qatlamdan boshlab yechish demak. O'rtacha vaznli esa har kirimda butun qoldiq bo'yicha qayta hisoblashni talab qiladi.
- Partiya (batch) o'lchovini tanladingiz — FIFO qatlamlari partiya bilan tabiiy mos keladi.
- O'zbekiston buxgalteriya amaliyotida FIFO keng tarqalgan va soliq hisobotida tushuntirish oson.
- Yaroqlilik muddati bo'lgan tovarda (sement) fizik oqim ham FIFO — hisob fizik haqiqatga mos bo'ladi.

**Narxi:** `cost_layers` jadvali kerak (`variant × ombor × partiya × kirim_narxi × qoldiq_miqdor`), va sotuvda qatlamlarni ketma-ket yechish. Bu o'rtacha vaznlidan ~2 barobar ko'proq kod.

> Agar hisobchingiz o'rtacha vaznlini talab qilsa, ayting — arxitektura ikkalasini ham ko'taradi, lekin **ikkalasini bir vaqtda emas**, chunki tanlov hisobot raqamlarini o'zgartiradi.

### 6.2. `NOTICE` da SHA-256 yetarlimi yoki commit hash kerakmi?

Tavsiyam — **SHA-256 + versiya + sana** (1.3-bo'lim). Yuridik jihatdan MIT atributi uchun bu ortig'i bilan yetarli; commit hash qulaylik, talab emas.

### 6.3. Chek chiqarish: `weasyprint` yoki ESC/POS?

Printerlaringizni bilmasdan qaror qilib bo'lmaydi. Bosqich 3 da `documents` ilovasiga kelganda so'rayman. Hozircha model shakli ikkalasini ham ko'taradigan qilib loyihalanadi (`output_format` maydoni).

---

## 7. Bosqich 3 ga o'tishdan oldin

Tasdiqlashingiz kerak bo'lgan narsalar:

1. **A ro'yxati** (~250 qator, 8 parcha) — nusxa olinadigan hajm shu darajada kichik bo'lishi sizga ma'qulmi?
2. **FIFO** tanlovi (6.1).
3. **`NOTICE` da SHA-256** yondashuvi (6.2 / 1.3).
4. **`User.role` ni `Membership` ga ko'chirish** (5-bo'lim ogohlantirishi).
5. **Ilova strukturasi** (5-bo'lim) — 10 ta ilova ko'p tuyulsa, birlashtirish mumkin (masalan `barcodes` → `catalog`, `units` → `catalog`).

Tasdiqlaganingizdan keyin Bosqich 3 ni boshlayman: `NOTICE` fayli, `apps/core` va `apps/tenants` (RLS asosi), so'ngra `apps/units` (A1, A2, B1, B2) — chunki qolgan hamma narsa birlik konversiyasiga bog'liq.
