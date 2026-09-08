"""Qoldiq testlari: append-only jurnal, kesh, partiya, ko'chirish."""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.test import TestCase
from django.utils import timezone

from apps.catalog.models import Category, Product, Variant
from apps.core.tenancy import tenant_context
from apps.stock import services
from apps.stock.enums import MovementReason
from apps.stock.models import Batch, StockBalance, StockMovement
from apps.tenants.models import Tenant
from apps.warehouse.models import Warehouse

D = Decimal


class StockTestBase(TestCase):
    """Umumiy tayyorgarlik: tashkilot, ombor, mahsulot."""

    @classmethod
    def setUpTestData(cls):
        cls.tenant = Tenant.objects.create(name='Do\'kon', slug='stock-test')

    def setUp(self):
        self.ctx = tenant_context(self.tenant.id)
        self.ctx.__enter__()

        self.main = Warehouse.objects.create(
            tenant=self.tenant, code='MAIN', name='Asosiy',
            purpose=Warehouse.Purpose.MAIN,
        )
        self.shop = Warehouse.objects.create(
            tenant=self.tenant, code='SHOP', name='Do\'kon',
            purpose=Warehouse.Purpose.RETAIL,
        )
        self.transit = Warehouse.objects.create(
            tenant=self.tenant, code='TR', name='Yo\'lda',
            purpose=Warehouse.Purpose.TRANSIT,
        )

        category = Category.objects.create(
            tenant=self.tenant, name='Sement', default_unit='kg'
        )
        product = Product.objects.create(
            tenant=self.tenant, category=category, name='Portlandsement', base_unit='kg'
        )
        self.variant = Variant.objects.create(
            tenant=self.tenant, product=product, sku='CEM-1'
        )

    def tearDown(self):
        self.ctx.__exit__(None, None, None)

    def add(self, quantity, warehouse=None, **kwargs):
        return services.record_movement(
            variant=self.variant,
            warehouse=warehouse or self.main,
            quantity=D(quantity),
            reason=kwargs.pop('reason', MovementReason.PURCHASE),
            **kwargs,
        )

    def balance_of(self, warehouse=None, batch=None):
        return StockBalance.objects.filter(
            variant=self.variant, warehouse=warehouse or self.main, batch=batch
        ).first()


class AppendOnlyTests(StockTestBase):
    """Jurnalni o'zgartirib bo'lmasligi — 3-arxitektura qarori."""

    def test_movement_cannot_be_updated_via_orm(self):
        movement = self.add('10')
        movement.quantity = D('999')

        with self.assertRaises(ValidationError):
            movement.save()

    def test_movement_cannot_be_deleted_via_orm(self):
        movement = self.add('10')

        with self.assertRaises(ValidationError):
            movement.delete()

    def test_database_trigger_blocks_queryset_update(self):
        """ORM ni chetlab o'tgan `update()` ham to'xtatiladi.

        Model darajasidagi himoya faqat `save()` ni ushlaydi;
        `queryset.update()` uni umuman chaqirmaydi. Shuning uchun
        asosiy kafolat — baza triggeri.
        """
        self.add('10')

        with self.assertRaises(Exception), transaction.atomic():
            StockMovement.objects.all().update(quantity=D('999'))

    def test_database_trigger_blocks_queryset_delete(self):
        self.add('10')

        with self.assertRaises(Exception), transaction.atomic():
            StockMovement.objects.all().delete()

    def test_zero_quantity_rejected(self):
        with self.assertRaises(ValidationError):
            self.add('0')


