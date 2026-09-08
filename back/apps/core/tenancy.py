"""Joriy tenant konteksti va PostgreSQL Row Level Security bilan ishlash.

Loyihaning 1-arxitektura qarori: bitta baza, bitta schema, har jadvalda
`tenant_id`, izolyatsiya PostgreSQL RLS orqali.

Ishlash prinsipi:

1. Har so'rov boshida `TenantMiddleware` foydalanuvchining tenantini
   aniqlaydi va uni `contextvar` ga yozadi.
2. Shu bilan birga bazaga `SET LOCAL app.tenant_id = '<uuid>'` yuboriladi.
3. Har jadvaldagi RLS policy `tenant_id = current_setting('app.tenant_id')`
   shartini qo'llaydi.

`SET LOCAL` tranzaksiya bilan chegaralangan — tranzaksiya tugashi bilan
qiymat avtomatik tozalanadi. Shuning uchun middleware so'rovni
`transaction.atomic()` ichiga o'raydi: ulanish pulida qayta ishlatilgan
ulanishga begona tenant qiymati "yopishib" qolmaydi.

**Muhim:** RLS jadval egasiga va superuserga standart holda qo'llanmaydi.
Shu sababli har jadvalda `FORCE ROW LEVEL SECURITY` yoqiladi, va Django
ishlatadigan baza foydalanuvchisi `SUPERUSER` yoki `BYPASSRLS` bo'lmasligi
shart. Buni `check_rls_configuration()` tekshiradi.
"""

from __future__ import annotations

import uuid
from contextlib import contextmanager
from contextvars import ContextVar, Token

from django.db import connection, transaction

# Joriy so'rov (yoki vazifa) qaysi tenant nomidan bajarilayotgani.
# `None` — tenant aniqlanmagan; bu holda RLS hech qanday qator qaytarmaydi.
_current_tenant_id: ContextVar[uuid.UUID | None] = ContextVar(
    'current_tenant_id', default=None
)

# Baza sessiya o'zgaruvchisining nomi. RLS policy'lari shunga tayanadi.
TENANT_SETTING = 'app.tenant_id'


def get_current_tenant_id() -> uuid.UUID | None:
    """Joriy kontekstdagi tenant ID sini qaytaradi."""
    return _current_tenant_id.get()


def set_current_tenant_id(tenant_id: uuid.UUID | None) -> Token:
    """Joriy kontekstga tenant ID ni yozadi.

    Qaytarilgan `Token` ni `reset_current_tenant_id()` ga berib, oldingi
    holatni tiklash mumkin. To'g'ridan-to'g'ri chaqirish o'rniga
    `tenant_context()` menejeridan foydalanish afzal.
    """
    return _current_tenant_id.set(tenant_id)


def reset_current_tenant_id(token: Token) -> None:
    """Kontekstni `set_current_tenant_id()` dan oldingi holatga qaytaradi."""
    _current_tenant_id.reset(token)


def apply_tenant_to_connection(tenant_id: uuid.UUID | None) -> None:
    """Bazaga joriy tenantni bildiradi (`SET LOCAL app.tenant_id`).

    Ochiq tranzaksiya ichida chaqirilishi kerak, aks holda `SET LOCAL`
    darhol kuchini yo'qotadi va RLS hech qanday qator qaytarmaydi.

    `tenant_id` `None` bo'lsa o'zgaruvchi bo'sh satrga o'rnatiladi —
    `current_setting(..., true)::uuid` buni `NULL` ga aylantiradi va
    solishtiruv hech qachon rost bo'lmaydi. Ya'ni tenant aniqlanmagan
    holat **yopiq** (fail-closed): ma'lumot ko'rinmaydi.
    """
    value = str(tenant_id) if tenant_id else ''

    with connection.cursor() as cursor:
        # set_config() parametrlashtirilgan qiymat qabul qiladi;
        # `SET LOCAL` esa faqat literal, ya'ni SQL injection xavfi bo'lardi.
        cursor.execute("SELECT set_config(%s, %s, true)", [TENANT_SETTING, value])


@contextmanager
def tenant_context(tenant_id: uuid.UUID | None):
    """Berilgan tenant nomidan kod bajarish uchun kontekst menejeri.

    Fon vazifalari (Celery), boshqaruv buyruqlari va testlarda
    ishlatiladi — u yerda HTTP so'rov va middleware yo'q.

    Namuna:
        with tenant_context(tenant.id):
            StockMovement.objects.create(...)

    **Tranzaksiyani o'zi ochadi.** `SET LOCAL` tranzaksiya bilan
    chegaralangan: tranzaksiyasiz chaqirilsa PostgreSQL uni jimgina
    e'tiborsiz qoldiradi va RLS hech narsa qaytarmaydi. Bu xavfsiz
    (fail-closed), lekin juda chalg'ituvchi — "ma'lumot bazada bor,
    lekin ko'rinmayapti" holati. Shuning uchun ochiq tranzaksiya
    bo'lmasa, shu yerda ochiladi.
    """
    token = set_current_tenant_id(tenant_id)

    # Allaqachon tranzaksiya ichida bo'lsak, yangisini ochmaymiz:
    # savepoint ortiqcha yuk beradi va `SET LOCAL` baribir tashqi
    # tranzaksiya oxirigacha amal qiladi.
    if connection.in_atomic_block:
        try:
            apply_tenant_to_connection(tenant_id)
            yield
        finally:
            reset_current_tenant_id(token)
            apply_tenant_to_connection(None)

        return

    try:
        with transaction.atomic():
            apply_tenant_to_connection(tenant_id)
            yield
    finally:
        reset_current_tenant_id(token)


def check_rls_configuration() -> list[str]:
    """RLS to'g'ri sozlanganini tekshiradi, muammolar ro'yxatini qaytaradi.

    `manage.py check` orqali chaqiriladi (apps.py da ro'yxatdan o'tgan),
    shuning uchun noto'g'ri sozlangan baza ishlab chiqarishga chiqmaydi.
    """
    problems: list[str] = []

    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT current_user,
                   usesuper,
                   usebypassrls
            FROM pg_user
            WHERE usename = current_user
        """)
        row = cursor.fetchone()

    if row is None:
        return ['Baza foydalanuvchisi haqida ma\'lumot olinmadi']

    username, is_super, bypass_rls = row

    if is_super:
        problems.append(
            f'Baza foydalanuvchisi "{username}" SUPERUSER — RLS unga '
            'qo\'llanmaydi va tenantlar izolyatsiyasi ishlamaydi. '
            'Django uchun alohida, oddiy foydalanuvchi yarating.'
        )

    if bypass_rls:
        problems.append(
            f'Baza foydalanuvchisi "{username}" BYPASSRLS huquqiga ega — '
            'RLS chetlab o\'tiladi. Huquqni olib tashlang: '
            f'ALTER ROLE {username} NOBYPASSRLS;'
        )

    return problems
