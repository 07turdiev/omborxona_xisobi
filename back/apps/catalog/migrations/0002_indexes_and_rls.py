"""Katalog jadvallariga RLS policy'lari va maxsus indekslar.

Ikkita indeks Django ORM orqali berilmaydi:

- `ltree` yo'li bo'yicha **GiST** indeks — ajdod/avlod so'rovlari
  (`@>`, `<@`) shusiz butun jadvalni skanerlaydi.
- JSONB atributlari bo'yicha **GIN** indeks `jsonb_path_ops` bilan —
  Django `GinIndex` ni beradi, lekin operator klassini emas.
  `jsonb_path_ops` faqat `@>` ni qo'llab-quvvatlaydi, buning evaziga
  standart `jsonb_ops` dan sezilarli kichik va tezroq.
"""

from django.db import migrations

from apps.core.db import enable_rls

CREATE_INDEXES = """
CREATE INDEX catalog_category_path_gist
    ON catalog_category USING GIST (path);

CREATE INDEX catalog_variant_attributes_gin
    ON catalog_variant USING GIN (attributes jsonb_path_ops);
"""

DROP_INDEXES = """
DROP INDEX IF EXISTS catalog_category_path_gist;
DROP INDEX IF EXISTS catalog_variant_attributes_gin;
"""


class Migration(migrations.Migration):
    dependencies = [('catalog', '0001_initial')]

    operations = [
        migrations.RunSQL(sql=CREATE_INDEXES, reverse_sql=DROP_INDEXES),
        enable_rls('catalog_category'),
        enable_rls('catalog_attributedefinition'),
        enable_rls('catalog_product'),
        enable_rls('catalog_variant'),
        enable_rls('catalog_productunit'),
        enable_rls('catalog_barcode'),
    ]