class BalanceCacheTests(StockTestBase):
    """Kesh jurnaldan hosila ekanini qotiradi."""

    def test_balance_follows_journal(self):
        self.add('100')
        self.add('-30', reason=MovementReason.SALE)
        self.add('50')

        self.assertEqual(self.balance_of().quantity, D('120'))

    def test_cache_matches_rebuild_from_journal(self):
        """Kesh haqiqat manbai emas: uni jurnaldan tiklash mumkin."""
        self.add('100')
        self.add('-40', reason=MovementReason.SALE)

        cached = self.balance_of().quantity

        # Keshni ataylab buzamiz
        StockBalance.objects.filter(pk=self.balance_of().pk).update(quantity=D('1'))

        rebuilt = services.rebuild_balance(self.variant, self.main)

        self.assertEqual(rebuilt.quantity, cached)
        self.assertEqual(rebuilt.quantity, D('60'))

    def test_balance_is_per_warehouse(self):
        self.add('100', warehouse=self.main)
        self.add('20', warehouse=self.shop)

        self.assertEqual(self.balance_of(self.main).quantity, D('100'))
        self.assertEqual(self.balance_of(self.shop).quantity, D('20'))

    def test_negative_balance_rejected_by_default(self):
        self.add('10')

        with self.assertRaises(ValidationError):
            self.add('-20', reason=MovementReason.SALE)

        self.assertEqual(self.balance_of().quantity, D('10'))

    def test_direction_must_match_reason(self):
        """Kirim sababi bilan manfiy miqdor yozib bo'lmaydi."""
        with self.assertRaises(ValidationError):
            self.add('-10', reason=MovementReason.PURCHASE)

        self.add('10')

        with self.assertRaises(ValidationError):
            self.add('5', reason=MovementReason.SALE)

    def test_decimal_precision_preserved(self):
        """6-qaror: miqdor Decimal(18,3), float emas."""
        self.add('0.125')
        self.add('0.250')

        balance = self.balance_of()
        self.assertIsInstance(balance.quantity, Decimal)
        self.assertEqual(balance.quantity, D('0.375'))

    def test_meta_numbers_stored_as_strings(self):
        """Audit jurnali yaxlitlash xatosi manbai bo'lmasligi kerak.

        InvenTree bu yerda `float` ishlatadi (stock/models.py:2373).
        """
        movement = self.add('10', meta={'expected': D('0.1')})

        self.assertEqual(movement.meta['expected'], '0.1')
        self.assertIsInstance(movement.meta['expected'], str)


class BatchTests(StockTestBase):
    """Partiya — qoldiq o'lchovi, yaroqlilik muddati bilan."""

    def make_batch(self, code, days=None):
        expiry = timezone.localdate() + timedelta(days=days) if days is not None else None
        return Batch.objects.create(
            tenant=self.tenant, variant=self.variant, code=code, expiry_date=expiry
        )

    def test_balance_is_tracked_per_batch(self):
        first = self.make_batch('A-001')
        second = self.make_batch('A-002')

        self.add('100', batch=first)
        self.add('60', batch=second)

        self.assertEqual(self.balance_of(batch=first).quantity, D('100'))
        self.assertEqual(self.balance_of(batch=second).quantity, D('60'))

    def test_batchless_stock_uses_single_row(self):
        """`batch = NULL` bo'lgan qatorlar dublikat bo'lmasligi kerak.

        PostgreSQL standart holda NULL larni bir-biridan farqli deb
        hisoblaydi, ya'ni unikal cheklov ularni ushlamaydi. Shuning
        uchun cheklovda `nulls_distinct=False`.
        """
        self.add('10')
        self.add('15')

        rows = StockBalance.objects.filter(
            variant=self.variant, warehouse=self.main, batch__isnull=True
        )

        self.assertEqual(rows.count(), 1)
        self.assertEqual(rows.first().quantity, D('25'))

    def test_expired_batch_is_detected(self):
        expired = self.make_batch('OLD', days=-1)
        fresh = self.make_batch('NEW', days=90)

        self.assertTrue(expired.is_expired)
        self.assertFalse(fresh.is_expired)

    def test_stale_batch_is_detected(self):
        """Muddati yaqinlashgan partiya ogohlantirish uchun ajratiladi."""
        soon = self.make_batch('SOON', days=10)
        later = self.make_batch('LATER', days=200)

        self.assertTrue(soon.is_stale(threshold_days=30))
        self.assertFalse(later.is_stale(threshold_days=30))

    def test_expired_batch_is_not_sellable(self):
        expired = self.make_batch('OLD', days=-1)
        self.add('100', batch=expired)

        self.assertFalse(self.balance_of(batch=expired).is_sellable)

    def test_batch_from_other_variant_rejected(self):
        other_product = Product.objects.create(
            tenant=self.tenant, category=self.variant.product.category, name='Gips'
        )
        other = Variant.objects.create(
            tenant=self.tenant, product=other_product, sku='GYP-1'
        )
        foreign = Batch.objects.create(
            tenant=self.tenant, variant=other, code='X-1'
        )

        with self.assertRaises(ValidationError):
            self.add('10', batch=foreign)


