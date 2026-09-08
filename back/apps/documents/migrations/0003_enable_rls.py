"""Hujjat jadvallariga tenant izolyatsiyasi policy'sini qo'shadi."""

from django.db import migrations

from apps.core.db import enable_rls


class Migration(migrations.Migration):
    dependencies = [('documents', '0002_initial')]

    operations = [
        enable_rls('documents_document'),
        enable_rls('documents_documentline'),
    ]
