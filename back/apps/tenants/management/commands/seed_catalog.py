"""Demo tashkilotlarga katalog ma'lumotini qo'shadi.

Foydalanish:
    python manage.py seed_catalog

Ikki sohaning farqi ataylab ko'rsatilgan:

- **Qurilish**: bir mahsulotning bitta varianti, lekin o'ram
  konversiyasi muhim ("1 qop = 50 kg", "1 palet = 1500 kg").
- **Kiyim**: bir mahsulotning o'lcham × rang bo'yicha bir nechta
  varianti, o'ram esa kerak emas.

Shu bilan JSONB atributlari va `ProductUnit` nima uchun kerakligi
ko'rinadi.
"""

from __future__ import annotations

from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.catalog.attributes import build_attributes
from apps.catalog.models import (
    AttributeDefinition,
    Barcode,
    Category,
    Product,
    ProductUnit,
    Variant,
)
from apps.core.tenancy import tenant_context
from apps.tenants.models import Tenant

VT = AttributeDefinition.ValueType


class Command(BaseCommand):
    help = 'Demo tashkilotlarga kategoriya, atribut va mahsulot qo\'shadi'

    def handle(self, *args, **options):
        self._seed_construction()
        self._seed_clothing()

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('Katalog demo ma\'lumoti tayyor.'))

    # -- qurilish mollari ----------------------------------------------

    @transaction.atomic
    def _seed_construction(self):
        tenant = Tenant.objects.filter(slug='qurilish').first()

        if tenant is None:
            self.stdout.write('qurilish tashkiloti topilmadi, o\'tkazib yuborildi')
            return

        with tenant_context(tenant.id):
            root, _ = Category.objects.get_or_create(
                tenant=tenant, parent=None, name='Qurilish mollari',
                defaults={'default_unit': 'kg', 'code_prefix': 'QM'},
            )

            cement, _ = Category.objects.get_or_create(
                tenant=tenant, parent=root, name='Sement va aralashmalar',
                defaults={'default_unit': 'kg', 'code_prefix': 'CEM'},
            )

            profile, _ = Category.objects.get_or_create(
                tenant=tenant, parent=root, name='Profil va metall',
                defaults={'default_unit': 'dona', 'code_prefix': 'PRF'},
            )

            # Ildizdagi atribut ikkala ostki kategoriyaga meros o'tadi
            self._define(tenant, root, 'ishlab_chiqaruvchi', 'Ishlab chiqaruvchi', VT.TEXT, position=1)

            self._define(tenant, cement, 'marka', 'Marka', VT.CHOICE, position=2,
                         choices=['M300', 'M400', 'M500'])
            self._define(tenant, cement, 'saqlash_muddati', 'Saqlash muddati', VT.NUMBER,
                         unit='day', position=3)

            self._define(tenant, profile, 'qalinlik', 'Qalinlik', VT.NUMBER,
                         unit='mm', position=2)
            self._define(tenant, profile, 'uzunlik', 'Uzunlik', VT.NUMBER,
                         unit='m', position=3)

            # Sement: bitta variant, lekin uchta o'ram
            product = self._product(
                tenant, cement, 'Portlandsement M400', brand='Bekabad', base_unit='kg'
            )
            variant = self._variant(
                tenant, product, 'CEM-M400', cement,
                {'ishlab_chiqaruvchi': 'Bekabadsement', 'marka': 'M400',
                 'saqlash_muddati': '180'},
                # Narx **bazaviy birlikda** (kg), qop uchun emas:
                # 1 qop = 50 kg, ya'ni 45 000 so'm/qop = 900 so'm/kg.
                # Qopdagi narxni ProductUnit koeffitsienti bilan chiqaramiz.
                purchase='900', sale='1040',
            )

            for unit, factor, default_purchase in [
                ('qop', '50', True),
                ('palet', '1500', False),
                ('tonna', '1000', False),
            ]:
                ProductUnit.objects.get_or_create(
                    tenant=tenant, variant=variant, unit=unit,
                    defaults={
                        'factor_to_base': Decimal(factor),
                        'is_default_purchase': default_purchase,
                        'is_default_sale': unit == 'qop',
                    },
                )

            self._barcode(tenant, variant, '4780123456789')

            # Gips: o'sha "qop" birligi, lekin boshqa og'irlik
            gypsum_product = self._product(
                tenant, cement, 'Gips qurilish uchun', brand='Nurafshon', base_unit='kg'
            )
            gypsum = self._variant(
                tenant, gypsum_product, 'GYP-01', cement,
                {'ishlab_chiqaruvchi': 'Nurafshon', 'marka': 'M300',
                 'saqlash_muddati': '90'},
                # 1 qop gips = 30 kg
                purchase='930', sale='1130',
            )
            ProductUnit.objects.get_or_create(
                tenant=tenant, variant=gypsum, unit='qop',
                defaults={'factor_to_base': Decimal('30'), 'is_default_sale': True},
            )
            self._barcode(tenant, gypsum, '4780123456796')

            # Profil: sonli atributlar
            profile_product = self._product(
                tenant, profile, 'Metall profil 60x27', brand='Knauf', base_unit='dona'
            )
            profile_variant = self._variant(
                tenant, profile_product, 'PRF-6027', profile,
                {'ishlab_chiqaruvchi': 'Knauf', 'qalinlik': '0.6 mm', 'uzunlik': '3 m'},
                purchase='32000', sale='39000',
            )
            self._barcode(tenant, profile_variant, '4780123456802')

            # Hisoblagich kontekst ichida: RLS tashqarida nol qaytaradi
            summary = (
                f'Qurilish: {Category.objects.count()} kategoriya, '
                f'{Product.objects.count()} mahsulot, '
                f'{ProductUnit.objects.count()} oram birligi'
            )

        self.stdout.write(summary)

    # -- kiyim-kechak --------------------------------------------------

    @transaction.atomic
    def _seed_clothing(self):
        tenant = Tenant.objects.filter(slug='kiyim').first()

        if tenant is None:
            self.stdout.write('kiyim tashkiloti topilmadi, o\'tkazib yuborildi')
            return

        with tenant_context(tenant.id):
            root, _ = Category.objects.get_or_create(
                tenant=tenant, parent=None, name='Kiyim-kechak',
                defaults={'default_unit': 'dona', 'code_prefix': 'KY'},
            )

            men, _ = Category.objects.get_or_create(
                tenant=tenant, parent=root, name='Erkaklar kiyimi',
                defaults={'default_unit': 'dona', 'code_prefix': 'ER'},
            )

            self._define(tenant, root, 'material', 'Material', VT.CHOICE, position=1,
                         choices=['Paxta', 'Jinsi', 'Polyester', 'Jun'])

            # Variant o'qlari: shu ikkisi bo'yicha alohida variantlar bo'ladi
            self._define(tenant, root, 'olcham', 'O\'lcham', VT.CHOICE, position=2,
                         choices=['S', 'M', 'L', 'XL'], variant_axis=True)
            self._define(tenant, root, 'rang', 'Rang', VT.CHOICE, position=3,
                         choices=['Oq', 'Qora', 'Ko\'k'], variant_axis=True)

            product = self._product(
                tenant, men, 'Klassik ko\'ylak', brand='Zamon', base_unit='dona'
            )

            # Bir mahsulot, olti variant — har biri alohida qoldiqqa va
            # **alohida shtrix-kodga** ega. Kassada skanerlanganda aynan
            # qaysi o'lcham sotilgani ma'lum bo'lishi kerak.
            code = 4780200000010

            for size in ['M', 'L', 'XL']:
                for color in ['Oq', 'Qora']:
                    variant = self._variant(
                        tenant, product, f'SHIRT-{size}-{color[:2].upper()}', men,
                        {'material': 'Paxta', 'olcham': size, 'rang': color},
                        purchase='95000', sale='149000',
                        name=f'{size} / {color}',
                    )
                    self._barcode(tenant, variant, str(code))
                    code += 1

            summary = (
                f'Kiyim: {Category.objects.count()} kategoriya, '
                f'{Product.objects.count()} mahsulot, '
                f'{Variant.objects.count()} variant'
            )

        self.stdout.write(summary)

    # -- yordamchilar --------------------------------------------------

    def _define(self, tenant, category, key, name, value_type, *, position,
                unit='', choices=None, variant_axis=False):
        AttributeDefinition.objects.get_or_create(
            tenant=tenant, category=category, key=key,
            defaults={
                'name': name,
                'value_type': value_type,
                'unit': unit,
                'choices': choices or [],
                'is_variant_axis': variant_axis,
                'position': position,
            },
        )

    def _product(self, tenant, category, name, *, brand='', base_unit=''):
        product, _ = Product.objects.get_or_create(
            tenant=tenant, category=category, name=name,
            defaults={'brand': brand, 'base_unit': base_unit},
        )
        return product

    def _variant(self, tenant, product, sku, category, values, *,
                 purchase, sale, name=''):
        variant = Variant.objects.filter(sku=sku).first()

        if variant is not None:
            return variant

        return Variant.objects.create(
            tenant=tenant,
            product=product,
            sku=sku,
            name=name,
            attributes=build_attributes(category, values),
            purchase_price=Decimal(purchase),
            sale_price=Decimal(sale),
        )

    def _barcode(self, tenant, variant, code):
        Barcode.objects.get_or_create(
            tenant=tenant,
            code_normalized=Barcode.normalize(code),
            defaults={
                'variant': variant,
                'code': code,
                'code_type': Barcode.CodeType.EAN13,
            },
        )
