# Qurilmalarni ulash va sinash

Do'konda ishlatiladigan qurilmalar:

| Qurilma | Model | Ulanish | Izoh |
|---|---|---|---|
| Yorliq printeri | **Xprinter XP-365B** | USB | To'g'ridan-to'g'ri termal, 203 dpi, yorliq 40×30 mm |
| Chek printeri | **Xprinter XP-Q80AS** | USB + LAN | 80 mm, ESC/POS, pul qutisi uchun 24 V chiqish |
| Skaner | **2D skaner "7710"** | USB | HID klaviatura rejimi |

Dastur ikki yo'l bilan chop etadi:

| Yo'l | Qachon | Nima muhim |
|---|---|---|
| **Chop etish agenti** | Kompyuterda agent ishlab tursa | Oyna ochilmaydi, chek kerakli uzunlikda chiqadi. Sozlash: [agent/README.md](../agent/README.md) |
| **Brauzer** | Agent bo'lmasa — o'zi shunga qaytadi | **Drayverdagi qog'oz o'lchami to'g'ri bo'lishi** hal qiluvchi ahamiyatga ega |

Quyidagi sozlamalar ikkala yo'l uchun ham kerak: agent ham o'sha
qurilmalarga, o'sha qog'ozga chop etadi.

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

### 2.5. Agent uchun ulashish

XP-365B da faqat USB bor. Chop etish agenti unga raw baytlarni yuborishi
uchun printer **ulashilgan** bo'lishi kerak — agent `\\127.0.0.1\NOM`
yo'liga yozadi.

Administrator huquqidagi PowerShell'da (oyna sarlavhasida
*Administrator* yozuvi bo'lsin):

```powershell
Set-Printer -Name "Xprinter XP-365B" -Shared $true -ShareName "XP365B"
Get-Printer -Name "Xprinter XP-365B" | Select-Object Name, Shared, ShareName
```

Ikkinchi qator `Shared: True` va `ShareName: XP365B` ko'rsatishi kerak.
`Access was denied` chiqsa — oyna ko'tarilmagan.

Bu usul haqiqiy qurilmada tekshirilgan: baytlar spooler orqali printerga
o'tadi, yorliqlar ketma-ket va orasida bo'sh yorliqsiz chiqadi.

> Ulashuvni oldindan tekshirib bo'lmaydi: printer ulashuvi fayl tizimi
> obyekti emas va mavjud, ishlaydigan ulashuv ham "topilmadi" deb
> javob beradi. Shuning uchun Sozlamalarda yorliq printeri "tekshirib
> bo'lmaydi" deb turadi — bu xato emas.

Ulashishga ruxsat bo'lmasa, yorliq brauzer orqali chiqaveradi: dastur
agentsiz ham ishlaydi.

---

## 3. Chek printeri — XP-Q80AS (80 mm)

### 3.1. Qog'oz o'lchami — eng muhim qadam

Brauzer orqali chop etishda **sahifa balandligini dastur belgilay
olmaydi**. Chrome `@page` dagi balandlikni e'tiborsiz qoldiradi va
printer drayveridagi qog'oz o'lchamini oladi. XP-80 drayverida standart
qog'oz `USER 72 × 296.9 mm` — shuning uchun har chekdan keyin **~30 sm
lenta** bo'shga ketadi.

Yechim: drayverda **maxsus qog'oz** yaratiladi va o'sha o'lcham
dasturga ham yoziladi.

**1. Drayverda qog'oz yaratish** (Windows):

```
Sozlamalar → Bluetooth va qurilmalar → Printerlar va skanerlar
  → Xprinter XP-80 → Printing preferences → Paper → Custom / New
```

