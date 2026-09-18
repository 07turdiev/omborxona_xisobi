# Chop etish agenti

Kompyuterda turadigan kichik xizmat. Dastur unga chek yoki yorliq
yuboradi, u esa printerga **tayyor baytlarni** uzatadi: ESC/POS (chek)
va TSPL (yorliq).

Nega kerak:

| Brauzer orqali | Agent orqali |
|---|---|
| Har chop etishda oyna ochiladi, kassir **Print** bosadi | Oyna ochilmaydi, faqat qisqa xabar chiqadi |
| Sahifa balandligi qat'iy — chek oxirida bo'sh lenta qoladi | Chek aynan kerakli uzunlikda chiqadi va o'sha yerda kesiladi |
| Shtrix-kodni brauzer rasm qilib chizadi | Kodni printerning o'zi chizadi — chiziqlar nuqtalarga aniq tushadi |
| Pul qutisi drayver sozlamasiga bog'liq | Naqd to'lovda ESC/POS impulsi bilan ochiladi |

**Agent majburiy emas.** O'chirilgan yoki yiqilgan bo'lsa, dastur
jimgina brauzer orqali chop etishga qaytadi — sotuv to'xtamaydi.

---

## Talablar

| Nima | Versiya |
|---|---|
| Node.js | 20+ (sinalgan: 24.13) |
| Windows | Yorliq printeri uchun. Chek printeri LAN orqali ishlaydi, unga OS muhim emas |

Tashqi paket **yo'q** — `npm install` qilish shart emas.

---

## Ishga tushirish

```bash
cd agent
copy config.example.json config.json    # keyin sozlamani to'g'rilang
npm start
```

Tekshirish: brauzerda <http://127.0.0.1:7777/health> — printerlar
ro'yxati JSON bo'lib chiqadi.

Dasturda holat **Sozlamalar → Qurilmalarni sinash** sahifasida
ko'rinadi: versiya, printerlar, oxirgi xatolar va sinov tugmalari.

---

## Sozlama — `config.json`

Bu fayl repoga kirmaydi: unda printerning tarmoqdagi manzili bo'ladi.
Namuna: `config.example.json`.

| Kalit | Standart | Nima |
|---|---|---|
| `port` | 7777 | Agent shu portda, **faqat 127.0.0.1** da tinglaydi |
| `origins` | 5173 portlari | Qaysi manzildagi ilova murojaat qila oladi |
| `codePage` | `cp1252` | Chek printerining kod sahifasi |
| `token` | yo'q | Ixtiyoriy. Bitta kompyuterli o'rnatmada **kerak emas** |

### Chek printeri — `printers.receipt`

| Kalit | Standart | Nima |
|---|---|---|
| `transport` | — | `tcp` (LAN) yoki `windows` (ulashuv) |
| `host`, `port` | 9100 | TCP uchun printer manzili |
| `columns` | 48 | Qog'ozga sig'adigan belgi soni |
| `cashDrawer` | `false` | Har chekda pul qutisini ochish |
| `feedBeforeCut` | 5 | Kesishdan oldin necha qator tortiladi |
| `cut` | `full` | `full`, `partial` yoki `none` |
| `barcodeHeight` | 80 | Nuqta (~10 mm) |
| `barcodeWidth` | 2 | Modul kengligi |

`feedBeforeCut` ni kamaytirmang: bosh bilan pichoq orasida 15–20 mm
masofa bor va kam tortilsa oxirgi qatorlar pichoqdan pastda qoladi.

### Yorliq printeri — `printers.label`

| Kalit | Standart | Nima |
|---|---|---|
| `transport` | — | Odatda `windows` |
| `share` | — | `\\127.0.0.1\XP365B` ko'rinishida |
| `density` | 8 | Qoralik, 0–15. Chiziq oqarib chiqsa oshiring |
| `speed` | 4 | Dyuym/soniya. Pastroq tezlik — aniqroq chiziq |
| `barcodeHeight` | 90 | Nuqta (~11 mm) |

Yorliq o'lchami sozlamada emas, **so'rovda** keladi — uni dastur
do'kon sozlamalaridan oladi (standart 40×30 mm, oraliq 2 mm).

### Xato yozilgan sozlama

Agent ishga tushganda noma'lum kalit haqida ogohlantiradi va
katta-kichik harf xatosida to'g'ri nomni taklif qiladi:

```
config.json: "receipt" printerida "barcodeheight" — "barcodeHeight" bo'lishi kerakmi?
```

Son noto'g'ri bo'lsa (manfiy, matn yoki bo'sh), standart qiymat olinadi
va sabab yoziladi — chek hech qachon shtrix-kodsiz yoki kesilmasdan
chiqmaydi.

---

## Printerlarni ulash

### Chek printeri — LAN, TCP 9100

XP-Q80AS da LAN bor, shuning uchun eng ishonchli yo'l — TCP. Statik IP
berish, routerda band qilish va ikkita amaliy tuzoq:
[docs/hardware.md](../docs/hardware.md) 3.3-bo'limi.

