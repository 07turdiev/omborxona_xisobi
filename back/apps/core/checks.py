"""`manage.py check` uchun tenant izolyatsiyasi tekshiruvlari.

Maqsad: RLS policy qo'shishni unutib bo'lmasin. `TenantOwnedModel` dan
meros olgan har bir model uchun bazada `tenant_isolation` policy'si
bo'lishi shart; bo'lmasa `check` xato beradi va deploy to'xtaydi.

Barcha tekshiruvlar `database` tegi bilan ro'yxatdan o'tgan, ya'ni
`manage.py check --database default` bilan ishga tushadi. Baza mavjud
bo'lmasa tekshiruv jimgina o'tkazib yuboriladi — CI da migratsiyasiz
`check` chaqirish odatiy holat.
"""

from __future__ import annotations

from django.apps import apps
from django.core.checks import Error, Warning, register
from django.db import OperationalError, ProgrammingError, connection

from apps.core.db import POLICY_NAME


def _tenant_owned_models():
    """`TenantOwnedModel` dan meros olgan barcha konkret modellar."""
    from apps.core.models import TenantOwnedModel

    return [
        model
        for model in apps.get_models()
        if issubclass(model, TenantOwnedModel) and not model._meta.abstract
    ]


def _inspect_tables() -> tuple[set[str], set[str]] | None:
    """(mavjud jadvallar, policy'si bor jadvallar); bazaga ulanib bo'lmasa None."""
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT tablename FROM pg_tables WHERE schemaname = current_schema()
            """)
            existing = {row[0] for row in cursor.fetchall()}

            cursor.execute(
                'SELECT tablename FROM pg_policies WHERE policyname = %s',
                [POLICY_NAME],
            )
            with_policy = {row[0] for row in cursor.fetchall()}

        return existing, with_policy
    except (OperationalError, ProgrammingError):
        return None


@register('database')
def check_rls_policies(app_configs, **kwargs):
    """Har bir tenantga tegishli jadvalda RLS policy borligini tekshiradi."""
    models = _tenant_owned_models()

    if not models:
        return []

    inspected = _inspect_tables()

    if inspected is None:
        return [
            Warning(
                'Bazaga ulanib bo\'lmadi, RLS policy tekshiruvi o\'tkazib yuborildi.',
                hint='Baza ishga tushgach `manage.py check --database default` ni qayta chaqiring.',
                id='core.W001',
            )
        ]

    existing, with_policy = inspected
    errors = []

    for model in models:
        table = model._meta.db_table

        # Jadval hali yaratilmagan bo'lsa, tekshirishga narsa yo'q. Bu
        # `migrate` ning birinchi ishga tushishi uchun zarur: policy
        # migratsiya ichida qo'shiladi, ya'ni u tekshiruv paytida hali
        # mavjud emas. Jadval paydo bo'lgach keyingi `check` uni ushlaydi.
        if table not in existing:
            continue

        if table not in with_policy:
            errors.append(
                Error(
                    f'"{table}" jadvalida tenant izolyatsiyasi policy\'si yo\'q.',
                    hint=(
                        'Migratsiyaga qo\'shing: '
                        f'apps.core.db.enable_rls("{table}")'
                    ),
                    obj=model,
                    id='core.E001',
                )
            )

    return errors


@register('database')
def check_database_role(app_configs, **kwargs):
    """Django ishlatadigan baza roli RLS ni chetlab o'tmasligini tekshiradi."""
    from apps.core.tenancy import check_rls_configuration

    try:
        problems = check_rls_configuration()
    except (OperationalError, ProgrammingError):
        return []

    return [
        Error(message, id='core.E002')
        for message in problems
    ]
