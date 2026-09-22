"""Savdo zali «Do'kon» emas, «Savdo zali» deb ataladi.

«Do'kon» butun do'konni ham bildirardi: ekranlarda «Ombor → Do'kon»
yozuvi bilan «Zalga chiqarish» tugmasi yonma-yon turib chalkashtirardi.
"""

from django.db import migrations, models


def rename_shop(apps, schema_editor):
    Location = apps.get_model('inventory', 'Location')

    Location.objects.filter(kind='shop', name='Do‘kon').update(name='Savdo zali')


def back_to_dokon(apps, schema_editor):
    Location = apps.get_model('inventory', 'Location')

    Location.objects.filter(kind='shop', name='Savdo zali').update(name='Do‘kon')


class Migration(migrations.Migration):

    dependencies = [
        ('catalog', '0006_remove_mxik_codes'),
        ('inventory', '0003_location_transfer_transferline_variantstock_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='location',
            name='kind',
            field=models.CharField(choices=[('warehouse', 'Ombor'), ('shop', 'Savdo zali')], max_length=10, verbose_name='Turi'),
        ),
        migrations.RunPython(rename_shop, back_to_dokon),
        migrations.AddConstraint(
            model_name='variantstock',
            constraint=models.CheckConstraint(condition=models.Q(('quantity__gte', 0)), name='location_stock_not_negative'),
        ),
    ]
