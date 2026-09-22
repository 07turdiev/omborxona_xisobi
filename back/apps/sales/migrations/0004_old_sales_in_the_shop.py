"""Eski cheklar savdo zalida sotilgan, omborda emas.

`0003` da ular omborga bog'langan edi. Bu xato: chek kassada, ya'ni
savdo zalida yoziladi. Bekor qilish va qaytarish tovarni chek sotilgan
joyga qaytaradi, shuning uchun eski cheklar ustidan qaytarish tovarni
ombor javoniga tiqib qo'yardi.
"""

from django.db import migrations


def move_to_shop(apps, schema_editor):
    Location = apps.get_model('inventory', 'Location')
    Sale = apps.get_model('sales', 'Sale')

    warehouse = Location.objects.filter(kind='warehouse').order_by('pk').first()
    shop = Location.objects.filter(kind='shop').order_by('pk').first()

    if warehouse is None or shop is None:
        return

    Sale.objects.filter(location=warehouse).update(location=shop)


class Migration(migrations.Migration):

    dependencies = [
        ('inventory', '0004_shop_is_savdo_zali'),
        ('sales', '0003_sale_location'),
    ]

    operations = [
        # Orqaga qaytarish yo'q: omborda sotilgan chek bo'lmaydi
        migrations.RunPython(move_to_shop, migrations.RunPython.noop),
    ]
