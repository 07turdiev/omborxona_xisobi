# Tizim qanday ishlaydi

Bu hujjat kodni o'qishdan oldin o'qiladi. Maqsad — bir kunda butun
tizimni tushunish.

---

## 1. Nima bu

Bitta kiyim do'koni uchun kassa va ombor tizimi. Bitta do'kon, bitta
ombor, bitta valyuta (so'm), ikkita rol.

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

## 3. Tannarx — o'rtacha qiymat

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

## 4. Narx

Sotuv narxi mahsulotda turadi; variant o'z narxini berishi mumkin
(masalan XL qimmatroq). Amaldagi narx — `Variant.price`.

**Kassa narxni o'zgartira olmaydi.** Server so'rovdagi narxni qabul
qilmaydi: narx doim bazadan olinadi. Agar kassa narx yuborsa, u joriy
narxga teng bo'lishi shart — aks holda so'rov rad etiladi ("narxi
o'zgargan"). Bu savatdagi eskirgan narxdan ham himoya qiladi.

Chegirma esa mumkin: qatorga yoki butun chekka. Kassir uchun chegirma
chegarasi sozlamalarda (`max_discount_percent`), administrator uchun
cheklov yo'q.

---

## 5. Hujjatlar va raqamlar

| Prefiks | Hujjat |
|---|---|
| `KIR-2026-000001` | Kirim (ta'minotchidan) |
| `SOT-2026-000001` | Sotuv (chek) |
| `QAY-2026-000001` | Qaytarish |
| `INV-2026-000001` | Inventarizatsiya |

Raqam har yili nolga qaytadi. Ikki hujjat bir xil raqam olmasligi uchun
`pg_advisory_xact_lock` ishlatiladi — tranzaksiya tugaguncha boshqa
so'rov shu prefiks uchun raqam ola olmaydi.

Chekka bosiladigan shtrix-kod esa **faqat raqam**: `2026000001`.
Sababi amaliy — skaner kodni klaviatura orqali yozadi va `SOT-`
harflari klaviatura tiliga bog'liq bo'lib qolardi. Qidiruv ikkalasini
ham qabul qiladi.

---

## 6. Shtrix-kod

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

## 7. Kassa oqimi

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

---

## 8. Qaytarish va almashtirish

Qaytarishda tovar **asl tannarxi bilan** omborga qaytadi va mijozga
chegirma hisobga olingan summa beriladi. Qator to'liq qaytarilsa,
yaxlitlashdan qolgan tiyinlar ham qaytadi.

Almashtirish — bu qaytarish + yangi sotuv. Buxgalteriyada ikki hujjat
qoladi, lekin kassir **bitta sonni** ko'radi: "Mijozdan oling" yoki
"Mijozga qaytaring". To'lov usulini ham bir marta tanlaydi.

Shu sababli kun oxirida hisobotdagi naqd summa kassadagi haqiqiy pulga
teng bo'ladi — sotuv, qaytarish va almashtirish qanday aralashmasin.

---

## 9. Bekor qilish va kun chegarasi

Chekni bekor qilish faqat **o'sha kuni** va faqat administrator uchun.
Ertasiga kunlik kassa yopilgan bo'ladi, shuning uchun qaytarish
ishlatiladi.

"O'sha kun" — Toshkent vaqti bo'yicha. Soat 23:30 dagi sotuv o'sha
kunning hisobotiga tushadi, ertangi kunga emas. Barcha hisobotlar
mahalliy kun chegarasidan foydalanadi (`apps/core/dates.py`).

---

## 10. Chop etish

Chek va yorliq brauzer orqali chiqadi — maxsus drayver kerak emas.

| Nima | Qog'oz |
|---|---|
| Chek | 80 mm lenta, bo'yi mazmunga qarab |
| Yorliq | Sozlamalardagi o'lcham (standart 40 × 30 mm), har dona uchun bitta |

Qog'oz o'lchami chop etishdan oldin `@page` qoidasi bilan beriladi
(`front/src/utils/print.ts`). CSS o'zgaruvchilari bu yerda ishlamaydi —
`@page` ularni ko'rmaydi.

---

## 11. Papkalar

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

## 12. Fiskal modul

O'zbekistonda chek fiskal operatorga yuborilishi kerak. Hozir bu
ulanmagan: `apps/sales/fiscal.py` da bo'sh provayder turibdi va u
faqat log yozadi.

Provayder tanlangach shu fayldagi `FiscalProvider` ni amalga oshirish
kifoya — qolgan kod o'zgarmaydi. Chaqiruv `transaction.on_commit`
ichida: chek bazaga yozilmaguncha tashqariga hech narsa yuborilmaydi.
