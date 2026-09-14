"""Tarixni baza darajasida o'zgarmas qiladi va RLS policy'sini qo'shadi.

Model darajasidagi himoya (`AuditEvent.save()` / `.delete()`) faqat ORM
orqali o'tgan kodni to'xtatadi. Xom SQL, `queryset.update()`, admin paneli,
`psql` — hammasi uni chetlab o'tadi. Shuning uchun asosiy kafolat trigger:
`audit_auditevent` jadvalida `UPDATE` va `DELETE` umuman mumkin emas.

Naqsh `stock/migrations/0002_append_only_and_rls.py` bilan bir xil.
"""

from django.db import migrations

from apps.core.db import enable_rls

APPEND_ONLY_TRIGGER = """
CREATE OR REPLACE FUNCTION audit_event_is_append_only()
RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION
        'audit_auditevent jadvali faqat qo''shish uchun: % taqiqlangan.',
        TG_OP;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER audit_event_no_update
    BEFORE UPDATE ON audit_auditevent
    FOR EACH ROW EXECUTE FUNCTION audit_event_is_append_only();

CREATE TRIGGER audit_event_no_delete
    BEFORE DELETE ON audit_auditevent
    FOR EACH ROW EXECUTE FUNCTION audit_event_is_append_only();
"""

DROP_TRIGGER = """
DROP TRIGGER IF EXISTS audit_event_no_update ON audit_auditevent;
DROP TRIGGER IF EXISTS audit_event_no_delete ON audit_auditevent;
DROP FUNCTION IF EXISTS audit_event_is_append_only();
"""


class Migration(migrations.Migration):
    dependencies = [('audit', '0001_initial')]

    operations = [
        migrations.RunSQL(sql=APPEND_ONLY_TRIGGER, reverse_sql=DROP_TRIGGER),
        enable_rls('audit_auditevent'),
    ]
