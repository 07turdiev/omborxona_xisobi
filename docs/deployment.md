# Ishlab chiqarishga chiqarish

Bu hujjat tizimni haqiqiy serverga qo'yish tartibini beradi. Lokal
ishga tushirish uchun [development.md](./development.md) ga qarang.

---

## 1. Nima kerak

| Nima | Izoh |
|---|---|
| Server | 2 CPU, 4 GB RAM yetarli. Do'kon soni o'nlab bo'lsa ham. |
| Docker + Docker Compose | Boshqa hech narsa o'rnatish shart emas |
| Domen | Masalan `ombor.example.uz`, A yozuvi server IP siga |
| Reverse proxy | Caddy yoki Traefik — HTTPS sertifikati uchun |

**Nima uchun HTTPS `docker-compose.yml` da yo'q.** Sertifikat
yangilanishi ilova hayot siklidan mustaqil bo'lishi kerak: ilovani
qayta qurganingizda sertifikat ishlashda davom etsin. Shuning uchun
tashqi proxy tavsiya qilinadi.

---

## 2. Birinchi ishga tushirish

```bash
git clone <repo> /srv/omborxona
cd /srv/omborxona

cp .env.production.example .env.production
```

`.env.production` ni to'ldiring. **Majburiy** maydonlar:

```bash
# Yangi kalit yaratish
docker run --rm python:3.13-slim python -c \
  "import secrets; print(''.join(secrets.choice('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%^&*(-_=+)') for _ in range(50)))"
```

| O'zgaruvchi | Nima |
|---|---|
| `SECRET_KEY` | Yuqoridagi buyruq natijasi |
| `ALLOWED_HOSTS` | Domeningiz |
| `CSRF_TRUSTED_ORIGINS` | `https://` bilan domeningiz |
| `POSTGRES_PASSWORD` | Kuchli parol |

Keyin:

```bash
docker compose up -d --build
docker compose exec backend python manage.py migrate
docker compose exec backend python manage.py createsuperuser
```

Tekshirish:

```bash
docker compose exec backend python manage.py check --deploy
docker compose exec backend python manage.py check --database default
```

Ikkinchi buyruq **eng muhimi**: u har bir jadvalda RLS policy borligini
va baza roli `SUPERUSER`/`BYPASSRLS` emasligini tekshiradi.

---

## 3. Reverse proxy (Caddy namunasi)

`/etc/caddy/Caddyfile`:

```
ombor.example.uz {
    reverse_proxy localhost:8080
}
```

Caddy sertifikatni o'zi oladi va yangilaydi. `WEB_PORT` ni
`.env.production` da o'zgartirsangiz, bu yerda ham o'zgartiring.

---

## 4. Xavfsizlik: nima tekshirilgan

Django `check --deploy` quyidagilarni talab qiladi va ular
`DEBUG=False` bo'lganda avtomatik yoqiladi
([back/config/settings.py](../back/config/settings.py)):

| Sozlama | Nima qiladi |
|---|---|
| `SECURE_SSL_REDIRECT` | HTTP so'rovni HTTPS ga yo'naltiradi |
| `SECURE_PROXY_SSL_HEADER` | Proxy orqasida HTTPS ni to'g'ri aniqlaydi |
| `SESSION_COOKIE_SECURE` | Cookie faqat HTTPS orqali ketadi |
| `CSRF_COOKIE_SECURE` | CSRF tokeni ham |
| `SESSION_COOKIE_HTTPONLY` | JavaScript cookie'ni o'qiy olmaydi |
| `X_FRAME_OPTIONS = DENY` | Sahifani begona iframe'ga solib bo'lmaydi |
| `SECURE_CONTENT_TYPE_NOSNIFF` | Brauzer Content-Type ni taxmin qilmaydi |

### HSTS haqida ogohlantirish

`SECURE_HSTS_SECONDS` — brauzerga «bu domenga faqat HTTPS orqali
murojaat qil» deydi. **Qaytarib olish qiyin**: brauzer qiymatni eslab
qoladi va muddat tugagunicha HTTP ga tushmaydi. Sertifikat buzilsa,
sayt butunlay ochilmay qoladi.

Shuning uchun:

1. Boshida `3600` (1 soat) bilan qoldiring — namunada shunday.
2. Sertifikat bir necha hafta barqaror ishlaganiga ishonch hosil qiling.
3. Keyin `31536000` (1 yil) ga oshiring.
4. `SECURE_HSTS_INCLUDE_SUBDOMAINS` ni faqat **barcha** subdomenlar
   HTTPS da ishlasa yoqing.

---

## 5. Zaxira nusxa

**Bu ixtiyoriy emas.** Ombor hisobi — do'konning moliyaviy tarixi;
uni yo'qotish tovarni yo'qotishdan og'irroq.

```bash
chmod +x scripts/backup.sh scripts/restore.sh

# Qo'lda
./scripts/backup.sh

# Har kuni soat 3 da
crontab -e
0 3 * * * cd /srv/omborxona && ./scripts/backup.sh >> /var/log/ombor-backup.log 2>&1
```

Skript bo'sh yoki juda kichik fayl chiqsa **xato bilan tugaydi**.
Sabab: eng xavfli holat — «zaxira bor» deb o'ylab yurish, aslida esa
bo'sh fayl saqlanayotgan bo'lishi.

