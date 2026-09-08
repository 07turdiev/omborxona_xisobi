"""Valyutalar, kurs tarixi va tannarx qatlamlarini yaratadi.

Foydalanish:
    python manage.py seed_pricing

Mavjud jurnal yozuvlaridan FIFO qatlamlarini **qayta quradi**. Bu bir
vaqtning o'zida ikki ishni bajaradi: demo ma'lumotni to'ldiradi va
`rebuild_layers()` haqiqiy ma'lumotda ishlashini ko'rsatadi.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from django.core.management.base import BaseCommand

from apps.core.tenancy import tenant_context
from apps.pricing import services as pricing
from apps.pricing.models import CostLayer, Currency, ExchangeRate
from apps.stock.models import StockBalance
from apps.tenants.models import Tenant

D = Decimal

#: O'zbekiston Markaziy banki kursiga yaqin, demo uchun
USD_RATES = [
    (date(2026, 1, 1), D('12400')),
    (date(2026, 4, 1), D('12580')),
    (date(2026, 7, 1), D('12720')),
]


class Command(BaseCommand):
    help = 'Valyuta, kurs tarixi va FIFO tannarx qatlamlarini yaratadi'

    def handle(self, *args, **options):
        for tenant in Tenant.objects.all():
            self._seed(tenant)

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('Narx ma\'lumoti tayyor.'))

    def _seed(self, tenant: Tenant):
        with tenant_context(tenant.id):
            base, _ = Currency.objects.get_or_create(
                tenant=tenant, code=tenant.base_currency,
                defaults={
                    'name': 'So\'m' if tenant.base_currency == 'UZS' else tenant.base_currency,
                    'symbol': 'so\'m' if tenant.base_currency == 'UZS' else '',
                    'is_base': True,
                },
            )

            usd, _ = Currency.objects.get_or_create(
                tenant=tenant, code='USD',
                defaults={'name': 'AQSh dollari', 'symbol': '$'},
            )

            for valid_from, rate in USD_RATES:
                ExchangeRate.objects.get_or_create(
                    tenant=tenant, currency=usd, valid_from=valid_from,
                    defaults={'rate': rate, 'source': 'Demo'},
                )

            # Mavjud jurnaldan qatlamlarni qayta qurish.
            # Variant kesimida: ko'chirish ikki omborni bog'laydi.
            from apps.catalog.models import Variant

            layers = 0
            variant_ids = (
                StockBalance.objects.values_list('variant_id', flat=True).distinct()
            )

            for variant in Variant.objects.filter(pk__in=list(variant_ids)):
                layers += pricing.rebuild_layers(variant)

            value = pricing.stock_value()
            remaining = CostLayer.objects.filter(quantity_remaining__gt=0).count()

            summary = (
                f'{tenant.name}: {base.code} asosiy, {ExchangeRate.objects.count()} kurs, '
                f'{layers} qatlam qurildi ({remaining} tasi ochiq), '
                f'qoldiq qiymati {value:,.0f}'
            )

        self.stdout.write(summary)