```json
{ "transport": "tcp", "host": "192.0.2.10", "port": 9100 }
```

### Yorliq printeri — USB, Windows ulashuvi

XP-365B da faqat USB bor. Unga raw baytlarni yuborish uchun printer
**ulashiladi**, agent esa `\\127.0.0.1\NOM` yo'liga yozadi.

Administrator huquqidagi PowerShell'da:

```powershell
Set-Printer -Name "Xprinter XP-365B" -Shared $true -ShareName "XP365B"
Get-Printer -Name "Xprinter XP-365B" | Select-Object Name, Shared, ShareName
```

Ikkinchi qator `Shared: True` ko'rsatishi kerak. Bu usul haqiqiy
qurilmada tekshirilgan: baytlar spooler orqali printerga o'tadi va
yorliqlar ketma-ket, orasida bo'sh yorliqsiz chiqadi.

> **Ulashuvni oldindan tekshirib bo'lmaydi.** Printer ulashuvi fayl
> tizimi obyekti emas: unga yozib bo'ladi, lekin `fs.access` ishlaydigan
> ulashuvda ham `ENOENT` qaytaradi. Shuning uchun `/health` bunday
> printer uchun `responds: null` beradi va Sozlamalarda "tekshirib
> bo'lmaydi" deb ko'rinadi. Haqiqiy holat — `lastError` ustunida.

**Agar ulashishga ruxsat bo'lmasa** (masalan domen siyosati taqiqlasa),
ikkita yo'l bor:

1. Yorliqni brauzer orqali chop etish — dastur o'zi shunga qaytadi,
   hech narsa sozlash kerak emas. Kamchiligi: har safar oyna ochiladi.
2. XP-365B ni USB print-server orqasiga qo'yish va uni chek printeri
   kabi `tcp` bilan ulash.

---

## Avtomatik ishga tushirish

```powershell
powershell -ExecutionPolicy Bypass -File install-service.ps1
```

Kassir tizimga kirishi bilan agent ko'tariladi, oyna ochilmaydi,
xabarlar `agent.log` ga yoziladi. **Administrator huquqi kerak emas**
(tekshirilgan).

O'chirish:

```powershell
powershell -ExecutionPolicy Bypass -File uninstall-service.ps1
```

### Nega haqiqiy Windows xizmati emas

1. Xizmat qilish uchun tashqi o'ram kerak bo'lardi (nssm, winsw), agent
   esa ataylab bog'liqliksiz.
2. Xizmat SYSTEM seansida ishlaydi. Yorliq printeriga yozish esa
   ulashuv orqali boradi va u **foydalanuvchi seansida** tekshirilgan.

Shuning uchun logonda ishga tushadigan rejalashtirilgan vazifa
ishlatiladi — u xuddi shu seansda ishlaydi.

---

## Endpoint'lar

| Manzil | Nima qiladi |
|---|---|
| `GET /health` | Versiya, kod sahifasi, printerlar, har biri bo'yicha oxirgi xato |
| `POST /receipt` | Chekni ESC/POS ga o'giradi va yuboradi |
| `POST /labels` | Yorliqlarni TSPL ga o'giradi va yuboradi |

Himoya:

- Faqat `127.0.0.1` da tinglaydi — tarmoqdagi boshqa kompyuter ulana olmaydi.
- `Origin` ro'yxatdagi manzil bo'lishi kerak, aks holda **403**.
- `Origin` umuman bo'lmasa (masalan `curl`) — token talab qilinadi.
- `Content-Type: application/json` bo'lmasa **415**.

---

## Muammolarni topish

| Belgi | Sabab | Yechim |
|---|---|---|
| Sozlamalarda "Agent topilmadi" | Agent ishlamayapti | `npm start` yoki vazifani tekshiring; `agent.log` ga qarang |
| Chek ketmaydi, `lastError` da timeout | Printer IP o'zgargan yoki 9100 band | `Test-NetConnection <ip> -Port 9100`; XPrinter sozlash dasturini yoping |
| Yorliq ketmaydi, `lastError` da ENOENT | Ulashuv nomi boshqa yoki ulashuv o'chgan | `Get-Printer ... Select ShareName` bilan solishtiring |
| Yorliq printeri "tekshirib bo'lmaydi" | Shunday bo'lishi kerak | Bu xato emas — yuqoridagi izohga qarang |
| Sozlama e'tiborsiz qolyapti | Kalit xato yozilgan | Agent ishga tushganda beradigan ogohlantirishni o'qing |

---

## Testlar

```bash
cd agent && npm test        # 85 ta
```

ESC/POS va TSPL baytlari **golden fixture** bilan solishtiriladi:
kutilgan baytlar `tests/fixtures/` da saqlanadi, shuning uchun
tasodifiy o'zgarish darhol ko'rinadi. Fixture o'zgarishi kerak bo'lsa,
eski faylni o'chirib testni ikki marta yurgizing — birinchisi yangisini
yozadi, ikkinchisi tekshiradi.
