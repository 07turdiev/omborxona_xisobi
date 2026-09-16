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

| Nima | Izoh |
|---|---|
| **Fiskal modul** | Eng muhimi. Ulanish nuqtasi tayyor (`apps/sales/fiscal.py`), provayder tanlanishi kerak |
| **Chek printerida sinash** | Chop etish 80 mm qog'ozga sozlangan va PDF bilan tekshirilgan, lekin haqiqiy termal printerda sinalmagan |
| **Skaner bilan sinash** | Kod klaviatura skaneriga mo'ljallangan; qurilma kelgach tekshirish kerak |
| **Mahsulot rasmi** | Model tayyor (`Product.photo`), interfeysda yuklash yo'q |
| **Excel'dan mahsulot import qilish** | Do'konda yuzlab pozitsiya bo'lsa qo'l bilan kiritish uzoq |

---

## Keyin kerak bo'lishi mumkin

- **Mijozlar bazasi va sodiqlik** — hozir chek anonim
- **Bir nechta kassa nuqtasi** — bitta kompyuterga mo'ljallangan
- **Sentry** — xatolarni loglardan qidirish o'rniga bildirishnoma
