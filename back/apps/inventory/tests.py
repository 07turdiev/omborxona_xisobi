"""Ombor testlari: o'rtacha tannarx, inventarizatsiya va qoldiq keshi."""

from decimal import Decimal
from io import StringIO

from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from apps.catalog.models import Variant
from apps.core.factories import (
    api_client,
    create_admin,
    create_cashier,
    create_product,
    receive_stock,
)
from apps.inventory.models import (
    Location,
    MovementReason,
    StockCount,
    StockCountLine,
    StockMovement,
    VariantStock,
)
from apps.inventory.services import (
    confirm_stock_count,
    create_transfer,
    create_write_off,
    moving_average,
    record_movement,
)
from apps.sales.services import create_sale


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
                variant=self.variant,
                location=Location.shop(),
                quantity=-3,
                reason=MovementReason.SALE,
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


class MovementDocumentTests(TestCase):
    """Jurnal yozuvida hujjat raqami — mahsulot sahifasidagi tarix havolalari uchun."""

    def setUp(self):
        self.admin = create_admin()
        self.variant = create_product(sizes=('M',), colors=('qora',)).variants.get()

    def movements(self):
        response = api_client(self.admin).get(f'/api/movements/?variant={self.variant.pk}')

        self.assertEqual(response.status_code, 200, response.content)

        return response.json()['results']

    def test_purchase_movement_carries_document_number(self):
        # Zalga ko'chirmaymiz: jurnalda faqat kirim yozuvi qolsin
        purchase = receive_stock(
            self.variant, 3, '100000', user=self.admin, location=Location.warehouse()
        )

        [movement] = self.movements()

        self.assertEqual(movement['document_type'], 'purchase')
        self.assertEqual(movement['document_id'], purchase.pk)
        self.assertEqual(movement['document_number'], purchase.number)

    def test_write_off_has_no_number(self):
        receive_stock(self.variant, 3, '100000', user=self.admin)
        create_write_off(variant=self.variant, quantity=1, reason='Yirtilgan', user=self.admin)

        write_off = next(item for item in self.movements() if item['document_type'] == 'writeoff')

        self.assertIsNone(write_off['document_number'])

    def test_cashier_cannot_read_movements(self):
        response = api_client(create_cashier()).get('/api/movements/')

        self.assertEqual(response.status_code, 403)


