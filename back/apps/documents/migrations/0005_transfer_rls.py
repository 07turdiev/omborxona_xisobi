"""Ko'chirish jadvallariga tenant izolyatsiyasi policy'sini qo'shadi."""

from django.db import migrations

from apps.core.db import enable_rls


class Migration(migrations.Migration):
    dependencies = [('documents', '0004_transfer_transferline_and_more')]

    operations = [
        enable_rls('documents_transfer'),
        enable_rls('documents_transferline'),
    ]
