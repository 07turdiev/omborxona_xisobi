# Qurilmalarni ulash va sinash

Do'konda ishlatiladigan qurilmalar:

| Qurilma | Model | Ulanish | Izoh |
|---|---|---|---|
| Yorliq printeri | **Xprinter XP-365B** | USB | To'g'ridan-to'g'ri termal, 203 dpi, yorliq 40×30 mm |
| Chek printeri | **Xprinter XP-Q80AS** | USB + LAN | 80 mm, ESC/POS, pul qutisi uchun 24 V chiqish |
| Skaner | **2D skaner "7710"** | USB | HID klaviatura rejimi |

Dastur qurilmalarga brauzer orqali chop etadi — maxsus dastur yoki
drayver kutubxonasi kerak emas. Shuning uchun **drayverdagi qog'oz
o'lchami to'g'ri bo'lishi** hal qiluvchi ahamiyatga ega.

> Hamma tekshiruvlarni dasturning o'zidan qilish mumkin:
> **Sozlamalar → Qurilmalarni sinash**.

---

## 1. Drayverlar

Ikkala printer uchun ham drayver bitta joydan olinadi:

**xprintertech.com/download** → model nomini tanlang (XP-365B, XP-Q80AS)
→ Windows drayverini yuklab oling va o'rnating.

O'rnatgandan keyin: **Windows → Sozlamalar → Bluetooth va qurilmalar →
Printerlar va skanerlar** ro'yxatida ikkala printer ko'rinishi kerak.

---

## 2. Yorliq printeri — XP-365B (40 × 30 mm)

### 2.1. Qog'oz o'lchami

Drayver sozlamalarida (Printer → Printing preferences):

