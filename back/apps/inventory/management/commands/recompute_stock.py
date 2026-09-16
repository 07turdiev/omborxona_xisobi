"""Qoldiq keshini jurnaldan qayta hisoblaydi.

    python manage.py recompute_stock          # faqat tekshiradi
    python manage.py recompute_stock --fix    # farqni tuzatadi

Kesh (`Variant.stock_quantity`) faqat tezlik uchun: haqiqat manbai —
harakatlar jurnali. Bu buyruq ikkalasi mos kelishini tasdiqlaydi.
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Sum

from apps.catalog.models import Variant
from apps.inventory.models import StockMovement


class Command(BaseCommand):
    help = 'Variant qoldig‘ini ombor jurnalidan qayta hisoblaydi'

    def add_arguments(self, parser):
        parser.add_argument(
            '--fix',
            action='store_true',
            help='Farq topilsa, keshni jurnaldagi qiymatga tenglashtiradi',
        )

    def handle(self, *args, **options):
        totals = dict(
            StockMovement.objects.values_list('variant_id')
            .annotate(total=Sum('quantity'))
            .values_list('variant_id', 'total')
        )

        mismatches = []

        for variant in Variant.objects.select_related('product').order_by('id'):
            expected = totals.get(variant.pk, 0)

            if variant.stock_quantity != expected:
                mismatches.append((variant, expected))

        if not mismatches:
            self.stdout.write(self.style.SUCCESS('Farq yo‘q: kesh jurnalga mos.'))
            return

        for variant, expected in mismatches:
            self.stdout.write(
                f'{variant.sku} — {variant}: keshda {variant.stock_quantity}, '
                f'jurnalda {expected}'
            )

        if not options['fix']:
            self.stdout.write(
                self.style.WARNING(
                    f'{len(mismatches)} ta farq topildi. Tuzatish uchun --fix qo‘shing.'
                )
            )
            return

        with transaction.atomic():
            for variant, expected in mismatches:
                variant.stock_quantity = expected
                variant.save(update_fields=['stock_quantity', 'updated_at'])

        self.stdout.write(self.style.SUCCESS(f'{len(mismatches)} ta qoldiq tuzatildi.'))
