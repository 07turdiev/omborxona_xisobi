# Ishlab chiqarishga chiqarish

Bu hujjat tizimni haqiqiy serverga qo'yish tartibini beradi. Lokal
ishga tushirish uchun [development.md](./development.md) ga qarang.

---

## 1. Nima kerak

| Nima | Izoh |
|---|---|
| Server | 2 CPU, 4 GB RAM yetarli. Do'kon soni o'nlab bo'lsa ham. Ubuntu 22.04/24.04 |
| Docker + Docker Compose | Compose 2.24.4+ (`docker compose version`) |
| PostgreSQL 15+ | Konteynerda (standart) yoki serverning o'zida — 2B bo'lim |
| Domen | Masalan `ombor.example.uz`, A yozuvi tashqi IP ga |
| Reverse proxy | Caddy — HTTPS sertifikati uchun (3-bo'lim) |

**Nima uchun HTTPS `docker-compose.yml` da yo'q.** Sertifikat
yangilanishi ilova hayot siklidan mustaqil bo'lishi kerak: ilovani
qayta qurganingizda sertifikat ishlashda davom etsin. Shuning uchun
tashqi proxy tavsiya qilinadi.

**PostgreSQL 15+ nima uchun.** Qoldiq jadvalidagi unikal cheklov
`NULLS NOT DISTINCT` dan foydalanadi (15-versiyadan). Ubuntu 22.04 ning
o'z paketi 14 — shuning uchun rasmiy PGDG repozitoriyasi ishlatiladi.

---

## 2. Birinchi ishga tushirish

```bash
sudo mkdir -p /srv && sudo chown "$USER" /srv
git clone https://github.com/07turdiev/omborxona_xisobi.git /srv/omborxona
cd /srv/omborxona

cp .env.production.example .env.production
# compose ${...} qiymatlarini `.env` dan oladi — ikkalasi bitta fayl bo'lsin
ln -s .env.production .env
chmod 600 .env.production
```

Maxfiy qiymatlarni yarating (faqat harf va raqam — `$` compose'ni,
`@ :` esa DATABASE_URL ni buzadi):

```bash
openssl rand -hex 50   # SECRET_KEY
openssl rand -hex 24   # POSTGRES_PASSWORD
```

`.env.production` ni to'ldiring (`nano .env.production`). **Majburiy**:

| O'zgaruvchi | Nima |
|---|---|
| `SECRET_KEY` | Birinchi buyruq natijasi |
| `ALLOWED_HOSTS` | Domeningiz: `ombor.example.uz` |
| `CSRF_TRUSTED_ORIGINS` | `https://` bilan: `https://ombor.example.uz` |
| `POSTGRES_PASSWORD` | Ikkinchi buyruq natijasi |

### 2A. Baza konteynerda (standart)

Qo'shimcha hech narsa kerak emas — 2C ga o'ting.

### 2B. Baza serverning o'zida (native PostgreSQL)

**1. O'rnatish** (rasmiy PGDG repozitoriyasidan):

```bash
sudo apt install -y postgresql-common
sudo /usr/share/postgresql-common/pgdg/apt.postgresql.org.sh   # Enter bosing
sudo apt install -y postgresql-18
```

**2. Rol va baza.** `PAROL` o'rniga `.env.production` dagi
`POSTGRES_PASSWORD` ni qo'ying:

```bash
sudo -u postgres psql <<'SQL'
CREATE ROLE omborxona_app LOGIN PASSWORD 'PAROL'
    NOSUPERUSER NOBYPASSRLS NOCREATEDB NOCREATEROLE;
CREATE DATABASE omborxona_xisobi OWNER omborxona_app
    ENCODING 'UTF8' TEMPLATE template0
    LOCALE_PROVIDER icu ICU_LOCALE 'uz-UZ' LOCALE 'C.UTF-8';
\c omborxona_xisobi
CREATE EXTENSION IF NOT EXISTS ltree;
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS btree_gin;
SQL
```

- `NOSUPERUSER NOBYPASSRLS` — **majburiy**: aks holda RLS bu rolga
  qo'llanmaydi va tashkilotlar bir-birining ma'lumotini ko'radi.
- Rol baza egasi — migratsiya jadval yarata oladi. Jadvallarda
  `FORCE ROW LEVEL SECURITY` yoqilgani uchun egalik RLS ni chetlab
  o'tmaydi.
- Extensionlar `postgres` nomidan oldindan yaratiladi; migratsiya ularni
  mavjud deb o'tkazib yuboradi.
- `ICU_LOCALE 'uz-UZ'` — nomlar o'zbekcha tartibda saralanadi.

**3. Docker konteynerlaridan ulanish.** Konteynerlar serverga
`172.16.0.0/12` tarmog'idan keladi:

```bash
PGCONF=/etc/postgresql/18/main
sudo sed -i "s/^#\?listen_addresses.*/listen_addresses = '*'/" $PGCONF/postgresql.conf
echo "host omborxona_xisobi omborxona_app 172.16.0.0/12 scram-sha-256" \
  | sudo tee -a $PGCONF/pg_hba.conf
sudo systemctl restart postgresql
```

**4. Firewall.** `listen_addresses = '*'` bo'lgani uchun 5432 port
tashqaridan yopiq bo'lishi shart:

```bash
sudo ufw allow OpenSSH          # AVVAL shu — aks holda SSH uziladi
sudo ufw allow 80,443/tcp
sudo ufw allow from 172.16.0.0/12 to any port 5432 proto tcp
sudo ufw enable
sudo ufw status
```

**5. `.env.production`** da B bo'limidagi uch qatorni oching (`#` ni
olib tashlang) va `PAROL` ni almashtiring:

```bash
COMPOSE_FILE=docker-compose.yml:docker-compose.hostdb.yml
POSTGRES_HOST=127.0.0.1
DATABASE_URL=postgres://omborxona_app:PAROL@host.docker.internal:5432/omborxona_xisobi
```

`COMPOSE_FILE` tufayli keyingi barcha `docker compose` buyruqlari
`docker-compose.hostdb.yml` ni o'zi qo'shadi: baza konteyneri ishga
tushmaydi, backend serverdagi bazaga ulanadi.

Zaxira skriptlari `POSTGRES_HOST` ni ko'rib, `pg_dump` ni serverning
o'zida ishga tushiradi.

### 2C. Ishga tushirish

```bash
docker compose config --quiet && echo "compose sozlamasi to'g'ri"

docker compose build
docker compose up -d
docker compose exec backend python manage.py migrate
docker compose exec backend python manage.py createsuperuser
```

`createsuperuser` — tizim superadmini. U interfeysdagi **Kompaniyalar**
bo'limidan do'konlarni va ularning egalarini ochadi.

Tekshirish:

```bash
docker compose ps
docker compose exec backend python manage.py check --deploy
docker compose exec backend python manage.py check --database default
curl -sI http://127.0.0.1:8080 | head -1     # HTTP/1.1 200 OK
```

`check --database default` **eng muhimi**: u har bir jadvalda RLS policy
borligini va baza roli `SUPERUSER`/`BYPASSRLS` emasligini tekshiradi.

---

## 3. HTTPS: domen, router va Caddy

**1. DNS.** Domen boshqaruv panelida `A` yozuvi: `ombor.example.uz` →
ofisning **tashqi** IP manzili (`curl -s ifconfig.me` serverda ko'rsatadi).
Provayder statik tashqi IP bermasa, sertifikat olinmaydi — avval shuni
hal qiling.

**2. Router.** 80 va 443 portlarni server ichki IP siga
(`192.168.100.61`) yo'naltiring (port forwarding / NAT). Let's Encrypt
sertifikat berishdan oldin domen orqali 80-portga ulanib tekshiradi.

**3. Caddy** (serverning o'zida):

```bash
sudo apt install -y debian-keyring debian-archive-keyring apt-transport-https curl
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' \
  | sudo gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' \
  | sudo tee /etc/apt/sources.list.d/caddy-stable.list
sudo apt update && sudo apt install -y caddy
```

`/etc/caddy/Caddyfile` (`sudo nano /etc/caddy/Caddyfile`, eski
tarkibni to'liq almashtiring):

```
ombor.example.uz {
    encode gzip
    reverse_proxy 127.0.0.1:8080
}
```

```bash
sudo systemctl reload caddy
sudo journalctl -u caddy -f      # "certificate obtained successfully" ni kuting
```

Caddy sertifikatni o'zi oladi va yangilaydi. `WEB_PORT` ni
`.env.production` da o'zgartirsangiz, bu yerda ham o'zgartiring.

**Nima uchun frontend porti faqat `127.0.0.1` da.** Docker o'z portlarini
UFW dan chetlab ochadi — `0.0.0.0:8080` bo'lsa firewall uni to'smaydi
va saytga HTTPS'siz kirish mumkin bo'lardi. Qolaversa frontend nginx
Caddy yuborgan `X-Forwarded-Proto` ga ishonadi; unga faqat Caddy
ulanishi kerak.

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