class SellabilityTests(StockTestBase):
    """"Bor" qoldiq va "sotish mumkin" qoldiq farqi."""

    def test_transit_stock_is_not_sellable(self):
        """Tranzitdagi tovar yo'lda — u sotuvga chiqmaydi (2-band)."""
        self.add('100', warehouse=self.transit, reason=MovementReason.TRANSFER_IN)

        self.assertFalse(self.balance_of(self.transit).is_sellable)
        self.assertEqual(self.balance_of(self.transit).quantity, D('100'))

    def test_reserved_quantity_reduces_available(self):
        """100 qop bor, 80 tasi band — sotuvchiga 20 ko'rinishi kerak."""
        self.add('100')
        services.reserve(self.variant, self.main, D('80'))

        balance = self.balance_of()

        self.assertEqual(balance.quantity, D('100'))
        self.assertEqual(balance.available_quantity, D('20'))

    def test_cannot_reserve_more_than_available(self):
        self.add('100')
        services.reserve(self.variant, self.main, D('80'))

        with self.assertRaises(ValidationError):
            services.reserve(self.variant, self.main, D('30'))

    def test_release_frees_reservation(self):
        self.add('100')
        services.reserve(self.variant, self.main, D('80'))
        services.release(self.variant, self.main, D('50'))

        self.assertEqual(self.balance_of().available_quantity, D('70'))

    def test_available_never_negative(self):
        """Ortiqcha band qilinganda manfiy son ko'rsatilmaydi."""
        self.add('100')
        services.reserve(self.variant, self.main, D('100'))
        self.add('-60', reason=MovementReason.SALE)

        balance = self.balance_of()

        self.assertEqual(balance.available_quantity, D('0'))
        self.assertTrue(balance.is_overallocated)


class TransferTests(StockTestBase):
    """Ikki bosqichli ko'chirish — promptdagi 6-band."""

    def test_transfer_out_moves_stock_to_transit(self):
        self.add('100')

        services.transfer_out(
            variant=self.variant, warehouse=self.main,
            transit_warehouse=self.transit, quantity=D('40'),
        )

        self.assertEqual(self.balance_of(self.main).quantity, D('60'))
        self.assertEqual(self.balance_of(self.transit).quantity, D('40'))

    def test_stock_is_not_lost_while_in_transit(self):
        """Yo'ldagi tovar qoldiqdan yo'qolmaydi, faqat sotuvga chiqmaydi."""
        self.add('100')
        services.transfer_out(
            variant=self.variant, warehouse=self.main,
            transit_warehouse=self.transit, quantity=D('40'),
        )

        total = sum(
            row.quantity
            for row in StockBalance.objects.filter(variant=self.variant)
        )

        self.assertEqual(total, D('100'))

    def test_full_receipt_completes_transfer(self):
        self.add('100')
        services.transfer_out(
            variant=self.variant, warehouse=self.main,
            transit_warehouse=self.transit, quantity=D('40'),
        )
        result = services.transfer_in(
            variant=self.variant, transit_warehouse=self.transit,
            warehouse=self.shop, quantity=D('40'),
        )

        self.assertNotIn('loss', result)
        self.assertEqual(self.balance_of(self.transit).quantity, D('0'))
        self.assertEqual(self.balance_of(self.shop).quantity, D('40'))

    def test_shortfall_is_recorded_not_swallowed(self):
        """Kamomad alohida yozuv sifatida ko'rinadi.

        InvenTree bu farqni jimgina yutib yuboradi:
        `transfer_quantity = min(self.quantity, self.item.quantity)`
        (order/models.py:4235).
        """
        self.add('100')
        services.transfer_out(
            variant=self.variant, warehouse=self.main,
            transit_warehouse=self.transit, quantity=D('40'),
        )
        result = services.transfer_in(
            variant=self.variant, transit_warehouse=self.transit,
            warehouse=self.shop, quantity=D('37'),
        )

        self.assertIn('loss', result)
        self.assertEqual(result['loss'].quantity, D('-3'))
        self.assertEqual(result['loss'].reason, MovementReason.TRANSIT_LOSS)
        self.assertEqual(result['loss'].meta['expected'], '40.000')
        self.assertEqual(result['loss'].meta['received'], '37')

        self.assertEqual(self.balance_of(self.transit).quantity, D('0'))
        self.assertEqual(self.balance_of(self.shop).quantity, D('37'))

    def test_cannot_receive_more_than_sent(self):
        self.add('100')
        services.transfer_out(
            variant=self.variant, warehouse=self.main,
            transit_warehouse=self.transit, quantity=D('40'),
        )

        with self.assertRaises(ValidationError):
            services.transfer_in(
                variant=self.variant, transit_warehouse=self.transit,
                warehouse=self.shop, quantity=D('50'),
            )

    def test_transit_loss_counts_as_loss(self):
        self.assertTrue(MovementReason.is_loss(MovementReason.TRANSIT_LOSS))
        self.assertFalse(MovementReason.is_loss(MovementReason.SALE))


