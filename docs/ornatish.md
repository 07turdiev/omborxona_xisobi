# Do'konga o'rnatish — bir kunlik ish tartibi

Bu hujjat kassa kompyuterini noldan ishga tayyorlash uchun. Tizimning
o'zi serverda turadi (<https://madlensen.uz>) — kassa kompyuteriga
faqat **chop etish agenti** o'rnatiladi. Usiz ham savdo ishlaydi,
lekin har chek va yorliqda brauzerning chop etish oynasi ochiladi va
kassir qo'lda **Print** bosadi.

Ish tartibi muhim: **avval qurilmalar, keyin dastur.** O'rnatuvchi
skript printerlarni o'zi topadi, lekin ularni fizik ulab, qog'oz
o'lchamini sozlab qo'yish kerak — buni dastur qila olmaydi.

---

## 1. O'zingiz bilan olib boradigan narsalar

| Nima | Izoh |
|---|---|
| **USB fleshka** | Ichida `agent` papkasi. GitHub'dan `Code -> Download ZIP`, ichidan faqat shu papka |
| **Chek qog'ozi** | 80 mm, bir-ikki rulon zaxira |
| **Yorliq rulonlari** | 40 × 30 mm |
| **Tarmoq kabeli** | Chek printerini routerga ulash uchun (USB dan ishonchliroq) |
| **Telefon** | Internet tarqatish uchun: do'kon interneti ishlamay qolsa ham o'rnatishni tugatish mumkin |

Oldindan bilib qo'yish kerak:

- Do'kon Wi-Fi/tarmog'ining paroli
- Router paneliga kirish (chek printeriga doimiy IP band qilish uchun)
- Kompyuterda **administrator** huquqi bormi

---

## 2. Qurilmalarni tayyorlash

Batafsil tartib: [hardware.md](hardware.md). Qisqa ro'yxat:

1. **Drayverlar.** `xprintertech.com/download` -> XP-365B va XP-Q80AS.
2. **Yorliq printeri (XP-365B).** USB ga ulanadi. Qog'oz o'lchamini
   40 × 30 mm qilib qo'yiladi va oraliq kalibrlanadi
   ([hardware.md, 2.1 va 2.3](hardware.md)).
3. **Chek printeri (XP-Q80AS).** Tarmoq kabelini ulang va **doimiy IP**
   bering. Zavoddan `192.168.123.100` IP bilan va DHCP o'chirilgan
   holda keladi — shuning uchun u darhol ko'rinmaydi
   ([hardware.md, 3.3](hardware.md)). IP ni routerda MAC bo'yicha band
   qilib qo'ying, aks holda bir kun kelib o'zgaradi va chek chiqmay
   qoladi.
4. **Skaner.** Ulanadi va Notepad'da sinaladi: shtrix-kod raqam bo'lib
   tushishi kerak.
5. **Chrome** o'rnatilgan bo'lsin.

> Chek printerini USB da qoldirish ham mumkin — o'rnatuvchi uni
> ulashuv orqali ishlatadi. Lekin LAN afzal: USB porti uzilsa chek
> chiqmay qoladi va buni kassir darhol tushunmaydi.

---

## 3. Bir bosishda o'rnatish

Fleshkadagi `agent` papkasini ochib **`ORNAT.cmd`** ni ikki marta
bosing. Skript administrator huquqini o'zi so'raydi.

Nima qiladi:

| Qadam | Izoh |
|---|---|
| 1. Node.js | Yo'q bo'lsa `winget` bilan o'rnatadi |
| 2. Papka | `C:\madlensen\` tuzilmasini yaratadi, agentni ko'chiradi |
| 3. Printerlar | Topadi, yorliq printerini `XP365B` nomi bilan ulashadi, chek printerining IP sini aniqlaydi |
| 4. Sozlama | `C:\madlensen\config.json` ni yozadi |
| 5. Avtomatik ishga tushish | Kassir kompyuterga kirganda agent fonda ko'tariladi |
| 6. Tekshirish | Sinov cheki va sinov yorlig'ini chiqaradi |

Skript ikki-uch savol berishi mumkin: qaysi printer yorliq uchun,
qaysi biri chek uchun. Taxmin qilmaydi — ofisdagi boshqa tarmoq
printeri tanlanib qolmasligi uchun ataylab so'raydi.

Qayta ishlatish xavfsiz: har qadam o'zidan oldingi holatni tekshiradi.
Bir joyda to'xtab qolsa, muammoni tuzatib yana ishga tushirsangiz
bo'ladi — qilingan ish takrorlanmaydi.

### Tuzilma

```
C:\madlensen\
  config.json     <- sozlama. FAQAT SHU FAYL TAHRIRLANADI.
  agent\          <- dastur. Yangilanganda butunlay almashtiriladi.
    agent.log     <- xabarlar shu yerda
