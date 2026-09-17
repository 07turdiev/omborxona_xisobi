# Qurilmalarni ulash va sinash

Skaner va printerlar kelganda shu ro'yxat bo'yicha yuriladi. Har qadamda
**dasturning o'zida qanday tekshirish** ham yozilgan — qurilma
"ulandi" deb hisoblanishi uchun shu tekshiruv o'tishi shart.

---

## 1. Shtrix-kod skaneri

Skaner klaviatura kabi ishlashi kerak (USB HID keyboard rejimi): kodni
yozadi va oxirida **Enter** bosadi. Dastur boshqa rejimlarni (COM-port,
HID POS) bilmaydi.

| Qadam | Nima qilinadi |
|---|---|
| 1 | Skanerni USB ga ulang. Qo'shimcha drayver kerak emas |
| 2 | Qo'llanmasidagi **"USB HID Keyboard"** shtrix-kodini skanerlang |
| 3 | Oxiriga **Enter (CR) qo'shish** shtrix-kodini skanerlang |
| 4 | Klaviatura tilini **English (US)** ga qo'ying |

### Tekshirish

1. Bloknotni oching va istalgan tovar kodini skanerlang. Natija:
   `2000000000725` kabi raqam chiqadi va kursor keyingi qatorga tushadi.
   Raqam o'rniga harf chiqsa — 2-qadam bajarilmagan.
2. Dasturda **Kassa** bo'limini oching va shu kodni skanerlang. Tovar
   savatga tushishi kerak.

### Rus klaviaturasi bilan sinash — majburiy

Windows'da til `RU` ga o'tib qolsa, ba'zi skanerlar raqam o'rniga
kirill harflarini yozadi.

1. Til panelida **RU** ni tanlang.
2. Kassada tovarni skanerlang.
3. Tovar baribir topilishi kerak.

Topilmasa: skanerni "Raqamli klaviatura (Num Pad) rejimi" ga o'tkazing —
bu rejimda raqamlar tildan qat'i nazar bir xil yuboriladi. Qo'llanmada
odatda "Emulate Numeric Keypad" deb yoziladi.

> Chekdagi shtrix-kod ataylab **faqat raqamdan** iborat (`2026000001`) —
> aynan shu sabab: harflar klaviatura tiliga bog'liq bo'lib qolardi.

---

## 2. Yorliq printeri (40 × 30 mm)

| Qadam | Nima qilinadi |
|---|---|
| 1 | Ishlab chiqaruvchi drayverini o'rnating |
| 2 | Windows → Printerlar → drayver sozlamalari |
| 3 | Qog'oz o'lchamini **40 × 30 mm** qilib yarating |
| 4 | Hoshiyalarni (margin) **0** ga qo'ying |
| 5 | Zichlik (darkness) o'rtacha; tezlik past — kichik shriftlar aniqroq chiqadi |

Dastur sahifa o'lchamini o'zi ham beradi (`@page { size: 40mm 30mm }`),
lekin drayverdagi qog'oz noto'g'ri bo'lsa brauzer uni kichraytiradi.

### Tekshirish

1. **Mahsulotlar** → mahsulot qatoridagi **Yorliqlar** tugmasi.
2. Chop etish oynasida:
   - qog'oz o'lchami **40 × 30 mm** ko'rinishi kerak;
   - masshtab **100 %**, "Fit to page" **o'chiq**;
   - har yorliq alohida sahifada.
3. Bosib chiqaring va o'lchang: yorliq cho'zilmagan, kesilmagan bo'lsin.
4. Chiqqan yorliqni skanerlang — kod o'qilishi kerak.

Yorliq o'lchami boshqacha bo'lsa: **Sozlamalar** bo'limida enini va
bo'yini o'zgartiring, drayverdagi qog'ozni ham shunga moslang.

---

## 3. Chek printeri (80 mm)

| Qadam | Nima qilinadi |
|---|---|
| 1 | Drayverni o'rnating |
| 2 | Qog'oz eni **80 mm**, bo'yi **avtomatik** (roll / receipt) |
| 3 | Hoshiyalar **0** |
| 4 | **Avtomatik kesish (auto-cut)** ni yoqing — chek oxirida qog'oz kesiladi |

### Tekshirish

1. Kassada sinov sotuvini yakunlang — chop etish oynasi o'zi ochiladi.
2. Qog'oz eni **80 mm** ko'rinishi va matn kesilmasligi kerak.
3. Bosib chiqaring va tekshiring:
   - eng kichik matn ham **kamida 2 mm balandlikda** (qonun talabi) —
     lupa kerak bo'lmasin;
   - pastdagi shtrix-kod skanerlanadi;
   - chek oxiri avtomatik kesiladi.
4. Chiqqan chekdagi shtrix-kodni **Qaytarish** bo'limida skanerlang —
   o'sha chek ochilishi kerak.

---

## 4. Kassa kompyuteri

- Brauzer: Chrome yoki Edge (yangi versiya).
- Ekran eni kamida **1366 px** — kassa oynasi shunga moslangan.
- Chop etish oynasida **"Headers and footers"** ni o'chiring, aks holda
  chekda sana va sahifa manzili chiqadi.
- Brauzerni kassa sahifasida ochiq qoldiring; savat brauzer xotirasida
  saqlanadi va tasodifan yangilansa yo'qolmaydi.

---

## 5. Hammasi ulangach

- [ ] Skaner ingliz va rus tilida bir xil ishlaydi
- [ ] Yorliq 40 × 30 mm da to'g'ri chiqadi va skanerlanadi
- [ ] Chek 80 mm da chiqadi, matn 2 mm dan kichik emas, avtomatik kesiladi
- [ ] Chekdagi shtrix-kod qaytarishda ochiladi
- [ ] Inventarizatsiya skaner bilan sinalgan (har skan +1 dona)
