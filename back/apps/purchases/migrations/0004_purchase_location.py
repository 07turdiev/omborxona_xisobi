"""Kirim hujjatida joy: tovar omborga yoki savdo zaliga tushadi.

Eski hujjatlar omborga bog'lanadi — ilgari kirim doim omborga
tushardi, ya'ni bu ularning haqiqiy joyi.
"""

import django.db.models.deletion
from django.db import migrations, models


def fill_location(apps, schema_editor):
    Location = apps.get_model('inventory', 'Location')
    Purchase = apps.get_model('purchases', 'Purchase')

    warehouse = Location.objects.filter(kind='warehouse').order_by('pk').first()

    if warehouse is not None:
        Purchase.objects.filter(location__isnull=True).update(location=warehouse)


class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '0004_shop_is_savdo_zali'),
        ('purchases', '0003_purchaseline_new_sale_price'),
    ]

    operations = [
        migrations.AddField(
            model_name='purchase',
            name='location',
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='purchases',
                to='inventory.location',
                verbose_name='Joy',
            ),
        ),
        migrations.RunPython(fill_location, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='purchase',
            name='location',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name='purchases',
                to='inventory.location',
                verbose_name='Joy',
            ),
        ),
    ]