class StocktakeTests(StockTestBase):
    """Inventarizatsiya — sanalgan va hisoblangan qoldiq farqi."""

    def test_shortage_recorded_as_correction(self):
        self.add('100')

        movement = services.stocktake(
            variant=self.variant, warehouse=self.main, counted_quantity=D('95')
        )

        self.assertEqual(movement.quantity, D('-5'))
        self.assertEqual(movement.reason, MovementReason.STOCKTAKE_CORRECTION)
        self.assertEqual(self.balance_of().quantity, D('95'))

    def test_surplus_recorded_as_correction(self):
        """Sanashda ortiqcha ham chiqishi mumkin."""
        self.add('100')

        movement = services.stocktake(
            variant=self.variant, warehouse=self.main, counted_quantity=D('103')
        )

        self.assertEqual(movement.quantity, D('3'))
        self.assertEqual(self.balance_of().quantity, D('103'))

    def test_no_movement_when_counts_match(self):
        self.add('100')

        self.assertIsNone(
            services.stocktake(
                variant=self.variant, warehouse=self.main, counted_quantity=D('100')
            )
        )

    def test_correction_keeps_previous_value_in_meta(self):
        """Farqning sababini keyin tekshirish mumkin bo'lishi kerak."""
        self.add('100')

        movement = services.stocktake(
            variant=self.variant, warehouse=self.main, counted_quantity=D('95')
        )

        self.assertEqual(movement.meta['expected'], '100.000')
        self.assertEqual(movement.meta['counted'], '95')

    def test_correction_is_a_loss_not_a_sale(self):
        """Foyda hisobotida yo'qotish sotuvdan alohida chiqishi kerak."""
        self.assertTrue(
            MovementReason.is_loss(MovementReason.STOCKTAKE_CORRECTION)
        )


class StockIsolationTests(TestCase):
    """Qoldiq ham RLS bilan himoyalangan."""

    @classmethod
    def setUpTestData(cls):
        cls.tenant_a = Tenant.objects.create(name='A', slug='stock-iso-a')
        cls.tenant_b = Tenant.objects.create(name='B', slug='stock-iso-b')

    def make_stock(self, tenant, quantity):
        with tenant_context(tenant.id):
            warehouse = Warehouse.objects.create(
                tenant=tenant, code='W', name='Ombor'
            )
            category = Category.objects.create(tenant=tenant, name='Tovar')
            product = Product.objects.create(
                tenant=tenant, category=category, name='Tovar'
            )
            variant = Variant.objects.create(
                tenant=tenant, product=product, sku='S-1'
            )

            services.record_movement(
                variant=variant, warehouse=warehouse,
                quantity=Decimal(quantity), reason=MovementReason.PURCHASE,
            )

    def test_balances_are_isolated(self):
        self.make_stock(self.tenant_a, '100')
        self.make_stock(self.tenant_b, '55')

        with tenant_context(self.tenant_a.id):
            self.assertEqual(
                [b.quantity for b in StockBalance.objects.all()], [Decimal('100.000')]
            )

        with tenant_context(self.tenant_b.id):
            self.assertEqual(
                [b.quantity for b in StockBalance.objects.all()], [Decimal('55.000')]
            )

    def test_movements_are_isolated(self):
        self.make_stock(self.tenant_a, '100')
        self.make_stock(self.tenant_b, '55')

        with tenant_context(self.tenant_a.id):
            self.assertEqual(StockMovement.objects.count(), 1)
