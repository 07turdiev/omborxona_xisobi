# Lokal ishga tushirish va sinash

## 1. Nima allaqachon sozlangan

Bazangizda quyidagilar yaratildi:

| Nima | Qiymat |
|---|---|
| Baza | `omborxona_xisobi` |
| Django roli | `omborxona_app` (parol `2002`) |
| Extensionlar | `ltree`, `pg_trgm`, `btree_gin` |

**Nega yangi rol kerak bo'ldi.** Siz bergan `omborxona` roli **SUPERUSER** va
**BYPASSRLS** huquqiga ega. PostgreSQL'da Row Level Security bunday rolga
**umuman qo'llanmaydi** — ya'ni butun tenant izolyatsiyasi ishlamas edi va
bir do'kon ikkinchisining ma'lumotini ko'rardi. Shuning uchun Django uchun
alohida oddiy rol yaratildi.

`omborxona` roli o'z holicha qoldi — undan admin ishlari (extension
o'rnatish, baza yaratish) uchun foydalanish mumkin. Eski `mborxona_xisobi`
bazasi ham tegilmadi; kerak bo'lmasa o'chirib yuboring:

```bash
psql -U omborxona -c "DROP DATABASE mborxona_xisobi"
```

Sozlamalar [back/.env](../back/.env) da. U git'ga tushmaydi.

## 2. Ishga tushirish — eng oson yo'li

Repo ildizidagi ikkita faylni **ikki marta bosing**:

| Fayl | Nima qiladi |
|---|---|
| `backend.bat` | Django serverini ishga tushiradi — http://127.0.0.1:8000 |
| `frontend.bat` | Vue serverini ishga tushiradi — http://localhost:5173 |

Ikkalasi ham ochiq turishi kerak. Yopish uchun oynada `Ctrl+C`.

## 3. Backend — qo'lda

PowerShell'da:

```powershell
cd D:\Sites\omborxona_xisobi\back
.\.venv\Scripts\python.exe manage.py runserver
```

`venv` ni faollashtirib ishlatmoqchi bo'lsangiz:

```powershell
.\.venv\Scripts\Activate.ps1
python manage.py runserver
```

> `Activate.ps1` "running scripts is disabled" xatosini bersa, yuqoridagi
> to'g'ridan-to'g'ri `python.exe` chaqiruvidan foydalaning — u hech qanday
> sozlama talab qilmaydi.

Boshqa foydali buyruqlar:

```powershell
.\.venv\Scripts\python.exe manage.py migrate      # baza sxemasini yangilash
.\.venv\Scripts\python.exe manage.py seed_demo    # demo ma'lumot
.\.venv\Scripts\python.exe manage.py test         # testlar
```

Backend: http://127.0.0.1:8000

Demo foydalanuvchilar (parol ikkalasida ham `demo12345`):

| Login | Parol | Tashkilot |
|---|---|---|
| `qurilish` | `demo12345` | Baraka qurilish mollari — `mashina` (6 m³), `vagon` (60 m³) |
| `kiyim` | `demo12345` | Zamon kiyim-kechak — `tup` (10 dona), `top` (50 m) |
| `superadmin` | `admin12345` | Ikkala tashkilotning egasi + Django admin paneli |

Ikkita tashkilot ataylab: tenant izolyatsiyasini brauzerda o'zingiz
tekshirib ko'rishingiz uchun.

`superadmin` `seed_demo` tomonidan yaratiladi va ikkala tashkilotga ega
qilib qo'shiladi. **Django superuser huquqi faqat `/admin/` ga taalluqli** —
interfeysda ma'lumot ko'rish uchun a'zolik kerak, chunki RLS superuserga ham
qo'llanadi (jadvallarda `FORCE ROW LEVEL SECURITY`).

Boshqa superuser kerak bo'lsa:

```bash
.venv/Scripts/python.exe manage.py createsuperuser
```

## 4. Frontend

```bash
cd front
npm run dev
```

Frontend: http://localhost:5173 — `/api` so'rovlari backendga proxy qilinadi.

