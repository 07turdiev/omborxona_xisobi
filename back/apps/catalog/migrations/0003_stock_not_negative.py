"""Qoldiq manfiy bo'lmasligi — bazadagi himoya.

Xizmat qatlamida ham tekshiriladi (`inventory.services.record_movement`),
lekin bu cheklov xatoni oxirgi nuqtada ushlaydi: qo'lda yozilgan SQL yoki
kelajakdagi yangi kod ham qoldiqni manfiyga tushira olmaydi.
"""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('catalog', '0002_barcode_sequence'),
    ]

    operations = [
        migrations.AddConstraint(
            model_name='variant',
            constraint=models.CheckConstraint(
                condition=models.Q(stock_quantity__gte=0),
                name='variant_stock_not_negative',
            ),
        ),
    ]
