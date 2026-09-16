# Serverga chiqarish

Lokal ishga tushirish uchun [development.md](./development.md) ga
qarang. Tizim qanday ishlashi — [how-it-works.md](./how-it-works.md).

---

## 1. Nima kerak

| Nima | Izoh |
|---|---|
| Server | 2 CPU, 2 GB RAM yetarli. Ubuntu 22.04 yoki 24.04 |
| Docker + Docker Compose | Compose 2.x (`docker compose version`) |
| **PostgreSQL 15+** | Serverning o'zida. 15-versiya majburiy: variantlar cheklovi `NULLS NOT DISTINCT` dan foydalanadi |
| Domen | Masalan `dokon.example.uz`, `A` yozuvi serverning tashqi IP siga |
| Caddy | HTTPS sertifikati uchun (5-bo'lim) |

**Baza nima uchun konteynerda emas.** Do'kon bitta, baza kichik.
Serverdagi PostgreSQL ni zaxiralash, yangilash va kuzatish oddiyroq,
va baza konteyner qayta qurilishiga bog'liq bo'lmaydi.

**HTTPS nima uchun compose'da yo'q.** Sertifikat yangilanishi ilova
hayot siklidan mustaqil bo'lishi kerak: ilovani qayta qurganingizda
sertifikat ishlashda davom etsin.

---

## 2. PostgreSQL

Rasmiy PGDG repozitoriyasidan (Ubuntu paketi eski bo'lishi mumkin):

```bash
sudo apt install -y postgresql-common
sudo /usr/share/postgresql-common/pgdg/apt.postgresql.org.sh   # Enter
sudo apt install -y postgresql-17
```

Rol va baza. `PAROL` o'rniga o'zingiz yaratgan qiymatni qo'ying
(`openssl rand -hex 24`):

```bash
sudo -u postgres psql <<'SQL'
CREATE ROLE dokon_app LOGIN PASSWORD 'PAROL' NOSUPERUSER NOCREATEROLE;
CREATE DATABASE dokon OWNER dokon_app
    ENCODING 'UTF8' TEMPLATE template0
    LOCALE_PROVIDER icu ICU_LOCALE 'uz-UZ' LOCALE 'C.UTF-8';
SQL
```

`ICU_LOCALE 'uz-UZ'` — nomlar o'zbekcha tartibda saralanadi.

### Konteynerdan ulanish

Konteynerlar serverga Docker tarmog'idan (`172.16.0.0/12`) keladi:

```bash
PGCONF=/etc/postgresql/17/main
sudo sed -i "s/^#\?listen_addresses.*/listen_addresses = '*'/" $PGCONF/postgresql.conf
echo "host dokon dokon_app 172.16.0.0/12 scram-sha-256" | sudo tee -a $PGCONF/pg_hba.conf
sudo systemctl restart postgresql
```

`listen_addresses = '*'` bo'lgani uchun 5432 port tashqaridan **yopiq
bo'lishi shart**:

```bash
sudo ufw allow OpenSSH          # AVVAL shu — aks holda SSH uziladi
sudo ufw allow 80,443/tcp
sudo ufw allow from 172.16.0.0/12 to any port 5432 proto tcp
sudo ufw enable
```

---

## 3. Sozlamalar

```bash
sudo mkdir -p /srv && sudo chown "$USER" /srv
git clone <repo-manzili> /srv/dokon
cd /srv/dokon

cp .env.production.example .env.production
ln -s .env.production .env      # compose ${...} ni `.env` dan oladi
chmod 600 .env.production
```

Maxfiy qiymatlarni yarating (faqat harf va raqam — `$` compose'ni,
`@ :` esa `DATABASE_URL` ni buzadi):

```bash
openssl rand -hex 50   # SECRET_KEY
openssl rand -hex 24   # baza paroli
```

`.env.production` da **majburiy**: `SECRET_KEY`, `ALLOWED_HOSTS`,
`CSRF_TRUSTED_ORIGINS`, `DATABASE_URL`, hamda zaxira skriptlari uchun
`POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_HOST`.

`DEBUG=False` bo'lishi shart. Shunda `/api/docs/` va `/api/schema/`
butunlay o'chadi.

---

## 4. Ishga tushirish

```bash
docker compose config --quiet && echo "compose sozlamasi to'g'ri"
docker compose up -d --build
```

**Migratsiya avtomatik qo'llanadi** — konteyner ishga tushganda
`back/entrypoint.sh` avval `migrate` ni bajaradi, keyin gunicorn ni
ochadi. Qo'lda bajarish shart emas.

Administrator yarating:

```bash
docker compose exec backend python manage.py createsuperuser
```

Tekshirish:

```bash
docker compose ps                    # backend "healthy" bo'lishi kerak
docker compose exec backend python manage.py check --deploy
curl -sI http://127.0.0.1:8080 | head -1     # HTTP/1.1 200 OK
```

`docker compose ps` dagi holat muhim: backend konteynerining
tekshiruvi `migrate --check` ni bajaradi, ya'ni "healthy" bo'lmasa
baza sxemasi koddan orqada qolgan.

> `check --deploy` ikkita HSTS ogohlantirishi beradi
> (`SECURE_HSTS_INCLUDE_SUBDOMAINS`, `SECURE_HSTS_PRELOAD`). Bu
> ataylab — 6-bo'limga qarang.

---

## 5. HTTPS

**1. DNS.** Domen panelida `A` yozuvi serverning tashqi IP siga
(`curl -s ifconfig.me` serverda ko'rsatadi). Statik tashqi IP bo'lmasa
sertifikat olinmaydi.

**2. Router.** Server ofisda bo'lsa, 80 va 443 portlarni serverning
ichki manziliga yo'naltiring (port forwarding). Let's Encrypt
sertifikat berishdan oldin domen orqali 80-portga ulanadi.

**3. Caddy:**

```bash
sudo apt install -y debian-keyring debian-archive-keyring apt-transport-https curl
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' \
  | sudo gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' \
  | sudo tee /etc/apt/sources.list.d/caddy-stable.list
sudo apt update && sudo apt install -y caddy
```

`/etc/caddy/Caddyfile`:

```
dokon.example.uz {
    encode gzip
    reverse_proxy 127.0.0.1:8080
}
```

```bash
sudo systemctl reload caddy
sudo journalctl -u caddy -f      # "certificate obtained successfully"
```

**Frontend porti nima uchun faqat `127.0.0.1` da.** Docker o'z
portlarini UFW dan chetlab ochadi — `0.0.0.0:8080` bo'lsa firewall uni
to'smaydi va saytga HTTPS'siz kirish mumkin bo'lardi.

---

## 6. Xavfsizlik

`DEBUG=False` bo'lganda avtomatik yoqiladi
([back/config/settings.py](../back/config/settings.py)):

| Sozlama | Nima qiladi |
|---|---|
| `SECURE_SSL_REDIRECT` | HTTP so'rovni HTTPS ga yo'naltiradi |
| `SECURE_PROXY_SSL_HEADER` | Proxy orqasida HTTPS ni to'g'ri aniqlaydi |
| `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE` | Cookie faqat HTTPS orqali |
| `SESSION_COOKIE_HTTPONLY` | JavaScript cookie'ni o'qiy olmaydi |
| `X_FRAME_OPTIONS = DENY` | Sahifani begona iframe'ga solib bo'lmaydi |
| `SECURE_CONTENT_TYPE_NOSNIFF` | Brauzer Content-Type ni taxmin qilmaydi |

### `/admin/` yopiq

Django admin paneli **domen orqali ochilmaydi**: `front/nginx.conf` da
u 404 qaytaradi. Sabab — admin paneli butun bazaga to'g'ridan-to'g'ri
yo'l ochadi, kundalik ishda esa umuman kerak emas (hamma narsa
ilovaning o'z interfeysida).

Kerak bo'lganda serverning o'zida buyruq bilan:

```bash
docker compose exec backend python manage.py createsuperuser
docker compose exec backend python manage.py recompute_stock --fix
```

### HSTS haqida

`SECURE_HSTS_SECONDS` brauzerga «bu domenga faqat HTTPS orqali murojaat
qil» deydi. **Qaytarib olish qiyin**: brauzer qiymatni eslab qoladi va
muddat tugagunicha HTTP ga tushmaydi.

1. Boshida `3600` (1 soat) bilan qoldiring — namunada shunday.
2. Sertifikat bir necha hafta barqaror ishlaganiga ishonch hosil qiling.
3. Keyin `31536000` (1 yil) ga oshiring.
4. `SECURE_HSTS_INCLUDE_SUBDOMAINS` ni faqat **barcha** subdomenlar
   HTTPS da ishlasa yoqing.

---

## 7. Zaxira nusxa

**Bu ixtiyoriy emas.** Ombor hisobi — do'konning moliyaviy tarixi;
uni yo'qotish tovarni yo'qotishdan og'irroq.

```bash
chmod +x scripts/backup.sh scripts/restore.sh

./scripts/backup.sh                  # qo'lda

crontab -e                           # har kuni soat 3 da
0 3 * * * cd /srv/dokon && ./scripts/backup.sh >> /var/log/dokon-backup.log 2>&1
```

Skript bo'sh yoki juda kichik fayl chiqsa **xato bilan tugaydi**.
Sabab: eng xavfli holat — «zaxira bor» deb o'ylab yurish, aslida esa
bo'sh fayl saqlanayotgan bo'lishi.

Nusxalar 30 kun saqlanadi (`KEEP_DAYS` bilan o'zgartiriladi).

### Serverdan tashqariga chiqaring

Server ishdan chiqsa, undagi zaxira ham yo'qoladi:

```bash
0 4 * * * rsync -a /srv/dokon/backups/ zaxira@boshqa-server:/backups/dokon/
```

### Tiklashni sinab ko'ring

```bash
./scripts/restore.sh backups/dokon-20260916-030000.dump
```

**Yiliga kamida bir marta sinang.** Tiklanmaydigan zaxira — zaxira
emas. Skript tiklashdan oldin joriy holatning nusxasini oladi, ya'ni
sinov xavfsiz.

---

## 8. Yangilash

```bash
cd /srv/dokon
git pull
docker compose up -d --build
docker compose ps        # backend yana "healthy" bo'lishini kuting
```

Migratsiya konteyner ishga tushganda o'zi qo'llanadi. Agar backend
"unhealthy" bo'lib qolsa — migratsiya yiqilgan:

```bash
docker compose logs backend | tail -30
```

---

## 9. Kuzatish

```bash
docker compose logs -f backend
docker compose ps

# Baza hajmi
sudo -u postgres psql -d dokon -c "SELECT pg_size_pretty(pg_database_size('dokon'))"

# Eng katta jadvallar
sudo -u postgres psql -d dokon -c "
  SELECT relname, pg_size_pretty(pg_total_relation_size(relid))
  FROM pg_catalog.pg_statio_user_tables
  ORDER BY pg_total_relation_size(relid) DESC LIMIT 10"
```

`inventory_stockmovement` eng tez o'sadigan jadval bo'ladi — u faqat
qo'shiladigan jurnal va hech qachon tozalanmaydi. Bu ataylab: u
haqiqat manbai.

---

## 10. Chiqarishdan oldin ro'yxat

- [ ] `.env.production` to'ldirilgan, `SECRET_KEY` yangi
- [ ] `DEBUG=False`
- [ ] `ALLOWED_HOSTS` da faqat haqiqiy domen
- [ ] `docker compose ps` — backend **healthy**
- [ ] `check --deploy` da faqat ikkita HSTS ogohlantirishi
- [ ] HTTPS ishlaydi, sertifikat avtomatik yangilanadi
- [ ] `https://domen/admin/` — **404** qaytaradi
- [ ] `https://domen/api/docs/` — **404** qaytaradi (`DEBUG=False`)
- [ ] Zaxira cron ga qo'yilgan va **bir marta tiklab sinalgan**
- [ ] Zaxira boshqa serverga ko'chiriladi
- [ ] Namuna ma'lumot yo'q (`seed_demo` serverda umuman ishlamaydi)
- [ ] Haqiqiy xodimlar yaratilgan, parollari kuchli
