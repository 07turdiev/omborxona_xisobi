"""Migratsiyalarda RLS policy'larini o'rnatish uchun yordamchilar.

Har bir `tenant_id` ustuni bo'lgan jadval uchun migratsiyada
`EnableRowLevelSecurity('table_name')` operatsiyasi qo'shiladi.

Nega qo'lda: Django RLS ni bilmaydi, shuning uchun policy'lar xom SQL
bilan yoziladi. `apps.core.checks` esa `tenant_id` ustuni bor, lekin
policy yo'q jadvallarni topib, `manage.py check` da xato beradi —
ya'ni policy qo'shishni unutib bo'lmaydi.
"""

from __future__ import annotations

from django.db import migrations

from apps.core.tenancy import TENANT_SETTING

POLICY_NAME = 'tenant_isolation'

_ENABLE_SQL = """
ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;
ALTER TABLE {table} FORCE ROW LEVEL SECURITY;

CREATE POLICY {policy} ON {table}
    USING (tenant_id = NULLIF(current_setting('{setting}', true), '')::uuid)
    WITH CHECK (tenant_id = NULLIF(current_setting('{setting}', true), '')::uuid);
"""

_DISABLE_SQL = """
DROP POLICY IF EXISTS {policy} ON {table};
ALTER TABLE {table} NO FORCE ROW LEVEL SECURITY;
ALTER TABLE {table} DISABLE ROW LEVEL SECURITY;
"""


def enable_rls(table: str) -> migrations.RunSQL:
    """Jadvalga tenant izolyatsiyasi policy'sini qo'shuvchi migratsiya.

    `NULLIF(..., '')` muhim: `set_config` bo'sh satr yozganda
    `''::uuid` cast xatosi chiqardi, `NULL::uuid` esa solishtiruvni
    shunchaki rost emas qiladi. Ya'ni tenant o'rnatilmaganda so'rov
    xato bermaydi, faqat nol qator qaytaradi (fail-closed).
    """
    params = {'table': table, 'policy': POLICY_NAME, 'setting': TENANT_SETTING}

    return migrations.RunSQL(
        sql=_ENABLE_SQL.format(**params),
        reverse_sql=_DISABLE_SQL.format(**params),
    )
