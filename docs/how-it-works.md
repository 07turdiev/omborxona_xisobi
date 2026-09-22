# Tizim qanday ishlaydi

Bu hujjat kodni o'qishdan oldin o'qiladi. Maqsad — bir kunda butun
tizimni tushunish.

---

## 1. Nima bu

Bitta kiyim do'koni uchun kassa va ombor tizimi. Bitta do'kon, bitta
ombor, bitta valyuta (so'm), ikkita rol. Tovar omborda turadi,
sotiladigani savdo zaliga chiqariladi (3-bo'lim).

| Rol | Nima qila oladi |
|---|---|
| **Administrator** | Hamma narsa: mahsulot, kirim, hisobot, xodim, sozlama |
| **Kassir** | Sotuv, qaytarish, almashtirish, tovar va qoldiqni ko'rish |

Kassir **tannarx, foyda, ta'minotchi, xarajat va hisobotlarni ko'rmaydi**.
Bu interfeysda yashirilgan emas — serverning o'zi bu maydonlarni
javobdan olib tashlaydi (`apps/core/redaction.py`) va hisobot
manzillariga umuman kiritmaydi.

---

## 2. Asosiy qoida: qoldiq jurnaldan chiqadi

Tizimda qoldiqni **hech kim qo'lda o'zgartirmaydi**. Har qanday harakat
— sotuv, kirim, qaytarish, hisobdan chiqarish, inventarizatsiya — ombor
jurnaliga (`StockMovement`) bitta qator yozadi.

```
kirim      +8
sotuv      −2
qaytarish  +1
           ───
qoldiq      7
```

Jurnal **faqat qo'shiladi**: uni o'zgartirish yoki o'chirish bazada
trigger bilan taqiqlangan. Xato yozuv teskari yozuv bilan tuzatiladi.
Sabab oddiy: ombor hisobi — do'konning moliyaviy tarixi, uni qayta
yozib bo'lmaydi.

`Variant.stock_quantity` — shu jurnalning keshi. Uni faqat bitta
funksiya yozadi: `apps.inventory.services.record_movement`. U qatorni
`SELECT FOR UPDATE` bilan qulflaydi, shuning uchun ikki kassir oxirgi
donani bir vaqtda sota olmaydi. Ustiga bazada `CHECK (stock_quantity >= 0)`
cheklovi bor — oxirgi himoya.

Kesh jurnaldan ajralib qolsa:

```bash
python manage.py recompute_stock --fix
```

---

### Inventarizatsiya — faqat do'kon yopiq bo'lganda

Sanoq davomida sotuv bo'lsa, qoldiq o'zgaradi va **soxta farqlar**
paydo bo'ladi: sanab bo'lingan tovar sotilsa, tizimda kam ko'rinadi va
kamomad deb yoziladi. Shuning uchun inventarizatsiya do'kon yopilgandan
keyin yoki sotuv to'xtatilgan holatda o'tkaziladi.

Sanoq qatorlari **noldan** boshlanadi va har skan +1 qo'shadi. Tizimdagi
qoldiq bilan to'ldirilganda sanalmagan tovar "bor" bo'lib qolar va
o'g'irlik umuman ko'rinmasdi.

Qoralama **avtomatik saqlanadi** (oxirgi o'zgarishdan 3 soniya keyin),
shuning uchun sanoq yarmida brauzer yopilib qolsa ham sanalgan sonlar
joyida qoladi.

---

## 3. Ombor va do'kon: tovar qayerda turadi

Do'konda tovar ikki joyda turadi va qoldiq **har joyda alohida**
yuritiladi (`Location`, `VariantStock`):

| Joy | Nimasi | Kim ishlatadi |
| --- | --- | --- |
| **Ombor** | zaxira: kelgan tovarning hammasi | qabul qiluvchi |
| **Do'kon** | savdo zali, javondagi tovar | kassa |

Oqim doim bir xil:

```
kirim → Ombor → (ko'chirish) → Do'kon → sotuv
```

- **Kirim doim omborga tushadi.** Tovar shtrix-kodsiz keladi, qabulda
  yorliq chop etiladi va zaxiraga qo'yiladi.
- **Sotuv faqat zaldagi qoldiqdan** bo'ladi. Omborda 20 dona bo'lsa-yu
  zalda nol bo'lsa, kassa uni sota olmaydi.
- **Ko'chirish** (`Transfer`, `KCH-` raqami) ikki yozuv qiladi:
  ombordan `TRANSFER_OUT`, zalga `TRANSFER_IN`. Do'konning umumiy
  qoldig'i o'zgarmaydi — tovar joyini almashtirdi, xolos.

Zalga chiqarishning ikki yo'li bor:

1. **«Zalga chiqarish» ekrani** — ertalab javonni to'ldirish. Tovar
   topiladi, har variantga nechta chiqarilishi yoziladi, bitta hujjat
   yoziladi.
2. **Kassadagi bir bosish** — xaridor so'ragan narsa zalda tugagan
   bo'lsa, kassir «Ombordan olib chiqish» tugmasini bosadi: bitta
   donaga ko'chirish yoziladi va tovar savatga tushadi.

Sanoq ham joy bo'yicha o'tkaziladi: zal sanalganda ombordagi tovar
farqqa tushmaydi. Hisobdan chiqarish ham o'z joyidan bo'ladi.

---

## 4. Tannarx — o'rtacha qiymat

Har kirimda variantning o'rtacha tannarxi qayta hisoblanadi:

```
yangi_tannarx = (eski_qoldiq × eski_tannarx + kelgan × kirim_narxi)
                ─────────────────────────────────────────────────────
                            eski_qoldiq + kelgan
```

Sotuv paytida o'sha paytdagi tannarx chek qatoriga **nusxa** bo'lib
tushadi (`SaleLine.unit_cost`). Keyin tannarx o'zgarsa ham eski chekning
foydasi o'zgarmaydi — o'tgan oyning hisoboti bugun boshqacha
ko'rsatmaydi.

---

## 5. Narx

Sotuv narxi mahsulotda turadi; variant o'z narxini berishi mumkin
(masalan XL qimmatroq). Amaldagi narx — `Variant.price`.

**Kassa narxni o'zgartira olmaydi.** Server so'rovdagi narxni qabul
qilmaydi: narx doim bazadan olinadi. Agar kassa narx yuborsa, u joriy
narxga teng bo'lishi shart — aks holda so'rov rad etiladi ("narxi
o'zgargan"). Bu savatdagi eskirgan narxdan ham himoya qiladi.

**Kirimda narx taklif qilinadi.** Ustama foizi yozilsa, sotuv narxi
`tannarx × (1 + ustama/100)` bo'lib hisoblanadi va sozlamadagi qadamga
(`price_rounding_step`, standart 1 000 so'm) **yuqoriga** yaxlitlanadi:
53 332,80 so'm → 54 000 so'm. Yuqoriga — chunki pastga yaxlitlansa
ustama kiritilganidan kam bo'lib qolardi.

Taklif qoralamada shunchaki yozib qo'yiladi (`PurchaseLine.new_sale_price`)
va mahsulotga faqat **kirim tasdiqlanganda** ko'chiriladi. Shuning uchun
hali kelmagan tovarning narxi do'konda ko'rinmaydi.

Chegirma esa mumkin: qatorga yoki butun chekka. Kassir uchun chegirma
chegarasi sozlamalarda (`max_discount_percent`), administrator uchun
cheklov yo'q.

---

## 6. Hujjatlar va raqamlar

| Prefiks | Hujjat |
|---|---|
| `KIR-2026-000001` | Kirim (ta'minotchidan) |
| `SOT-2026-000001` | Sotuv (chek) |
| `QAY-2026-000001` | Qaytarish |
| `INV-2026-000001` | Inventarizatsiya |
| `KCH-2026-000001` | Ombordan zalga ko'chirish |

Raqam har yili nolga qaytadi. Ikki hujjat bir xil raqam olmasligi uchun
`pg_advisory_xact_lock` ishlatiladi — tranzaksiya tugaguncha boshqa
so'rov shu prefiks uchun raqam ola olmaydi.

Chekka bosiladigan shtrix-kod esa **faqat raqam**: `2026000001`.
Sababi amaliy — skaner kodni klaviatura orqali yozadi va `SOT-`
harflari klaviatura tiliga bog'liq bo'lib qolardi. Qidiruv ikkalasini
ham qabul qiladi.

---

## 7. Shtrix-kod

Har variantga ichki EAN-13 kod beriladi:

```
200  +  000000012  +  7
│       │             └─ nazorat raqami
│       └─ ketma-ketlik (baza sequence)
└─ ichki foydalanish prefiksi
```

`200`-`299` oralig'i xalqaro standartda do'konning ichki ishlatishi
uchun ajratilgan — bu kodlar boshqa hech qayerda uchramaydi.

Tovarning zavod kodi bo'lsa, uni ham yozish mumkin; tizim ikkalasini
ham topadi.

---

## 8. Tovar qabul qilish

Do'konga tovar **shtrix-kodsiz** keladi: qutida, o'lchamlari aralash,
yorliqsiz. Yorliqni do'konning o'zi chiqaradi. Shuning uchun kirim
ekrani skanerdan emas, **modeldan** boshlanadi.

Ish tartibi:

1. **Qutini oching va modellarga ajrating.** Bir model — bir nom: masalan
   "Bahorgi kurtka". Uning ichida o'lchamlar va ranglar bo'ladi.

2. **Tovarni kiriting** (1-qadam). Nomi, brendi, kategoriyasi va
   **qaysi o'lcham, qaysi ranglarda kelgani** belgilanadi; tannarx va
   ustama shu yerda yoziladi, sotuv narxi o'zi hisoblanadi. Bitta
   o'lcham va bitta rang belgilansa, jadval bitta katakdan iborat
   bo'ladi.

   **Rasm majburiy.** Rasmsiz tovarni ro'yxatda ham, kassa
   tanlagichida ham tanib bo'lmaydi — nom hamma ko'ylakda o'xshash.
   Telefondan suratga olish ham, fayl tanlash ham mumkin.

   Shu nomli tovar do'konda allaqachon bo'lsa, ekran ogohlantiradi va
   «Shu tovar yana keldi» tugmasini beradi — bir tovar ikki marta
   yaratilib, qoldiq ikkiga bo'linib ketmasin. Avval kelgan tovarni
   Tovarlar sahifasidan ham ochib, «Yana keldi» tugmasi bilan shu
   ekranga o'tish mumkin.

3. **Katakchani to'ldiring** (2-qadam). Ustunlar — o'lchamlar, qatorlar — ranglar.
   Har katakka nechta kelganini yozasiz, Tab bilan keyingisiga o'tasiz.
   Bo'sh katak — o'sha o'lchamdan kelmagan degani.

   Model yangi o'lchamda yoki rangda kelgan bo'lsa (ko'k M va L edi,
   qizil XL keldi), «O'lcham yoki rang» tugmasi bilan shu yerda
   qo'shiladi — mahsulot sahifasiga o'tish shart emas. Punktir katakdagi
   «+» ham xuddi shunday ishlaydi. **Faqat o'sha juftlik** yaratiladi:
   qizil M, qizil L va ko'k XL paydo bo'lmaydi (mahsulot formasidagi
   to'liq matritsa esa avvalgidek ishlaydi).

4. **Tannarx va ustama.** Tannarx modelga bitta yoziladi va hamma
   qatorga tushadi; bitta qatorniki boshqacha bo'lsa, «Alohida tannarx»
   ostida o'zgartiriladi. «Ustama %» yozilsa, sotuv narxi taklif
   qilinadi (5-bo'limga qarang) — uni qo'lda tuzatish mumkin.

   Kim keltirgani, to'langan summa va sana — «Qo'shimcha» ostida. Ular
   majburiy emas: ko'pincha tovar shunchaki keladi va kiritiladi.

5. **«Qabul qilish» tugmasini bosing.** Shunda tovar **omborga**
   tushadi, yangi narx mahsulotga yoziladi va xulosa ko'rinadi: nechta
   tovar turi, nechta dona, tannarx jami va nechta yorliq. Sotish uchun
   u keyin savdo zaliga chiqariladi (3-bo'lim).

6. **Yorliqlarni chop eting va yopishtiring** (3-qadam). Har dona uchun bitta
   yorliq chiqadi. «Qo'shimcha yorliq» — yopishtirishda yirtilganini
   almashtirish uchun; qo'shimchalar qatorlar bo'ylab navbat bilan
   taqsimlanadi. Keyin ham kerak bo'lsa, hujjatni ochib bitta modelning
   yoki bitta variantning yorlig'ini qayta chiqarish mumkin.

Ishni yarmida to'xtatish kerak bo'lsa, «Keyinroq tugataman» bosiladi:
hujjat saqlanadi va pastdagi «Tugallanmagan» chipidan qaytarib ochiladi.

**Skaner qayerda kerak.** Sotishda, sanoqda va qaytarishda — u yerda
tovarda do'kon yopishtirgan yorliq bor. Qabul qilishda skaner
ishlatilmaydi: kelgan tovarda kod bo'lmaydi, kodni do'konning o'zi
beradi.

---

## 9. Kassa oqimi

```
skanerlash → savat → chegirma → to'lov turi → «Yakunlash»
                                                   │
                            ┌──────────────────────┤
                            ▼                      ▼
                    chek chop etiladi       jurnal + qoldiq
```

Uch narsa e'tiborga olingan:

1. **Savat yo'qolmaydi.** U `sessionStorage` da saqlanadi: sahifa
   tasodifan yangilansa, skanerlangan tovarlar joyida qoladi.

2. **Ikki marta bosish ikkita chek yaratmaydi.** Har savatga bitta
   kalit (`request_key`) biriktiriladi. Server o'sha kalitli chek
   borligini ko'rsa, yangisini yaratmay, borini qaytaradi.

3. **Fokus har amaldan keyin skaner maydoniga qaytadi** — kassir
   sichqonchaga qo'l urmaydi.

4. **Zalda tugagan tovar yo'lni to'smaydi.** Xaridor so'ragan narsa
   javonda qolmagan, lekin omborda bor bo'lsa, kassa «Ombordan olib
   chiqish» tugmasini ko'rsatadi: bitta bosishda ko'chirish hujjati
   yoziladi va tovar savatga tushadi (3-bo'lim).

---

## 10. Qaytarish va almashtirish

Qaytarishda tovar **asl tannarxi bilan** omborga qaytadi va mijozga
chegirma hisobga olingan summa beriladi. Qator to'liq qaytarilsa,
yaxlitlashdan qolgan tiyinlar ham qaytadi.

Almashtirish — bu qaytarish + yangi sotuv. Buxgalteriyada ikki hujjat
qoladi, lekin kassir **bitta sonni** ko'radi: "Mijozdan oling" yoki
"Mijozga qaytaring". To'lov usulini ham bir marta tanlaydi.

Shu sababli kun oxirida hisobotdagi naqd summa kassadagi haqiqiy pulga
teng bo'ladi — sotuv, qaytarish va almashtirish qanday aralashmasin.

---

## 11. Bekor qilish va kun chegarasi

Chekni bekor qilish faqat **o'sha kuni** va faqat administrator uchun.
Ertasiga kunlik kassa yopilgan bo'ladi, shuning uchun qaytarish
ishlatiladi.

"O'sha kun" — Toshkent vaqti bo'yicha. Soat 23:30 dagi sotuv o'sha
kunning hisobotiga tushadi, ertangi kunga emas. Barcha hisobotlar
mahalliy kun chegarasidan foydalanadi (`apps/core/dates.py`).

---

## 12. Chop etish

Chek va yorliq brauzer orqali chiqadi — maxsus drayver kerak emas.

| Nima | Qog'oz |
|---|---|
| Chek | 80 mm lenta, bo'yi mazmunga qarab |
| Yorliq | Sozlamalardagi o'lcham (standart 40 × 30 mm), har dona uchun bitta |

Qog'oz o'lchami chop etishdan oldin `@page` qoidasi bilan beriladi
(`front/src/utils/print.ts`). CSS o'zgaruvchilari bu yerda ishlamaydi —
`@page` ularni ko'rmaydi.

**Chekdagi shrift millimetrda o'lchanadi.** Qonun bo'yicha chekdagi
belgilar balandligi kamida **2 mm** bo'lishi kerak. Shuning uchun
`ReceiptPrint.vue` da o'lchamlar `px` emas, `mm` da yozilgan: eng
kichik matn 3 mm shriftda, ya'ni harf balandligi ~2.1 mm. `px` da
yozilganda o'lcham printer zichligiga (203 dpi) qarab suzib ketardi.

---

## 13. Papkalar

```
back/apps/
  core/       pul maydoni, hujjat raqamlari, sanalar, ruxsatlar,
              kassirdan yashirish, Excel, do'kon sozlamalari
  accounts/   xodim va rol
  catalog/    kategoriya, o'lcham, rang, mahsulot, variant, shtrix-kod
  inventory/  ombor jurnali, inventarizatsiya, hisobdan chiqarish
  purchases/  ta'minotchi, kirim, to'lov
  sales/      chek, qaytarish, almashtirish, fiskal ulash nuqtasi
  expenses/   do'kon xarajatlari
  reports/    hisobotlar va Excel eksporti

front/src/
  api/        server bilan aloqa (axios)
  stores/     auth va kassa savati (Pinia)
  views/      ekranlar
  components/ skaner maydoni, chek, yorliq, qobiq
  utils/      pul, sana, chop etish, inventarizatsiya yordamchilari
```

Har ilovada bir xil tartib: `models.py` → `services.py` (biznes
qoidalari) → `serializers.py` → `api.py`. **Biznes mantiq faqat
`services.py` da**: API qatlami uni chaqiradi, model esa ma'lumotni
saqlaydi.

---

## 14. Fiskal modul

O'zbekistonda chek fiskal operatorga yuborilishi kerak. Hozir bu
ulanmagan: `apps/sales/fiscal.py` da bo'sh provayder turibdi va u
faqat log yozadi.

Provayder tanlangach shu fayldagi `FiscalProvider` ni amalga oshirish
kifoya — qolgan kod o'zgarmaydi. Chaqiruv `transaction.on_commit`
ichida: chek bazaga yozilmaguncha tashqariga hech narsa yuborilmaydi.
