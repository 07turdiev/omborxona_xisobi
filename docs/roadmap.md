# Holat va qolgan ish

Holat: **2026-09-16**.

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

Testlar: **backend 81 ta, frontend 22 ta** — hammasi o'tadi.

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
| **Chek printerida sinash** | Chop etish 80 mm qog'ozga sozlangan va PDF bilan tekshirilgan, lekin haqiqiy termal printerda sinalmagan |
| **Skaner bilan sinash** | Kod klaviatura skaneriga mo'ljallangan; qurilma kelgach tekshirish kerak |
| **Mahsulot rasmi** | Model tayyor (`Product.photo`), interfeysda yuklash yo'q |
| **Excel'dan mahsulot import qilish** | Do'konda yuzlab pozitsiya bo'lsa qo'l bilan kiritish uzoq |

---

## Ochiq savol: ESC/POS bilan to'g'ridan-to'g'ri chop etish

Hozir chek brauzer orqali chiqadi. Bundan ikkita kamchilik kelib
chiqadi va ikkalasini ham faqat printerga **to'g'ridan-to'g'ri** ESC/POS
buyruqlarini yuborish hal qiladi:

| Kamchilik | Sabab |
|---|---|
| Chek oxirida bo'sh lenta | Sahifa balandligi qat'iy (drayverdagi qog'oz), chek esa har xil uzunlikda |
| Har chop etishda oyna ochiladi | Brauzer chop etish dialogini o'zi ko'rsatadi |

ESC/POS da chek aynan kerakli uzunlikda chiqadi va qog'oz o'sha yerda
kesiladi — bo'sh joy ham, dialog ham qolmaydi. Buning uchun kichik
lokal xizmat kerak: dastur unga chekni yuboradi, u esa printerga
ESC/POS buyruqlarini uzatadi. Pul qutisini ochish buyrug'i ham o'sha
yerdan boriladi.

**Hozircha qilinmaydi** — avval qurilmalar haqiqiy ishda sinalsin.

---

## Ochiq savol: jimgina chop etish

Hozir har chek va yorliq uchun Chrome'ning chop etish oynasi ochiladi va
kassir **Print** ni bosadi. Kun bo'yi bu ortiqcha harakat.

Chrome'da `--kiosk-printing` bayrog'i oynani ochmasdan chop etadi, lekin
u **faqat standart printerga** yuboradi. Bizda esa ikkita printer bor
(yorliq va chek), ya'ni bitta standart printer yetmaydi.

Keyinroq baholanadigan variantlar:

| Variant | Ma'nosi |
|---|---|
| Alohida Chrome profili | Yorliq chop etish uchun ikkinchi profil/oyna, unda standart printer — yorliq printeri |
| Kichik lokal yordamchi dastur | Kompyuterda turadigan kichik xizmat: dastur unga hujjatni yuboradi, u kerakli printerga uzatadi |

**Hozircha amalga oshirilmaydi** — avval qurilmalar haqiqiy ishda
sinalsin, keyin qaysi biri arzonroq tushishi ko'rinadi.

---

## Keyin kerak bo'lishi mumkin

- **Mijozlar bazasi va sodiqlik** — hozir chek anonim
- **Bir nechta kassa nuqtasi** — bitta kompyuterga mo'ljallangan
- **Sentry** — xatolarni loglardan qidirish o'rniga bildirishnoma
