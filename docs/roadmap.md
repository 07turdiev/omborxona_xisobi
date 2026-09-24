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
| **Chop etish agenti** | Chek va yorliq to'g'ridan-to'g'ri printerga: oyna ochilmaydi, qog'oz bo'shga ketmaydi |
| **Ombor va savdo zali** | Qoldiq ikki joyda alohida; ko'chirish hujjati; kassa faqat zaldagini sotadi |
| **Mahsulot rasmi** | Har tovarga majburiy, har rangga alohida surat; kassa savatida va ro'yxatlarda ko'rinadi |

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

**Dastur tayyor, o'rnatish tugallanmagan.** Kod yozilgan va sinalgan,
server ishlayapti — lekin do'konni shu tizimda ochishdan oldin
quyidagilar bajarilishi kerak. Tartib muhim: yuqoridagisi pastdagisiga
to'sqinlik qiladi.

| Nima | Nega kerak |
|---|---|
| **Chop etish agentini kassa kompyuteriga o'rnatish** | Usiz har chek va yorliqda brauzer oynasi ochiladi, kassir qo'lda **Print** bosadi. Yorliq ham hira chiqadi: brauzer shtrix-kodni rasm qilib chizadi. Tartib: `agent/README.md` |
| **`kassa` foydalanuvchisi** | `createsuperuser` bilan yaratilgani uchun u **administrator** — tannarx, foyda va hisobotlarni ko'radi. Roli kassirga o'zgartirilsin, paroli kuchli bo'lsin: sayt ochiq internetda |
| **Zaxirani serverdan tashqariga chiqarish** | Hozir nusxa serverning o'zida yotadi. Server ishdan chiqsa zaxira ham u bilan ketadi (`docs/deployment.md`, 7-bo'lim) |
| **Skanerni uchidan-uchiga sinash** | Rus klaviaturasi yoqilganda ham kod to'g'ri o'qilishi tekshirilsin (`docs/hardware.md`, 4-bo'lim) |
| **Qayta yuklashni sinash** | `sudo reboot` dan keyin hammasi o'zi ko'tarilishi kerak: konteynerlar, baza, agent |
| **Boshlang'ich ma'lumot** | Kategoriya, o'lcham, rang, xodimlar; keyin birinchi kirim |

### Fiskal modul

Do'kon soliq tizimi bilan integratsiya qilmaydi — bu buyurtmachining
qarori. Ulash nuqtasi kodda qoldirilgan (`apps/sales/fiscal.py` dagi
`FiscalProvider`): kerak bo'lsa provayder ulanadi va soliq tasnifi
kodi (MXIK) qaytariladi.

### Keyinroq foydali bo'lishi mumkin

| Nima | Izoh |
|---|---|
| **Excel'dan mahsulot import qilish** | Do'konda yuzlab pozitsiya bo'lsa qo'l bilan kiritish uzoq |
| **Ombor strukturasi** (javon, polka) | Hozir kerak emas: ombor kichik va unda tovar ko'p saqlanmaydi |
| **O'lchamlarni kategoriya bo'yicha ajratish** | Kiyim (S, M, L) va oyoq kiyim (36–41) bitta ro'yxatda. Ro'yxat uzayib ketsa kerak bo'ladi |

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