class LocationStockTests(TestCase):
    """Ombor va zal: qoldiq har joyda alohida yuritiladi.

    Do'konga tovar avval omborga keladi, sotiladigani zalga chiqariladi.
    Xaridor so'ragan narsa zalda tugagan bo'lsa, ombordan olib chiqiladi.
    """

    def setUp(self):
        self.admin = create_admin()
        self.cashier = create_cashier()
        self.variant = create_product(price='250000').variants.get()

        self.warehouse = Location.warehouse()
        self.shop = Location.shop()

    def stock(self, location) -> int:
        row = VariantStock.objects.filter(variant=self.variant, location=location).first()

        return row.quantity if row else 0

    def test_purchase_lands_in_the_warehouse(self):
        receive_stock(self.variant, 5, '150000', location=self.warehouse)

        self.assertEqual(self.stock(self.warehouse), 5)
        self.assertEqual(self.stock(self.shop), 0)
        self.assertEqual(Variant.objects.get(pk=self.variant.pk).stock_quantity, 5)

    def test_transfer_moves_stock_and_keeps_the_total(self):
        receive_stock(self.variant, 5, '150000', location=self.warehouse)

        transfer = create_transfer(
            source=self.warehouse,
            target=self.shop,
            lines=[{'variant': self.variant, 'quantity': 3}],
            user=self.admin,
        )

        self.assertTrue(transfer.number.startswith('KCH-'))
        self.assertEqual(self.stock(self.warehouse), 2)
        self.assertEqual(self.stock(self.shop), 3)

        # Umumiy qoldiq o'zgarmaydi — tovar do'kondan chiqmadi
        self.assertEqual(Variant.objects.get(pk=self.variant.pk).stock_quantity, 5)

        reasons = set(
            StockMovement.objects.filter(document_type='transfer').values_list(
                'reason', flat=True
            )
        )

        self.assertEqual(
            reasons, {MovementReason.TRANSFER_OUT, MovementReason.TRANSFER_IN}
        )

    def test_shop_cannot_sell_what_is_only_in_the_warehouse(self):
        receive_stock(self.variant, 5, '150000', location=self.warehouse)

        with self.assertRaises(ValidationError):
            create_sale(
                user=self.cashier,
                lines=[{'variant': self.variant, 'quantity': 1}],
                cash_amount=Decimal('250000'),
            )

        self.assertEqual(self.stock(self.warehouse), 5)

    def test_sale_takes_from_the_shop(self):
        receive_stock(self.variant, 5, '150000')  # standart: zalga chiqariladi

        create_sale(
            user=self.cashier,
            lines=[{'variant': self.variant, 'quantity': 2}],
            cash_amount=Decimal('500000'),
        )

        self.assertEqual(self.stock(self.shop), 3)
        self.assertEqual(self.stock(self.warehouse), 0)

    def test_transfer_cannot_exceed_the_source(self):
        receive_stock(self.variant, 2, '150000', location=self.warehouse)

        with self.assertRaises(ValidationError):
            create_transfer(
                source=self.warehouse,
                target=self.shop,
                lines=[{'variant': self.variant, 'quantity': 3}],
                user=self.admin,
            )

        self.assertEqual(self.stock(self.warehouse), 2)
        self.assertEqual(self.stock(self.shop), 0)

    def test_transfer_to_the_same_place_is_rejected(self):
        with self.assertRaises(ValidationError):
            create_transfer(
                source=self.shop,
                target=self.shop,
                lines=[{'variant': self.variant, 'quantity': 1}],
                user=self.admin,
            )

    def test_write_off_takes_from_its_location(self):
        receive_stock(self.variant, 4, '150000', location=self.warehouse)

        create_write_off(
            variant=self.variant,
            quantity=1,
            reason='Yirtilgan',
            location=self.warehouse,
            user=self.admin,
        )

        self.assertEqual(self.stock(self.warehouse), 3)

    def test_count_compares_only_its_own_location(self):
        """Zal sanalganda ombordagi tovar farqqa tushmaydi."""
        receive_stock(self.variant, 5, '150000', location=self.warehouse)

        create_transfer(
            source=self.warehouse,
            target=self.shop,
            lines=[{'variant': self.variant, 'quantity': 2}],
            user=self.admin,
        )

        count = StockCount.objects.create(
            number='INV-2026-000900',
            date=timezone.localdate(),
            location=self.shop,
            created_by=self.admin,
        )

        # Zalda ikkita bor edi, sanoqda ikkitasi topildi — farq yo'q
        StockCountLine.objects.create(
            stock_count=count, variant=self.variant, counted_quantity=2
        )

        confirm_stock_count(count, user=self.admin)

        line = count.lines.get()

        self.assertEqual(line.expected_quantity, 2)
        self.assertEqual(line.difference, 0)
        self.assertEqual(self.stock(self.warehouse), 3)


class TransferApiTests(TestCase):
    """Ko'chirish API si: kassa ham, ombor ekrani ham shu yerga murojaat qiladi."""

    def setUp(self):
        self.admin = create_admin()
        self.variant = create_product().variants.get()
        self.warehouse = Location.warehouse()
        self.shop = Location.shop()

        receive_stock(self.variant, 6, '100000', location=self.warehouse)

    def payload(self, quantity=2):
        return {
            'source': self.warehouse.pk,
            'target': self.shop.pk,
            'lines': [{'variant': self.variant.pk, 'quantity': quantity}],
        }

    def test_admin_moves_stock_to_the_shop(self):
        response = api_client(self.admin).post(
            '/api/transfers/', self.payload(), format='json'
        )

        self.assertEqual(response.status_code, 201, response.content)

        body = response.json()

        self.assertTrue(body['number'].startswith('KCH-'))
        self.assertEqual(body['source_name'], self.warehouse.name)
        self.assertEqual(body['target_name'], self.shop.name)

        self.assertEqual(
            VariantStock.objects.get(variant=self.variant, location=self.shop).quantity, 2
        )

    def test_cashier_can_bring_goods_from_the_warehouse(self):
        """Zalda tugagan tovarni kassir bir bosishda olib chiqadi."""
        response = api_client(create_cashier()).post(
            '/api/transfers/', self.payload(1), format='json'
        )

        self.assertEqual(response.status_code, 201, response.content)
        self.assertEqual(
            VariantStock.objects.get(variant=self.variant, location=self.shop).quantity, 1
        )

    def test_missing_stock_is_reported(self):
        response = api_client(self.admin).post(
            '/api/transfers/', self.payload(99), format='json'
        )

        self.assertEqual(response.status_code, 400, response.content)
        self.assertIn('yetarli emas', ' '.join(response.json()['detail']))

    def test_locations_are_listed(self):
        response = api_client(self.admin).get('/api/locations/')

        self.assertEqual(response.status_code, 200)

        kinds = {item['kind'] for item in response.json()}

        self.assertEqual(kinds, {'warehouse', 'shop'})
