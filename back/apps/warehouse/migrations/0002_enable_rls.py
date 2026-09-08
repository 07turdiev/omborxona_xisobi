"""Ombor jadvallariga tenant izolyatsiyasi policy'sini qo'shadi."""

from django.db import migrations

from apps.core.db import enable_rls


class Migration(migrations.Migration):
    dependencies = [('warehouse', '0001_initial')]

    operations = [
        enable_rls('warehouse_warehouse'),
        enable_rls('warehouse_warehouseaccess'),
    ]
