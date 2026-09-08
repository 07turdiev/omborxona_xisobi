"""Jurnalni baza darajasida o'zgarmas qiladi va RLS policy'larini qo'shadi.

Model darajasidagi himoya (`StockMovement.save()` / `.delete()`) faqat
ORM orqali o'tgan kodni to'xtatadi. Xom SQL, `queryset.update()`,
`bulk_update()`, admin paneli, `psql` — hammasi uni chetlab o'tadi.

Shuning uchun asosiy kafolat trigger: `stock_stockmovement` jadvalida
`UPDATE` va `DELETE` **umuman mumkin emas**. Loyihaning 3-arxitektura
qarori shu bilan qotiriladi — jurnal haqiqat manbai bo'lishi uchun uni
o'zgartirib bo'lmasligi kerak.

Xato yozuvni tuzatish yo'li bitta: teskari yozuv qo'shish. Shunda tarix
to'liq qoladi.
"""

from django.db import migrations

from apps.core.db import enable_rls

APPEND_ONLY_TRIGGER = """
CREATE OR REPLACE FUNCTION stock_movement_is_append_only()
RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION
        'stock_stockmovement jadvali faqat qo''shish uchun: % taqiqlangan. '
        'Xatoni tuzatish uchun teskari yozuv qo''shing.',
        TG_OP;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER stock_movement_no_update
    BEFORE UPDATE ON stock_stockmovement
    FOR EACH ROW EXECUTE FUNCTION stock_movement_is_append_only();

CREATE TRIGGER stock_movement_no_delete
    BEFORE DELETE ON stock_stockmovement
    FOR EACH ROW EXECUTE FUNCTION stock_movement_is_append_only();
"""

DROP_TRIGGER = """
DROP TRIGGER IF EXISTS stock_movement_no_update ON stock_stockmovement;
DROP TRIGGER IF EXISTS stock_movement_no_delete ON stock_stockmovement;
DROP FUNCTION IF EXISTS stock_movement_is_append_only();
"""


class Migration(migrations.Migration):
    dependencies = [('stock', '0001_initial')]

    operations = [
        migrations.RunSQL(sql=APPEND_ONLY_TRIGGER, reverse_sql=DROP_TRIGGER),
        enable_rls('stock_batch'),
        enable_rls('stock_stockmovement'),
        enable_rls('stock_stockbalance'),
    ]
