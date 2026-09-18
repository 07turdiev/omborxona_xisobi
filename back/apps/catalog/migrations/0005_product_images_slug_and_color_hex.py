"""Mahsulot rasmlari, manzil qismi (slug), rang kodi va tarkib maydonlari.

Qo'lda yozilgan: `slug` takrorlanmasligi kerak, `hex_code` esa bo'sh
qolmasligi kerak — ikkalasi ham mavjud qatorlarga avval to'ldirilib,
keyin cheklov qo'yiladi. Shu sababli operatsiyalar tartibi muhim:
maydonlarni qo'shish → ma'lumotni to'ldirish → cheklovni qo'yish.
"""

import django.core.validators
import django.db.models.deletion
from django.db import migrations, models
from django.utils.text import slugify

#: Seed qilingan va odatda uchraydigan ranglar uchun mos kodlar
KNOWN_COLORS = {
    'oq': '#FFFFFF',
    'qora': '#1A1A1A',
    'qizil': '#D32F2F',
    'ko‘k': '#1976D2',
    'kok': '#1976D2',
    'yashil': '#388E3C',
    'sariq': '#FBC02D',
    'kulrang': '#9E9E9E',
    'jigarrang': '#6D4C41',
    'pushti': '#EC407A',
    'binafsha': '#7B1FA2',
    'bej': '#D7CCC8',
}

DEFAULT_HEX = '#808080'


def fill_colors_slugs_and_images(apps, schema_editor):
    Color = apps.get_model('catalog', 'Color')
    Product = apps.get_model('catalog', 'Product')
    ProductImage = apps.get_model('catalog', 'ProductImage')

    for color in Color.objects.all():
        color.hex_code = KNOWN_COLORS.get(color.name.strip().lower(), DEFAULT_HEX)
        color.save(update_fields=['hex_code'])

    # Tarixiy modelda `save()` dagi avtomatik slug yo'q, shuning uchun
    # bu yerda o'sha qoida takrorlanadi
    taken = set()

    for product in Product.objects.order_by('pk'):
        base = slugify(product.name)[:200] or 'mahsulot'
        candidate = base
        index = 2

        while candidate in taken:
            candidate = f'{base}-{index}'
            index += 1

        taken.add(candidate)
        product.slug = candidate
        product.save(update_fields=['slug'])

    # Eski bitta `photo` → yangi rasm modeli
    from apps.catalog.images import build_sizes

    for product in Product.objects.exclude(photo='').exclude(photo=None):
        try:
            files = build_sizes(product.photo)
        except Exception:
            # Fayl yo'q yoki buzilgan bo'lsa migratsiya to'xtamasin:
            # rasmni administrator qaytadan yuklaydi
            continue

        ProductImage.objects.create(
            product=product, sort_order=0, is_primary=True, **files
        )


class Migration(migrations.Migration):

    dependencies = [
        ('catalog', '0004_category_mxik_code_category_package_code_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='color',
            name='hex_code',
            field=models.CharField(default='', help_text='#RRGGBB ko‘rinishida.', max_length=7, validators=[django.core.validators.RegexValidator(message='Rang kodi #RRGGBB ko‘rinishida bo‘lishi kerak, masalan #1A2B3C.', regex='^#[0-9A-Fa-f]{6}$')], verbose_name='Rang kodi'),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='product',
            name='description',
            field=models.TextField(blank=True, verbose_name='Tavsif'),
        ),
        migrations.AddField(
            model_name='product',
            name='material',
            field=models.CharField(blank=True, help_text='Masalan: 60% paxta, 40% polyester.', max_length=200, verbose_name='Tarkibi'),
        ),
        migrations.AddField(
            model_name='product',
            name='care',
            field=models.CharField(blank=True, help_text='Yuvish va dazmollash ko‘rsatmasi.', max_length=300, verbose_name='Parvarish'),
        ),
        # Vaqtinchalik: avval bo'sh bo'lishi mumkin, quyida to'ldiriladi.
        # `db_index=False` ataylab: `SlugField` o'zi LIKE uchun indeks
        # yaratadi, quyidagi `unique=True` esa xuddi shu nomdagi indeksni
        # qayta yaratmoqchi bo'lib "already exists" xatosini beradi.
        migrations.AddField(
            model_name='product',
            name='slug',
            field=models.SlugField(db_index=False, max_length=220, null=True, verbose_name='Manzil qismi'),
        ),
        migrations.CreateModel(
            name='ProductImage',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True, verbose_name='Yaratilgan')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='O‘zgartirilgan')),
                ('thumb', models.ImageField(upload_to='products/thumb/', verbose_name='Kichik')),
                ('medium', models.ImageField(upload_to='products/medium/', verbose_name='O‘rta')),
                ('large', models.ImageField(upload_to='products/large/', verbose_name='Katta')),
                ('sort_order', models.PositiveSmallIntegerField(default=0, verbose_name='Tartib')),
                ('is_primary', models.BooleanField(default=False, verbose_name='Asosiy')),
                ('color', models.ForeignKey(blank=True, help_text='Bo‘sh bo‘lsa rasm butun mahsulotga tegishli.', null=True, on_delete=django.db.models.deletion.PROTECT, related_name='images', to='catalog.color', verbose_name='Rang')),
                ('product', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='images', to='catalog.product', verbose_name='Mahsulot')),
            ],
            options={
                'verbose_name': 'Mahsulot rasmi',
                'verbose_name_plural': 'Mahsulot rasmlari',
                'ordering': ['sort_order', 'id'],
                'constraints': [models.UniqueConstraint(condition=models.Q(('is_primary', True)), fields=('product',), name='one_primary_image_per_product')],
            },
        ),
        migrations.RunPython(fill_colors_slugs_and_images, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='product',
            name='slug',
            field=models.SlugField(help_text='Nomdan avtomatik yasaladi. O‘zgartirish mumkin, lekin keyin emas.', max_length=220, unique=True, verbose_name='Manzil qismi'),
        ),
        migrations.RemoveField(
            model_name='product',
            name='photo',
        ),
    ]
