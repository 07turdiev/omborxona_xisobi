# Holat va qolgan ish

Holat: **2026-09-18**.

---

## Tayyor

| Bo'lim | Nima ishlaydi |
|---|---|
| **Kirish** | JWT, ikki rol (administrator, kassir) |
| **Katalog** | Kategoriya, o'lcham, rang; mahsulot va variant matritsasi; ichki EAN-13 shtrix-kod |
| **Ombor** | Faqat qo'shiladigan jurnal (baza triggeri bilan), o'rtacha tannarx, manfiy qoldiqdan himoya |
| **Kirim** | Ta'minotchili yoki ta'minotchisiz (do'kon ochilishidagi qoldiq), tasdiqlash va bekor qilish |
| **Kassa** | Skaner bilan sotuv, chegirma, aralash to'lov, chek chop etish, takroriy yuborishdan himoya |
| **Qaytarish** | Chek bo'yicha qaytarish va almashtirish — kassir bitta summani ko'radi |
| **Inventarizatsiya** | Skaner bilan sanash, farqlarni ko'rsatish, qoldiqni to'g'rilash |
| **Hisobotlar** | Davr bo'yicha tushum, tannarx, foyda; kategoriya va kassir kesimi; Excel |
| **Xarajatlar** | Ijara, ish haqi, kommunal — sof foydada hisobga olinadi |
| **Xodimlar** | Qo'shish, rol, parolni almashtirish, bloklash |
| **Sozlamalar** | Do'kon nomi, yorliq o'lchami, kassir chegirma chegarasi |
| **MXIK kodlari** | Kategoriya bo'yicha standart kod, mahsulotda o'zgartirish mumkin; fiskal chekka har qator bilan ketadi |
| **Chop etish agenti** | Chek va yorliq to'g'ridan-to'g'ri printerga: oyna ochilmaydi, qog'oz bo'shga ketmaydi |

Testlar: **backend 95, frontend 44, agent 85, chop etish 10** — hammasi
o'tadi.

---

## Ataylab qilinmagan

Bular yo'qligi kamchilik emas — bitta do'kon uchun keraksiz
murakkablik bo'lardi.

| Nima | Nega yo'q |
|---|---|
| Ko'p do'kon / ko'p ombor | Bitta do'kon. Kerak bo'lsa qayta kiritish — katta ish |
| Partiya va yaroqlilik muddati | Kiyimda muddat yo'q |
| FIFO tannarx | O'rtacha tannarx yetarli va tushunarli |
| Valyuta va kurs | Hammasi so'mda |
| Buyurtma, band qilish | Do'konda tovar javonda turadi |
| Fon vazifalari (Celery, Redis) | Bajariladigan fon ishi yo'q |
| Tungi rejim | Bitta ko'rinish — kamroq kod, kamroq xato |

---

## Qolgan ish

### Ishga tushirishga to'sqinlik qiladigan yagona narsa: fiskal modul

Qolgan hamma narsa tayyor. Chek soliq tizimida ro'yxatdan o'tmasa,
do'kon qonuniy ishlay olmaydi — shuning uchun **birinchi navbatda shu
qaror qabul qilinishi kerak**:

| Variant | Nimani anglatadi |
|---|---|
| **Ro'yxatdan o'tgan virtual kassa provayderi (API bilan)** | Dastur chekni provayder API siga yuboradi. Ulash nuqtasi tayyor: `apps/sales/fiscal.py` dagi `FiscalProvider` ni amalga oshirish kifoya. Har qator MXIK kodi bilan ketadi |
| **Alohida onlayn-NKM apparati** | Kassir chekni alohida qurilmada ham chiqaradi. Dasturga o'zgarish kam, lekin kassir har sotuvni ikki marta kiritadi |

Birinchi variant afzal: kassir bitta ish qiladi va xato kamayadi.
Lekin provayder tanlash — texnik emas, tashkiliy qaror (shartnoma,
narx, qo'llab-quvvatlash).

### Boshqa qolgan ishlar

| Nima | Izoh |
|---|---|
| **Mahsulot rasmi** | Model tayyor (`Product.photo`), interfeysda yuklash yo'q |
| **Excel'dan mahsulot import qilish** | Do'konda yuzlab pozitsiya bo'lsa qo'l bilan kiritish uzoq |

---

## Chop etish agenti — hal qilindi

Ilgari bu yerda ikkita ochiq savol turardi: chek oxirida bo'shga
ketadigan lenta va har chop etishda ochiladigan oyna. Ikkalasini ham
`agent/` papkasidagi kichik lokal xizmat hal qildi.

| Nima | Qanday |
|---|---|
| Chek | ESC/POS, TCP 9100 orqali XP-Q80AS ga. Chek aynan kerakli uzunlikda chiqadi va o'sha yerda kesiladi |
| Yorliq | TSPL, Windows printer ulashuvi orqali XP-365B ga. EAN-13 ni printerning o'zi chizadi |
| Oyna | Ochilmaydi — kassir faqat qisqa xabar ko'radi |
| Pul qutisi | Naqd to'lovda ESC/POS impulsi bilan ochiladi |

Agent **majburiy emas**. U o'chirilgan bo'lsa ilova jimgina brauzer
orqali chop etishga qaytadi va sotuv to'xtamaydi — shuning uchun agent
yiqilsa ham do'kon ishlayveradi.

Qurilmada tekshirilgan (2026-09-18): chek matni, apostroflar, shtrix-kod
va kesish; yorliqlar ketma-ket chiqadi, orada bo'sh yorliq yo'q va
mazmun yorliq o'rtasida turadi.

Batafsil: [agent/README.md](../agent/README.md) va
[hardware.md](hardware.md).

---

## Keyin kerak bo'lishi mumkin

- **Mijozlar bazasi va sodiqlik** — hozir chek anonim
- **Bir nechta kassa nuqtasi** — bitta kompyuterga mo'ljallangan
- **Sentry** — xatolarni loglardan qidirish o'rniga bildirishnoma
