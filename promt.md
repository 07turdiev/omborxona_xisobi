# Prompt: InvenTree'dan foydali qismlarni ajratib olish

> Buni Claude Code'ga (yoki Claude'ga) to'liq nusxalab bering.
> `[...]` bilan belgilangan joylarni o'zingizga moslang.

---

## Kontekst

Men noldan **multi-tenant SaaS ombor va savdo tizimi** qurmoqdaman.

**Stek:** Django 5 + DRF, PostgreSQL 16, Redis + Celery, Vue 3 + Pinia (alohida SPA).

**Maqsad bozor:** O'zbekiston. Chakana va ulgurji do'konlar — asosiy fokus **qurilish materiallari**, keyinchalik boshqa segmentlar.

**Muhim arxitektura qarorlari (bular allaqachon qabul qilingan, ularni qayta muhokama qilma):**

1. **Multi-tenancy:** bitta baza, bitta schema, har jadvalda `tenant_id`, PostgreSQL Row Level Security orqali izolyatsiya. `django-tenants` ishlatilmaydi.
2. **Dinamik atributlar:** kategoriyaga bog'langan atribut ta'riflari (`attribute_definitions`), qiymatlar esa variantda **JSONB** ustunida + GIN indeks. EAV (har qiymat alohida qator) ishlatilmaydi.
3. **Qoldiq:** hech qachon mutable `quantity` ustuni emas. `stock_movements` — faqat qo'shiladigan (append-only) jurnal. Qoldiq shundan hisoblanadi, tezlik uchun `stock_balances` keshi bo'ladi.
4. **Ierarxiya:** kategoriya daraxti uchun PostgreSQL `ltree`. MPTT ishlatilmaydi.
5. **Frontend:** Vue 3, alohida repo/papka. Django faqat API beradi, HTML template render qilmaydi.
6. **Pul:** `Decimal(18,2)`, miqdor `Decimal(18,3)`. `float` hech qayerda yo'q. Ko'p valyuta (UZS/USD) + kurs tarixi.

---

## Domen talablari — ombor

Bular biznes talablari, ularni ham qayta muhokama qilma:

