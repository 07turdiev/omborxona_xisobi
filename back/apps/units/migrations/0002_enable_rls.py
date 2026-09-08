"""`units_customunit` jadvaliga tenant izolyatsiyasi policy'sini qo'shadi."""

from django.db import migrations

from apps.core.db import enable_rls


class Migration(migrations.Migration):
    dependencies = [('units', '0001_initial')]

    operations = [enable_rls('units_customunit')]
