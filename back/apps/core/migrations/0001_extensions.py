"""Loyiha talab qiladigan PostgreSQL extensionlari.

Bu migratsiya birinchi bo'lib bajarilishi kerak: `catalog` ilovasidagi
`ltree` maydoni jadval yaratilishidan oldin extension mavjud bo'lishini
talab qiladi. Test bazasi har safar noldan yaratilgani uchun extensionlar
qo'lda emas, migratsiya orqali o'rnatiladi.

PostgreSQL 13 dan boshlab bu uchtasi "trusted" hisoblanadi, ya'ni ularni
superuser emas, **baza egasi** ham o'rnata oladi. Shuning uchun
`omborxona_app` roli uchun yetarli.
"""

from django.contrib.postgres.operations import CreateExtension
from django.db import migrations


class Migration(migrations.Migration):
    initial = True
    dependencies = []

    operations = [
        # Kategoriya daraxti uchun (4-arxitektura qarori)
        CreateExtension('ltree'),
        # Nom bo'yicha noaniq qidiruv uchun
        CreateExtension('pg_trgm'),
        # JSONB va oddiy ustunlarni bitta indeksda birlashtirish uchun
        CreateExtension('btree_gin'),
    ]