```

Sozlama agent papkasidan **tashqarida** turadi: agentni yangilaganda
`agent` papkasini o'chirib yangisini qo'yasiz, `config.json` esa o'z
joyida qoladi.

---

## 4. Qo'lda o'rnatish — skript ishlamasa

Har qadamni alohida bajarish mumkin. Tartib bir xil.

**1. Node.js.** Administrator PowerShell'da:

```powershell
winget install OpenJS.NodeJS.LTS
```

Tekshirish (**yangi** oynada): `node --version` -> `v20` yoki yuqorisi.
`winget` bo'lmasa <https://nodejs.org> dan LTS o'rnatiladi.

**2. Papkani yarating** va fleshkadan `agent` papkasini
`C:\madlensen\agent` ga ko'chiring.

**3. Yorliq printerini ulashing.** Administrator PowerShell'da:

```powershell
Get-Printer | Select-Object Name
Set-Printer -Name "Xprinter XP-365B" -Shared $true -ShareName "XP365B"
```

**4. Sozlamani yozing.** `C:\madlensen\config.json`:

```json
{
  "port": 7777,
  "origins": ["https://madlensen.uz"],
  "codePage": "cp1252",
  "printers": {
    "receipt": {
      "transport": "tcp",
      "host": "CHEK-PRINTER-IP",
      "port": 9100,
      "columns": 48,
      "cut": "full",
      "feedBeforeCut": 5
    },
    "label": {
      "transport": "windows",
      "share": "\\\\127.0.0.1\\XP365B",
      "density": 11,
      "speed": 3
    }
  }
}
```

Uchta ehtiyot shart:

- `origins` da do'konning **haqiqiy manzili** bo'lishi kerak. Agent
  boshqa manzildan kelgan so'rovni rad etadi va chek brauzer oynasi
  orqali chiqib ketadi.
- Faylni **BOM'siz UTF-8** da saqlang. Notepad'ning `UTF-8 with BOM`
  varianti agentni ishdan chiqaradi: `config.json o'qilmadi`.
- Chek printeri USB da bo'lsa `receipt` ni ham ulashuvga o'tkazing:
  `"transport": "windows", "share": "\\\\127.0.0.1\\XPQ80AS"`.

**5. Avtomatik ishga tushishni yoqing:**

```powershell
cd C:\madlensen\agent
powershell -ExecutionPolicy Bypass -File install-service.ps1
```

O'chirish kerak bo'lsa: `uninstall-service.ps1`.

**6. Tekshiring:** <http://127.0.0.1:7777/health> printerlar ro'yxatini
JSON bo'lib qaytarsin.

---

## 5. Qabul qilish ro'yxati

O'rnatish tugadi deyish uchun hammasi bajarilishi kerak.

- [ ] `http://127.0.0.1:7777/health` javob beradi, `receipt` uchun
      `"responds": true`
- [ ] Saytda **Sozlamalar -> Qurilmalarni sinash**: «Agent ishlayapti»
      yozuvi bor
- [ ] Sinov cheki chiqdi, kesildi, matn 80 mm ga to'g'ri joylashgan
- [ ] Sinov yorlig'i chiqdi va **skaner uni o'qiydi** (ko'z bilan
      baholash yetmaydi: zichlik ortiqcha bo'lsa qora joylar yoyilib,
      kod o'qilmay qoladi)
- [ ] Bitta sinov sotuvi qilindi va **Chrome'ning chop etish oynasi
      ochilmadi**
- [ ] Skaner **rus klaviaturasi yoqilgan** holda ham to'g'ri o'qiydi
      ([hardware.md, 4-bo'lim](hardware.md))
- [ ] `sudo reboot` emas — kompyuter **qayta yuklangandan** keyin
      agent o'zi ko'tarildi (kassir kirishi bilan)
- [ ] Ish stolida «Madlen sen» yorlig'i bor
- [ ] **Kassir hisobi kassir rolida**, administrator emas, paroli
      kuchli — sayt ochiq internetda
- [ ] Boshlang'ich ma'lumot kiritildi: kategoriya, o'lcham, rang,
      xodimlar; keyin birinchi kirim

Oxirgi ikkita band dasturga tegishli emas, lekin ularsiz do'konni
ochib bo'lmaydi.

---

## 6. Muammolar

| Belgi | Sabab va yechim |
|---|---|
| Chop etish oynasi ochilyapti | Agent ishlamayapti yoki `origins` da sayt manzili yo'q. `agent.log` ni ko'ring |
| `config.json o'qilmadi` | Fayl BOM bilan saqlangan. BOM'siz UTF-8 da qayta yozing |
| Chek chiqmaydi, yorliq chiqadi | Chek printeri IP si o'zgargan. `Test-NetConnection <ip> -Port 9100` |
| Yorliq hira | `config.json` -> `label.density` ni oshiring (0–15), `speed` ni pasaytiring. Keyin agentni qayta ishga tushirib **skaner bilan** sinang |
| Yorliq ikki yorliqqa bo'linib chiqadi | Oraliq kalibrlanmagan: [hardware.md, 2.3](hardware.md) |
| Agent ertalab ishlamaydi | Vazifa boshqa foydalanuvchi uchun yozilgan. `Get-ScheduledTask 'Chop etish agenti' \| Select-Object -ExpandProperty Principal` |
| Skaner harf chiqaradi | Klaviatura tili. [hardware.md, 4-bo'lim](hardware.md) |

Agentni qo'lda ko'rib chiqish kerak bo'lsa:

```powershell
cd C:\madlensen\agent
node index.js
```

Xabarlar ekranda ko'rinadi. Jurnal: `C:\madlensen\agent\agent.log`.

---

## 7. Agent ishlamay qolsa nima bo'ladi

Savdo to'xtamaydi. Ilova jimgina brauzerning chop etish oynasiga
qaytadi — kassir Ctrl+P bosgandek chiqaradi. Agent keyin ko'tarilsa,
ilova uni o'zi topadi: sahifani yangilash shart emas.

Rejalashtirilgan vazifa har 5 daqiqada ham urinib ko'radi, shuning
uchun to'xtab qolgan agent o'zi tiklanadi.