| Sozlama | Qiymat |
|---|---|
| Paper size | **40 × 30 mm** (yo'q bo'lsa — yangi o'lcham yarating) |
| Margins | **0** (to'rt tomondan) |
| Orientation | Portrait |
| Speed | past yoki o'rta — kichik shriftlar aniqroq chiqadi |
| Darkness / Density | o'rta; chiziqlar oqarib chiqsa oshiring |

### 2.2. Yorliqlar orasidagi oraliqni kalibrlash

Rulon almashtirilganda printer yorliq chegarasini "yo'qotishi" mumkin —
u holda chop etish siljib boradi.

1. Printerni o'chiring, rulonni to'g'ri joylang, qopqog'ini yoping.
2. Yoqing va **FEED** tugmasini bosib turing: printer bir necha yorliqni
   chiqarib, oraliqni o'lchaydi va to'xtaydi.
3. Yoki drayverdagi **Calibrate / Gap sensor** tugmasini bosing.

### 2.3. Self-test

Printer yoqilgandan keyin **FEED** ni bosib turib o'chirib-yoqish —
printer o'z sozlamalarini (zichlik, tezlik, sensor turi) yorliqqa
bosadi. Shu varaq drayver bilan mos kelishini tekshiring.

### 2.4. Dasturdan tekshirish

**Sozlamalar → Qurilmalarni sinash → Sinov yorlig'i.**

- Chizg'ich bilan o'lchang: chiziq **roppa-rosa 30 mm** bo'lsin.
  Kaltaroq chiqsa — brauzerda masshtab 100 % emas yoki drayverdagi
  qog'oz o'lchami boshqa.
- Yorliq **ramkasi to'liq** ko'rinsin, chetlari kesilmasin.
- Chiqqan shtrix-kodni skanerlang — o'qilishi shart.

---

## 3. Chek printeri — XP-Q80AS (80 mm)

### 3.1. Qog'oz o'lchami

| Sozlama | Qiymat |
|---|---|
| Paper size | **80 × 297 mm** yoki "Roll 80mm" |
| Margins | **0** |
| Auto-cut | **yoqilgan** — chek oxirida qog'oz kesiladi |

Bosiladigan en 80 mm rulonda odatda **72 mm** — dastur aynan shunga
moslangan.

### 3.2. Pul qutisi

Pul qutisi printerning **24 V (RJ-11/RJ-12)** chiqishiga ulanadi va
ESC/POS buyrug'i bilan ochiladi. Brauzerdan chop etishda bu buyruq
yuborilmaydi, shuning uchun drayverda **"Open cash drawer before
printing"** (yoki shunga o'xshash) bandini yoqing — u holda har chek
bosilganda quti ochiladi.

### 3.3. LAN orqali ulash (ixtiyoriy)

Printer USB bilan ham ishlaydi. LAN kerak bo'lsa: self-test varag'ida
printerning IP manzili yoziladi, drayverda **Standard TCP/IP port**
sifatida qo'shiladi.

### 3.4. Dasturdan tekshirish

**Sozlamalar → Qurilmalarni sinash → Sinov cheki.**

- Chiziq **50 mm** bo'lsin.
- Har o'lchamdagi matn yozib qo'yilgan (4.5 / 4.0 / 3.0 mm). Eng kichigi
  ham **2 mm dan baland** bo'lishi kerak — bu qonun talabi.
- Shtrix-kod skanerlansin.
- Chek oxiri avtomatik kesilsin.

---

## 4. Skaner — "7710"

Skaner klaviatura kabi ishlashi kerak: kodni yozadi va oxirida
**Enter** yuboradi.

| Qadam | Nima qilinadi |
|---|---|
| 1 | Skanerni USB ga ulang (drayver kerak emas) |
| 2 | Qo'llanmadagi **USB HID Keyboard** kodini skanerlang |
| 3 | **Enter (CR) suffiks** kodini skanerlang — eng muhimi |
| 4 | Klaviatura tilini **English (US)** ga qo'ying |

### Dasturdan tekshirish

**Sozlamalar → Qurilmalarni sinash → Skanerni sinash** maydoniga
skanerlang. Jadvalda ko'rinadi:

| Ustun | Nima bo'lishi kerak |
|---|---|
| Kod | Skanerlangan kod; raqam bo'lmagan belgi bo'lsa qizil ogohlantirish chiqadi |
| Uzunligi | Tovar kodi — 13, chek kodi — 10 |
| Enter | **bor** |
| Oraliq | **50 ms dan kichik** |
| Bazada | Tovar yoki chek topilgani |

### Rus klaviaturasi bilan sinash — majburiy

Windows tili `RU` ga o'tib qolsa, ba'zi skanerlar raqam o'rniga kirill
harflarini yuboradi.

1. Til panelida **RU** ni tanlang.
2. Sinov maydoniga skanerlang.
3. Kod o'zgarmasligi kerak. O'zgarsa — skanerni **"Emulate Numeric
   Keypad"** rejimiga o'tkazing: bu rejimda raqamlar tildan qat'i nazar
   bir xil yuboriladi.

> Chekdagi shtrix-kod ataylab **faqat raqamdan** iborat (`2026000001`) —
> aynan shu sabab.

---

## 5. Chrome sozlamalari

Chop etish oynasida (Ctrl+P):

| Sozlama | Qiymat |
|---|---|
| Destination | **To'g'ri printer** (yorliq uchun XP-365B, chek uchun XP-Q80AS) |
| Margins | **None** |
| Scale | **100 %** (Default emas — "Fit to printable area" kodni kichraytiradi) |
| Headers and footers | **o'chiq** |
| Background graphics | yoqilgan |

Bu sozlamalar Chrome'da printer bo'yicha eslab qolinadi — bir marta
to'g'rilash kifoya.

---

## 6. Uchidan-uchiga sinov

Qurilmalar sozlangach, haqiqiy oqimni tekshiring:

1. **Mahsulotlar** → biror mahsulotda **Yorliqlar** → yorliqni bosib
   chiqaring.
2. **Kassa** ga o'ting va chiqqan yorliqni skanerlang — tovar savatga
   tushsin.
3. Sotuvni yakunlang — chek o'zi chop etilsin.
4. **Qaytarish** bo'limini oching va **chekdagi shtrix-kodni**
   skanerlang — o'sha chek ochilishi kerak.
5. **Inventarizatsiya → Yangi** → bir tovarni bir necha marta
   skanerlang — har skan +1 qo'shilsin.

Shu besh qadam o'tsa, qurilmalar to'liq ishlayapti.

---

## 7. Tez-tez uchraydigan muammolar

| Belgi | Sabab | Yechim |
|---|---|---|
| Shtrix-kod o'qilmaydi | Brauzer masshtabi 100 % emas | Chrome → Scale: 100 % |
| Yorliq siljib chiqadi | Oraliq kalibrlanmagan | FEED bilan kalibrlang (2.2) |
| Chek juda och | Zichlik past | Drayverda Darkness ni oshiring |
| Kod o'rniga harflar | Klaviatura tili | Skanerni Numeric Keypad rejimiga o'tkazing |
| Enter kelmaydi | Suffiks sozlanmagan | Qo'llanmadagi CR suffiks kodini skanerlang |
| Chek kesilmaydi | Auto-cut o'chiq | Drayverda yoqing |
