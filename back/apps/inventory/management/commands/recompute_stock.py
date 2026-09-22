"""Qoldiq keshini jurnaldan qayta hisoblaydi.

    python manage.py recompute_stock          # faqat tekshiradi
    python manage.py recompute_stock --fix    # farqni tuzatadi

Kesh ikkita: joydagi qoldiq (`VariantStock.quantity`) va variantning
umumiy qoldig'i (`Variant.stock_quantity`). Ikkalasi ham faqat tezlik
uchun — haqiqat manbai harakatlar jurnali. Bu buyruq uchalasi mos
kelishini tasdiqlaydi.
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Sum

from apps.catalog.models import Variant
from apps.inventory.models import Location, StockMovement, VariantStock


class Command(BaseCommand):
    help = 'Qoldiq keshini (joy bo‘yicha va umumiy) ombor jurnalidan qayta hisoblaydi'

    def add_arguments(self, parser):
        parser.add_argument(
            '--fix',
            action='store_true',
            help='Farq topilsa, keshni jurnaldagi qiymatga tenglashtiradi',
        )

    def handle(self, *args, **options):
        by_location = {
            (row['variant_id'], row['location_id']): row['total'] or 0
            for row in StockMovement.objects.values('variant_id', 'location_id')
            .annotate(total=Sum('quantity'))
            .order_by()
        }

        totals: dict[int, int] = {}

        for (variant_id, _location_id), quantity in by_location.items():
            totals[variant_id] = totals.get(variant_id, 0) + quantity

        location_names = dict(Location.objects.values_list('pk', 'name'))

        problems = self._check(by_location, totals, location_names)

        if not problems:
            self.stdout.write(self.style.SUCCESS('Farq yo‘q: kesh jurnalga mos.'))
            return

        if not options['fix']:
            self.stdout.write(
                self.style.WARNING(
                    f'{len(problems)} ta farq topildi. Tuzatish uchun --fix qo‘shing.'
                )
            )
            return

        self._fix(by_location, totals)

        self.stdout.write(self.style.SUCCESS(f'{len(problems)} ta qoldiq tuzatildi.'))

    def _check(self, by_location, totals, location_names) -> list[str]:
        problems = []

        for stock in VariantStock.objects.select_related('variant__product').order_by('id'):
            expected = by_location.get((stock.variant_id, stock.location_id), 0)

            if stock.quantity != expected:
                problems.append(
                    f'{stock.variant.sku} — {location_names.get(stock.location_id, "?")}: '
                    f'keshda {stock.quantity}, jurnalda {expected}'
                )

        # Jurnalda bor, lekin keshda umuman yo'q qatorlar
        known = set(
            VariantStock.objects.values_list('variant_id', 'location_id')
        )

        for key, quantity in by_location.items():
            if key not in known and quantity:
                problems.append(f'variant {key[0]}, joy {key[1]}: keshda qator yo‘q')

        for variant in Variant.objects.select_related('product').order_by('id'):
            expected = totals.get(variant.pk, 0)

            if variant.stock_quantity != expected:
                problems.append(
                    f'{variant.sku} — umumiy: keshda {variant.stock_quantity}, '
                    f'jurnalda {expected}'
                )

        for line in problems:
            self.stdout.write(line)

        return problems

    def _fix(self, by_location, totals) -> None:
        with transaction.atomic():
            for (variant_id, location_id), quantity in by_location.items():
                VariantStock.objects.update_or_create(
                    variant_id=variant_id,
                    location_id=location_id,
                    defaults={'quantity': quantity},
                )

            # Jurnalda qolmagan qatorlar nolga tushadi. Tekshiruv aynan
            # «variant + joy» juftligi bo'yicha: variant ombordan zalga
            # to'liq chiqarilgan bo'lsa, ombordagi eski qator qolib ketardi
            stale = [
                row.pk
                for row in VariantStock.objects.all()
                if (row.variant_id, row.location_id) not in by_location
            ]

            VariantStock.objects.filter(pk__in=stale).update(quantity=0)

            for variant in Variant.objects.order_by('id'):
                expected = totals.get(variant.pk, 0)

                if variant.stock_quantity != expected:
                    variant.stock_quantity = expected
                    variant.save(update_fields=['stock_quantity', 'updated_at'])
