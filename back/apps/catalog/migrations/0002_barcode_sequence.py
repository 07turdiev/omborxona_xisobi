"""Ichki shtrix-kodlar uchun ketma-ketlik.

Kod `200` + 9 xonali tartib raqami + nazorat raqamidan iborat (EAN-13).
Tartib raqamini bazadagi ketma-ketlik beradi: ikki xodim bir vaqtda
mahsulot qo'shsa ham bir xil kod chiqmaydi (`nextval` tranzaksiyadan
tashqarida ishlaydi va hech qachon takrorlanmaydi).
"""

from django.db import migrations

CREATE = """
CREATE SEQUENCE IF NOT EXISTS catalog_barcode_seq
    START WITH 1
    INCREMENT BY 1
    MINVALUE 1
    MAXVALUE 999999999
    NO CYCLE;
"""

DROP = "DROP SEQUENCE IF EXISTS catalog_barcode_seq;"


class Migration(migrations.Migration):

    dependencies = [
        ('catalog', '0001_initial'),
    ]

    operations = [
        migrations.RunSQL(sql=CREATE, reverse_sql=DROP),
    ]