> **Eslatma:** tarmog'ingizda sertifikat MITM bor, shuning uchun `npm install`
> kabi tarmoqqa chiqadigan buyruqlarga `NODE_OPTIONS=--use-system-ca` prefiksi
> kerak. `npm run dev` va `npm run build` uchun kerak emas.

## 5. Testlar

```bash
cd back
.venv/Scripts/python.exe manage.py test              # hammasi
.venv/Scripts/python.exe manage.py test apps.units   # bitta ilova
```

Django test uchun `test_omborxona_xisobi` bazasini o'zi yaratadi va
o'chiradi — shuning uchun `omborxona_app` roliga `CREATEDB` huquqi berilgan.

**Testlarda tenant konteksti majburiy.** RLS bilan himoyalangan jadvalga
kontekstsiz murojaat qilsangiz nol qator qaytadi (xato emas — shunchaki
bo'sh). Shuning uchun:

```python
from apps.core.tenancy import tenant_context

with tenant_context(tenant.id):
    CustomUnit.objects.create(name='mashina', definition='6 * m3')
```

## 6. Tenant izolyatsiyasini o'z ko'zingiz bilan ko'rish

Backend ishlab turganda:

```bash
# qurilish do'koni nomidan token olish
curl -s -X POST http://127.0.0.1:8000/api/auth/login/ \
     -H "Content-Type: application/json" \
     -d '{"username":"qurilish","password":"demo12345"}'

# olingan access token bilan birliklar ro'yxati
curl -s http://127.0.0.1:8000/api/units/ -H "Authorization: Bearer <TOKEN>"
```

`qurilish` tokeni bilan `mashina` va `vagon`, `kiyim` tokeni bilan `tup` va
`top` ko'rinadi. Bir-birinikini hech qanday usul bilan ko'rib bo'lmaydi —
bu Django kodida emas, **bazaning o'zida** cheklangan.

Konversiya ham ajratilgan:

```bash
# qurilish uchun ishlaydi -> "12"
curl -s "http://127.0.0.1:8000/api/units-convert/?value=2%20mashina&unit=m3" \
     -H "Authorization: Bearer <QURILISH_TOKEN>"

# kiyim uchun xato -> "mashina" degan birlik u yerda yo'q
curl -s "http://127.0.0.1:8000/api/units-convert/?value=2%20mashina&unit=m3" \
     -H "Authorization: Bearer <KIYIM_TOKEN>"
```

Bir foydalanuvchi bir nechta tashkilotga a'zo bo'lsa, `X-Tenant-Id`
sarlavhasi bilan qaysi biri ekanini ko'rsatadi. A'zoligi yo'q tashkilot
ID si berilsa — hech narsa ko'rinmaydi.

## 7. API hujjatlari

| Manzil | Nima |
|---|---|
| http://127.0.0.1:8000/api/docs/ | Swagger UI |
| http://127.0.0.1:8000/api/redoc/ | ReDoc |
| http://127.0.0.1:8000/admin/ | Django admin |

## 8. Foydali buyruqlar

```bash
# RLS to'g'ri sozlanganini tekshirish (superuser rol, yetishmayotgan policy)
.venv/Scripts/python.exe manage.py check --database default

# demo ma'lumotni qaytadan yaratish
.venv/Scripts/python.exe manage.py seed_demo --reset

# InvenTree manbasi NOTICE dagi digestga mos ekanini tekshirish
.venv/Scripts/python.exe ../scripts/verify_source_digest.py
```

## 9. Yangi model qo'shganda — RLS ni unutmang

Tashkilotga tegishli har bir model `apps.core.models.TenantOwnedModel` dan
meros olishi va migratsiyasida RLS policy'si bo'lishi shart:

```python
# apps/<ilova>/migrations/000X_enable_rls.py
from django.db import migrations
from apps.core.db import enable_rls


class Migration(migrations.Migration):
    dependencies = [('<ilova>', '000X-1_...')]
    operations = [enable_rls('<jadval_nomi>')]
```

Unutsangiz `manage.py check` xato beradi va deploy to'xtaydi —
[apps/core/checks.py](../back/apps/core/checks.py) buni tekshiradi.