| Maydon | Qiymat |
|---|---|
| Nomi | `Chek 80x110` |
| Eni | **80 mm** |
| Bo'yi | **110 mm** |
| Hoshiyalar | **0** (to'rt tomondan) |

Saqlang va shu qog'ozni **standart** qilib tanlang.

**2. Dasturda o'sha o'lchamni yozing:**

```
Sozlamalar → Chek qog'ozi eni: 80,  Chek sahifasi bo'yi: 110
```

Ikkalasi **aynan bir xil** bo'lishi shart.

**3. Balandlikni qanday tanlash.** Bitta chek chop eting va
**Sozlamalar → Qurilmalarni sinash** sahifasiga qarang: u yerda oxirgi
chek mazmuni necha millimetr bo'lgani yoziladi. Qog'oz bo'yini shundan
biroz katta qilib oling (masalan mazmun 86 mm bo'lsa — 110 mm).

| Sozlama | Qiymat |
|---|---|
| Paper size | **Chek 80×110** (o'zingiz yaratgan) |
| Margins | **0** |
| Auto-cut | **yoqilgan** — chek oxirida qog'oz kesiladi |

Bosiladigan en 80 mm rulonda odatda **72 mm** — dastur aynan shunga
moslangan va mazmunni qog'oz o'rtasiga qo'yadi.

### Nega baribir biroz bo'sh joy qoladi

Sahifa balandligi qat'iy, chek esa har xil uzunlikda bo'ladi. Qisqa
chekda qolgan joy bo'sh chiqadi — bu brauzer orqali chop etishning
narxi. Uni butunlay yo'qotish uchun ESC/POS bilan to'g'ridan-to'g'ri
chop etish kerak (docs/roadmap.md).

Shuning uchun qog'oz bo'yini **odatdagi chekka qarab** tanlang, eng
uzuniga qarab emas: uzun chek ikkinchi sahifaga o'tadi va qatorlar
o'rtasidan uzilmaydi.

### 3.2. Pul qutisi

Pul qutisi printerning **24 V (RJ-11/RJ-12)** chiqishiga ulanadi va
ESC/POS buyrug'i bilan ochiladi. Brauzerdan chop etishda bu buyruq
yuborilmaydi, shuning uchun drayverda **"Open cash drawer before
printing"** (yoki shunga o'xshash) bandini yoqing — u holda har chek
bosilganda quti ochiladi.

### 3.3. LAN orqali ulash

Printer USB bilan ham ishlaydi, lekin LAN afzal: kassa kompyuteri
almashsa ham printer o'z joyida qoladi va chop etish agenti unga
to'g'ridan-to'g'ri **9100-port** orqali yozadi.

#### 1. Zavod sozlamasi — printer darhol ko'rinmaydi

XP-Q80AS zavoddan **`192.168.123.100`** IP bilan va **DHCP o'chirilgan**
holda keladi. Do'kon tarmog'i boshqa pastki tarmoqda bo'lgani uchun
printer tarmoqqa ulangan zahoti ko'rinmaydi — avval IP ni o'zgartirish
kerak, buni esa faqat **USB orqali** qilib bo'ladi.

#### 2. Statik IP berish

XPrinter sozlash dasturida, printer **USB bilan ulangan** holda:

```
Port Select: USB  →  New IP: <do'kon tarmog'idagi bo'sh manzil>
  →  Set New IP  →  DHCP Close
```

Keyin printerni **o'chirib-yoqing** va **FEED** tugmasi bilan self-test
varag'ini chiqaring — yangi IP o'sha varaqda yozilgan bo'lishi kerak.

> Manzilni routerning DHCP diapazonidan **tashqaridan** tanlang, aks
> holda router o'sha IP ni boshqa qurilmaga berib yuborishi mumkin.

#### 3. Routerda MAC bo'yicha band qiling

Router qayta yuklanganda IP o'zgarib ketmasligi uchun printerning MAC
manzili bo'yicha rezervatsiya qiling (DHCP reservation / static lease).
Buni qilmasangiz, bir kuni chek chop etilmay qoladi va sababini topish
qiyin bo'ladi.

#### 4. Tekshirish

PowerShell'da:

```powershell
ping <ip>
Test-NetConnection <ip> -Port 9100
```

**`TcpTestSucceeded : True`** bo'lishi shart. `ping` o'tib, port o'tmasa —
printer tarmoqda bor, lekin chop etish ulanishi band (1-tuzoq).

#### 5. Windows'da port

| Sozlama | Qiymat |
|---|---|
| Port turi | **Standard TCP/IP Port** |
| Protocol | **Raw** |
| Port raqami | **9100** |
| SNMP Status Enabled | **belgilanmagan** (2-tuzoq) |

Ro'yxatda printerning **bitta** yozuvi qolsin va nomi aniq bo'lsin
(masalan `XP-Q80AS LAN`). USB orqali o'rnatilgan eski nusxalarni
o'chiring — aks holda chek noto'g'ri yozuvga ketib, navbatda qotib
qoladi.

#### Ikki tuzoq — ikkalasi ham amalda uchragan

**1. Sozlash dasturi ulanishni ushlab turadi.** Printer bir vaqtda
**bitta** TCP ulanishni qabul qiladi. XPrinter sozlash dasturi ochiq
tursa, o'sha yagona ulanishni egallaydi va na Windows, na agent
printerga yoza oladi. Sozlashni tugatgach dasturni **butunlay yoping** —
trey (bildirishnomalar) belgisini ham tekshiring.

**2. SNMP tufayli "oflayn".** Port sozlamalarida (Configure Port)
**SNMP Status Enabled** yoqilgan bo'lsa, Windows printerni oflayn deb
belgilaydi va topshiriqlar navbatda qolib ketadi — printer aslida
ishlab turgan bo'lsa ham. Bu bandni **o'chiring**.

#### Do'kon uchun yozib qo'yiladigan ma'lumot

| Nima | Qiymat |
|---|---|
| IP manzil | `_______________` |
| MAC manzil | `_______________` |
| Bosiladigan en | 72 mm / 48 belgi |
| Kod sahifasi | WPC1252 |
| Kesuvchi | bor |

> Haqiqiy IP va MAC bu faylga yozilmaydi — ular har do'konda boshqacha.
> Jadvalni to'ldirib, do'konning o'z yozuvlarida saqlang. Agent
> sozlamasida ham o'sha IP ishlatiladi (`agent/config.json` →
> `printers.receipt.host`), u fayl repoga kirmaydi.

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
| Chek chiqmaydi, navbatda qotadi | Port sozlamasida SNMP yoqilgan | Configure Port → SNMP Status Enabled ni o'chiring (3.3) |
| `ping` o'tadi, 9100-port o'tmaydi | XPrinter sozlash dasturi yagona ulanishni ushlab turibdi | Dasturni butunlay yoping (3.3) |
| Router qayta yuklangach printer topilmaydi | IP MAC bo'yicha band qilinmagan | Routerda rezervatsiya qiling (3.3) |
| Printer tarmoqda umuman ko'rinmaydi | Zavod IP `192.168.123.100`, DHCP o'chiq | USB orqali statik IP bering (3.3) |