1. **Har tenant o'zi bir nechta ombor yaratadi.** Ombor soni cheklanmagan. Ombor tenantga tegishli obyekt, tizim darajasidagi sozlama emas.
2. **Ombor turi bo'ladi:** asosiy ombor, savdo nuqtasi (do'kon zali), tranzit. Tur qoldiq mantiqiga ta'sir qiladi — masalan, tranzitdagi tovar sotuvga chiqmaydi.
3. **Qoldiq har doim `(variant × ombor)` kesimida.** Global "umumiy qoldiq" degan ustun yo'q; u faqat hisoblab chiqariladigan qiymat.
4. **Ko'rish huquqi ombor darajasida.** Foydalanuvchi dashboard'ga kirganda **faqat o'ziga ochilgan omborlarni** ko'radi. Bir odam A omborda omborchi, B omborda faqat ko'ruvchi, C omborni umuman ko'rmasligi mumkin. Bu API'ning har bir endpointida amal qilishi shart — frontendda yashirish yetarli emas.
5. **Ruxsat modeli:** `membership (user × tenant × rol)` va undan alohida `warehouse_access (user × ombor × ruxsat darajasi)`.
6. **Omborlar orasida ko'chirish ikki bosqichli:** jo'natildi → qabul qilindi. Oradagi farq (yo'qolgan, kam yetib kelgan) alohida ko'rinishi kerak. Bir bosqichli oddiy `transfer` qilma.
7. **Ombor ichida joy (lokatsiya) ixtiyoriy** — qator/javon/yacheyka. MVP uchun shart emas, lekin model buni keyin qo'shishga to'sqinlik qilmasin.

InvenTree'dagi `StockLocation` daraxtini shu talablar nuqtai nazaridan baholab, Bosqich 1 hisobotida alohida yozib chiq: ularning yechimi 4-bandni (ombor darajasidagi ruxsat) qanchalik qo'llab-quvvatlaydi va nimasi yetishmaydi.

---

## Manba

`[./reference/InvenTree/]` papkasida InvenTree loyihasining to'liq kodi bor (MIT litsenziya, Django + DRF).

**Bu papka qat'iy read-only ma'lumotnoma:**
- Undagi hech qanday faylni o'zgartirma, o'chirma yoki ko'chirma.
- Mening loyihamdagi kod undan hech qachon `import` qilmaydi.
- U `.gitignore` da — mening repomga kirmaydi.

---

## Vazifa

InvenTree'ni o'qib, undan **kod emas, dizayn qarorlarini** ajratib ol va mening arxitekturamga moslashtirilgan holda qayta yoz.

Ishni **uch bosqichda** bajar. Har bosqich oxirida **to'xta va natijani menga ko'rsat**. Mening tasdig'imsiz keyingi bosqichga o'tma.

### Bosqich 1 — Tahlil hisoboti

`docs/inventree-analysis.md` faylini yoz. Unda:

- InvenTree ilovalarining (`part`, `stock`, `order`, `company`, `build`, `common`, `plugin`, `report`, `label`) har biri nima qilishi — har biriga 2-3 jumla.
- Har ilova uchun bitta baho: **OLAMIZ / MOSLASHTIRAMIZ / TASHLAYMIZ** va bir jumlalik sabab.
- Asosiy modellar o'rtasidagi bog'lanishlar diagrammasi (Mermaid).
- Ular hal qilgan, men hali o'ylamagan **3-5 ta muammo** — masalan, qoldiqni bo'lish/birlashtirish, seriya raqami, o'rtacha narx hisobi. Bu eng qimmatli qismi, unga alohida e'tibor ber.

Kod yozma. Faqat hisobot.

### Bosqich 2 — Ko'chirish rejasi

`docs/extraction-plan.md` faylini yoz:

- Aynan qaysi fayl/funksiyalar **haqiqatan nusxa olinadi** (ro'yxat, sabab bilan).
- Qaysilari **qaytadan yoziladi** (g'oyasi olinadi, kodi emas).
- Har bir nusxa olinadigan fayl uchun: MIT litsenziya talabini bajarish rejasi (`NOTICE` faylida manba va litsenziya matni).
- Har bir moslashtirish uchun: mening 6 ta arxitektura qarorimdan qaysi biri ta'sir qiladi va nima o'zgaradi.

### Bosqich 3 — Kod

Faqat men tasdiqlagandan keyin. `apps/` ostida yangi Django ilovalarini yoz.

---

## Aniq olinishi kerak bo'lgan qismlar

Bularni InvenTree'da diqqat bilan o'rgan:

1. **O'lchov birligi va konversiya** — `pint` kutubxonasi integratsiyasi, `CustomUnit` modeli, mos kelmaydigan birliklarni rad etish validatsiyasi. Bu eng qimmatli qism. Menga qo'shimcha ravishda qurilish uchun `qop`, `palet`, `rulon`, `m2`, `m3` kabi birliklar va ular orasidagi konversiya kerak.
2. **Parametr shablonlari** — `PartParameterTemplate`, `PartCategoryParameterTemplate` mantiqi: shablon kategoriyaga bog'lanadi, standart qiymat yangi mahsulotga avtomatik tushadi, ostki kategoriyalarga meros o'tadi. **Lekin saqlashni EAV emas, JSONB qilib qayta loyihalashtir.**
3. **Qoldiq tarixi** — `StockItem`, `StockItemTracking`: har harakat qanday yozilishi, qoldiqni bo'lish/birlashtirish, omborlar orasida ko'chirish.
4. **Shtrix-kod** — bir mahsulotga bir nechta kod biriktirish va tez qidirish yondashuvi.
5. **Narx hisobi** — o'rtacha/FIFO narx, valyuta va kurs bilan ishlash.
6. **Hisobot va yorliq shablonlari** — narx yorlig'i va chek chiqarish uchun umumiy g'oya.

---

## Aniq TASHLANISHI kerak bo'lgan qismlar

Bularga umuman vaqt sarflama:

- `build` ilovasi — BOM, ishlab chiqarish buyurtmalari. Menga kerak emas.
- Butun frontend (React/Mantine, `crispy_forms`, Django template'lar). Men Vue yozaman.
- Plugin tizimi. Ortiqcha murakkablik.
- `django-mptt` — men `ltree` ishlataman.
- Elektronika/komponentga xos narsalar: `IPN`, supplier part matching, BOM importerlar.
- Single-tenant deb faraz qiluvchi har qanday mantiq — global sozlamalar, bitta kompaniya konfiguratsiyasi.
- Ularning auth/permission tizimi — men rolni `user × tenant × ombor` kesimida qilaman.

---

## Qoidalar

- **Faraz qilma, so'ra.** Biror qaror noaniq bo'lsa, kod yozishdan oldin savol ber.
- **Nusxa olingan har bir qator uchun manbani ko'rsat** — fayl yo'li va commit. MIT litsenziya atribut talab qiladi.
- Katta faylni ko'r-ko'rona o'qima — avval `rg` / `grep` bilan kerakli joyni top, keyin o'sha qismini o'qi.
- Har bosqichda o'zingdan so'ra: "bu InvenTree'ning yechimi menga mos, yoki men shunchaki uni takrorlayapmanmi?" Ikkinchisi bo'lsa, to'xta va menga ayt.
- Hisobotlarni o'zbek tilida yoz, kod va identifikatorlar ingliz tilida.

---

## Birinchi qadam

Hozir faqat **Bosqich 1** ni bajar. Boshlashdan oldin `[./reference/InvenTree/]` papkasi tuzilishini ko'rib chiq va menga ish rejangni bir xatboshida ayt.
