"""Ombor jurnali faqat qo'shishga ochiq.

Model darajasida ham tekshiruv bor (`StockMovement.save`/`delete`), lekin
u faqat Python orqali o'tgan yozuvni ushlaydi. Bazadagi trigger esa
`update`/`delete` so'rovini, boshqaruv buyrug'ini va qo'lda yozilgan SQL ni
ham to'xtatadi: qoldiq tarixi haqiqat manbai bo'lgani uchun uni
o'zgartirishning to'g'ri yo'li yo'q — faqat teskari yozuv qo'shiladi.
"""

from django.db import migrations

CREATE = """
CREATE OR REPLACE FUNCTION inventory_movement_append_only()
RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION 'Ombor harakatini o''zgartirib yoki o''chirib bo''lmaydi';
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER inventory_stockmovement_append_only
    BEFORE UPDATE OR DELETE ON inventory_stockmovement
    FOR EACH ROW EXECUTE FUNCTION inventory_movement_append_only();
"""

DROP = """
DROP TRIGGER IF EXISTS inventory_stockmovement_append_only ON inventory_stockmovement;
DROP FUNCTION IF EXISTS inventory_movement_append_only();
"""


class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '0001_initial'),
    ]

    operations = [
        migrations.RunSQL(sql=CREATE, reverse_sql=DROP),
    ]
