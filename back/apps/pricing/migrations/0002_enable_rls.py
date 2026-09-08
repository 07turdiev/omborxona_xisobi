"""Narx jadvallariga tenant izolyatsiyasi policy'sini qo'shadi."""

from django.db import migrations

from apps.core.db import enable_rls


class Migration(migrations.Migration):
    dependencies = [('pricing', '0001_initial')]

    operations = [
        enable_rls('pricing_currency'),
        enable_rls('pricing_exchangerate'),
        enable_rls('pricing_costlayer'),
        enable_rls('pricing_costconsumption'),
    ]
