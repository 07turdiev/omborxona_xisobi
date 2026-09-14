"""To'lovlarni baza darajasida o'zgarmas qiladi va RLS policy'larini qo'shadi.

Qarzning o'zi o'zgaradi (to'langan summa, holat), qabul qilingan to'lov
esa yo'q: pul yozuvini keyin o'zgartirib bo'lsa, kassadagi kamomadni
yashirish mumkin bo'lardi. Naqsh `stock` va `audit` migratsiyalaridagi
bilan bir xil.
"""

from django.db import migrations

from apps.core.db import enable_rls

APPEND_ONLY_TRIGGER = """
CREATE OR REPLACE FUNCTION debt_payment_is_append_only()
RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION
        'debts_debtpayment jadvali faqat qo''shish uchun: % taqiqlangan.',
        TG_OP;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER debt_payment_no_update
    BEFORE UPDATE ON debts_debtpayment
    FOR EACH ROW EXECUTE FUNCTION debt_payment_is_append_only();

CREATE TRIGGER debt_payment_no_delete
    BEFORE DELETE ON debts_debtpayment
    FOR EACH ROW EXECUTE FUNCTION debt_payment_is_append_only();
"""

DROP_TRIGGER = """
DROP TRIGGER IF EXISTS debt_payment_no_update ON debts_debtpayment;
DROP TRIGGER IF EXISTS debt_payment_no_delete ON debts_debtpayment;
DROP FUNCTION IF EXISTS debt_payment_is_append_only();
"""


class Migration(migrations.Migration):
    dependencies = [('debts', '0001_initial')]

    operations = [
        migrations.RunSQL(sql=APPEND_ONLY_TRIGGER, reverse_sql=DROP_TRIGGER),
        enable_rls('debts_debt'),
        enable_rls('debts_debtpayment'),
    ]
