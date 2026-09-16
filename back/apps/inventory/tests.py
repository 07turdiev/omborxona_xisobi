"""Ombor testlari: o'rtacha tannarx, inventarizatsiya va qoldiq keshi."""

from decimal import Decimal
from io import StringIO

from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.test import TestCase

from apps.catalog.models import Variant
from apps.core.factories import (
    api_client,
    create_admin,
    create_cashier,
    create_product,
    receive_stock,
)
from apps.inventory.models import MovementReason, StockMovement
from apps.inventory.services import create_write_off, moving_average, record_movement


class MovingAverageTests(TestCase):

    def setUp(self):
        self.product = create_product(sizes=('S', 'M', 'L'), colors=('qora', 'oq'))
        self.variants = list(self.product.variants.all())

    def test_first_purchase_sets_average_cost(self):
        """Har variantdan 5 dona, 150 000 dan: jami 30, o'rtacha 150 000."""
        for variant in self.variants:
            receive_stock(variant, 5, '150000')

        total = sum(
            Variant.objects.get(pk=variant.pk).stock_quantity for variant in self.variants
        )

        self.assertEqual(total, 30)

        for variant in self.variants:
            fresh = Variant.objects.get(pk=variant.pk)
            self.assertEqual(fresh.stock_quantity, 5)
            self.assertEqual(fresh.average_cost, Decimal('150000.00'))

    def test_second_purchase_recalculates_average(self):
        """5×150 000 va 5×170 000 → o'rtacha 160 000."""
        variant = self.variants[0]

        receive_stock(variant, 5, '150000')
        receive_stock(variant, 5, '170000')

        fresh = Variant.objects.get(pk=variant.pk)

        self.assertEqual(fresh.stock_quantity, 10)
        self.assertEqual(fresh.average_cost, Decimal('160000.00'))

    def test_average_formula_rounds_to_two_places(self):
        # (3×100 + 4×175) / 7 = 142.857… → 142.86
        self.assertEqual(
            moving_average(3, Decimal('100'), 4, Decimal('175')), Decimal('142.86')
        )

    def test_average_uses_new_cost_when_stock_is_empty(self):
        self.assertEqual(
            moving_average(0, Decimal('999'), 5, Decimal('120')), Decimal('120.00')
        )


class MovementGuardTests(TestCase):

    def setUp(self):
        self.variant = create_product().variants.get()

    def test_movement_cannot_go_below_zero(self):
        receive_stock(self.variant, 2, '1000')

        with self.assertRaises(ValidationError):
            record_movement(
                variant=self.variant, quantity=-3, reason=MovementReason.SALE
            )

        self.assertEqual(Variant.objects.get(pk=self.variant.pk).stock_quantity, 2)

    def test_movement_cannot_be_updated_or_deleted(self):
        receive_stock(self.variant, 1, '1000')
        movement = StockMovement.objects.first()

        with self.assertRaises(ValueError):
            movement.quantity = 5
            movement.save()

        with self.assertRaises(ValueError):
            movement.delete()


class StockCountTests(TestCase):

    def setUp(self):
        self.admin = create_admin()
        self.client_admin = api_client(self.admin)
        self.variant = create_product().variants.get()
        receive_stock(self.variant, 10, '50000', user=self.admin)

    def test_shortage_writes_adjustment_movement(self):
        """Sanoqda 10 o'rniga 8 topildi: 2 dona kamomad."""
        created = self.client_admin.post(
            '/api/stock-counts/',
            {
                'date': '2026-06-15',
                'lines': [{'variant': self.variant.pk, 'counted_quantity': 8}],
            },
            format='json',
        )
        self.assertEqual(created.status_code, 201, created.content)

        count_id = created.json()['id']
        confirmed = self.client_admin.post(f'/api/stock-counts/{count_id}/confirm/')

        self.assertEqual(confirmed.status_code, 200, confirmed.content)

        body = confirmed.json()
        self.assertEqual(body['status'], 'confirmed')
        self.assertEqual(body['lines'][0]['expected_quantity'], 10)
        self.assertEqual(body['lines'][0]['difference'], -2)

        self.assertEqual(Variant.objects.get(pk=self.variant.pk).stock_quantity, 8)

        movement = StockMovement.objects.filter(
            reason=MovementReason.COUNT_ADJUSTMENT
        ).get()
        self.assertEqual(movement.quantity, -2)
        self.assertEqual(movement.unit_cost, Decimal('50000.00'))

    def test_confirmed_count_cannot_be_changed(self):
        created = self.client_admin.post(
            '/api/stock-counts/',
            {'date': '2026-06-15', 'lines': [{'variant': self.variant.pk, 'counted_quantity': 9}]},
            format='json',
        )
        count_id = created.json()['id']
        self.client_admin.post(f'/api/stock-counts/{count_id}/confirm/')

        response = self.client_admin.patch(
            f'/api/stock-counts/{count_id}/', {'note': 'yangi izoh'}, format='json'
        )

        self.assertEqual(response.status_code, 400)

    def test_cashier_cannot_open_stock_count(self):
        response = api_client(create_cashier()).get('/api/stock-counts/')

        self.assertEqual(response.status_code, 403)


class WriteOffTests(TestCase):

    def setUp(self):
        self.admin = create_admin()
        self.variant = create_product().variants.get()
        receive_stock(self.variant, 4, '60000', user=self.admin)

    def test_write_off_reduces_stock(self):
        create_write_off(
            variant=self.variant, quantity=1, reason='Buzilgan', user=self.admin
        )

        self.assertEqual(Variant.objects.get(pk=self.variant.pk).stock_quantity, 3)

        movement = StockMovement.objects.filter(reason=MovementReason.WRITE_OFF).get()
        self.assertEqual(movement.quantity, -1)
        self.assertEqual(movement.unit_cost, Decimal('60000.00'))


class RecomputeCommandTests(TestCase):

    def setUp(self):
        self.variant = create_product().variants.get()
        receive_stock(self.variant, 7, '10000')

    def test_no_mismatch_after_normal_work(self):
        output = StringIO()
        call_command('recompute_stock', stdout=output)

        self.assertIn('Farq yo‘q', output.getvalue())

    def test_fix_restores_cache_from_ledger(self):
        # Keshni ataylab buzamiz — jurnal haqiqat manbai bo'lib qoladi
        Variant.objects.filter(pk=self.variant.pk).update(stock_quantity=999)

        output = StringIO()
        call_command('recompute_stock', '--fix', stdout=output)

        self.assertIn('tuzatildi', output.getvalue())
        self.assertEqual(Variant.objects.get(pk=self.variant.pk).stock_quantity, 7)