Nusxalar 30 kun saqlanadi (`KEEP_DAYS` bilan o'zgartiriladi).

### Zaxirani serverdan tashqariga chiqaring

Server ishdan chiqsa, undagi zaxira ham yo'qoladi. Kamida:

```bash
# Boshqa serverga
0 4 * * * rsync -a /srv/omborxona/backups/ backup@boshqa-server:/backups/ombor/
```

### Tiklashni sinab ko'ring

```bash
./scripts/restore.sh backups/omborxona_xisobi-20260909-030000.dump
```

**Yiliga kamida bir marta sinang.** Tiklanmaydigan zaxira — zaxira
emas, faqat xotirjamlik illyuziyasi. Skript tiklashdan oldin joriy
holatning nusxasini oladi, ya'ni sinov xavfsiz.

---

## 6. Yangilanish

```bash
cd /srv/omborxona
git pull

docker compose build
docker compose exec backend python manage.py migrate
docker compose up -d

docker compose exec backend python manage.py check --database default
```

Migratsiyani konteynerni qayta ishga tushirishdan **oldin** bajaring:
yangi kod eski sxemada ishlamasligi mumkin.

---

## 7. Kuzatish

```bash
# Loglar
docker compose logs -f backend
docker compose logs -f db
docker compose logs -f worker beat   # fon vazifalari

# Holat
docker compose ps

# Baza hajmi
docker compose exec db psql -U omborxona_app -d omborxona_xisobi \
  -c "SELECT pg_size_pretty(pg_database_size('omborxona_xisobi'))"

# Eng katta jadvallar
docker compose exec db psql -U omborxona_app -d omborxona_xisobi -c "
  SELECT relname, pg_size_pretty(pg_total_relation_size(relid))
  FROM pg_catalog.pg_statio_user_tables
  ORDER BY pg_total_relation_size(relid) DESC LIMIT 10"
```

### Fon vazifalari

`worker` va `beat` konteynerlari Celery'ni ishga tushiradi. Hozircha bitta
vazifa bor — **Markaziy bank valyuta kursi**, kuniga uch marta (08:05,
12:05, 17:05 Toshkent vaqti). U nima uchun muhim: kurs yangilanmasa,
tizim eng oxirgi eski kursni ishlatadi va dollar kirimining tannarxi
jimgina noto'g'ri hisoblanadi.

Ishlayotganini tekshirish:

```bash
# beat jadvalni yuboryaptimi
docker compose logs beat | grep sync-cbu

# worker bajaryaptimi — "Markaziy bank kursi yozildi" qatori
docker compose logs worker | grep "kursi yozildi"

# qo'lda, hoziroq
docker compose exec backend python manage.py sync_exchange_rates
```

`beat` **faqat bitta nusxada** ishlashi kerak (`docker compose up --scale
beat=2` qilmang) — aks holda har vazifa ikki marta yuboriladi.

Celery'siz server bo'lsa (masalan oddiy VPS, Docker'siz), xuddi shu ishni
cron bajaradi:

```bash
5 8,12,17 * * * cd /app && python manage.py sync_exchange_rates
```

`stock_stockmovement` eng tez o'sadigan jadval bo'ladi — u append-only
jurnal va hech qachon tozalanmaydi. Bu ataylab: u haqiqat manbai.

---

## 8. Chiqarishdan oldin ro'yxat

- [ ] `.env.production` to'ldirilgan, `SECRET_KEY` yangi
- [ ] `DEBUG=False`
- [ ] `ALLOWED_HOSTS` da faqat haqiqiy domen
- [ ] Baza roli `SUPERUSER`/`BYPASSRLS` emas
- [ ] `check --deploy` va `check --database default` toza
- [ ] HTTPS ishlaydi, sertifikat avtomatik yangilanadi
- [ ] Zaxira cron ga qo'yilgan va **bir marta tiklab sinalgan**
- [ ] Zaxira boshqa serverga ko'chiriladi
- [ ] `worker` va `beat` ishlayapti, sozlamalarda bugungi sanali
      "Markaziy bank" kursi paydo bo'lgan
- [ ] **Demo parollar almashtirilgan** — `demo12345`, `admin12345`,
      `omborchi12345` hujjatlarda ochiq yozilgan
- [ ] Demo ma'lumot o'chirilgan yoki haqiqiy ma'lumot bilan
      almashtirilgan (`seed_demo` faqat sinov uchun)

Oxirgi ikkitasi ayniqsa muhim: demo hisoblar `owner` rolida va ular
bilan hamma narsani o'zgartirish mumkin.

---

## 9. Hali qilinmagan

| Nima | Nega kerak bo'lishi mumkin |
|---|---|
| Og'ir hisobotlarni fonga o'tkazish | Celery tayyor, lekin hisobotlar hozircha tez va sinxron. O'nlab ming yozuvda sekinlashsa, Excel eksportini vazifaga aylantirish kerak bo'ladi |
| Termal chek formati | Hozir chop etish brauzer orqali, har qanday printerda ishlaydi. 58/80 mm uchun maxsus shablon printer turi aniqlangach |
| Sentry yoki shunga o'xshash | Xatolarni loglardan qidirish o'rniga bildirishnoma olish |
| Ko'p til | Interfeys faqat o'zbekcha; dizayn prototipida ru/en ham bor edi |
