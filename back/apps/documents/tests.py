"""Hujjat testlari: tasdiqlash, bekor qilish, o'ram va foyda."""

from __future__ import annotations

from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase

from apps.catalog.models import Category, Product, ProductUnit, Variant
from apps.core.tenancy import tenant_context
from apps.documents import services as docs
from apps.documents.models import Document
from apps.partners.models import Partner
from apps.pricing.models import Currency
from apps.stock.models import StockBalance, StockMovement
from apps.tenants.models import Tenant
from apps.warehouse.models import Warehouse

D = Decimal


class DocumentTestBase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.tenant = Tenant.objects.create(
            name='Do\'kon', slug='doc-test', base_currency='UZS'
        )

    def setUp(self):
        self.ctx = tenant_context(self.tenant.id)
        self.ctx.__enter__()

        Currency.objects.create(
            tenant=self.tenant, code='UZS', name='So\'m', is_base=True
        )

        self.main = Warehouse.objects.create(
            tenant=self.tenant, code='MAIN', name='Asosiy'
        )
        self.transit = Warehouse.objects.create(
            tenant=self.tenant, code='TR', name='Yo\'lda',
            purpose=Warehouse.Purpose.TRANSIT,
        )

        self.supplier = Partner.objects.create(
            tenant=self.tenant, name='Bekabadsement', is_supplier=True
        )
        self.customer = Partner.objects.create(
            tenant=self.tenant, name='Qurilish MCHJ', is_customer=True
        )

        category = Category.objects.create(
            tenant=self.tenant, name='Sement', default_unit='kg'
        )
        product = Product.objects.create(
            tenant=self.tenant, category=category, name='Sement', base_unit='kg'
        )
        self.variant = Variant.objects.create(
            tenant=self.tenant, product=product, sku='CEM-1'
        )

        # 1 qop = 50 kg
        ProductUnit.objects.create(
            tenant=self.tenant, variant=self.variant,
            unit='qop', factor_to_base=D('50'),
        )

    def tearDown(self):
        self.ctx.__exit__(None, None, None)

    def make_doc(self, kind, warehouse=None, partner=None):
        return Document.objects.create(
            tenant=self.tenant,
            kind=kind,
            number=docs.next_number(self.tenant, kind),
            warehouse=warehouse or self.main,
            partner=partner,
        )

    def purchase(self, quantity, price, unit='', confirm=True):
        doc = self.make_doc(Document.Kind.PURCHASE, partner=self.supplier)
        docs.build_line(
            doc, variant=self.variant, quantity=D(quantity),
            unit_price=D(price), unit=unit,
        )
        docs.recalculate_totals(doc)

        return docs.confirm(doc) if confirm else doc

    def balance(self, warehouse=None):
        row = StockBalance.objects.filter(
            variant=self.variant, warehouse=warehouse or self.main
        ).first()

        return row.quantity if row else D('0')


class NumberingTests(DocumentTestBase):
    def test_number_format(self):
        number = docs.next_number(self.tenant, Document.Kind.PURCHASE)

        self.assertRegex(number, r'^KIR-\d{4}-000001$')

    def test_numbers_increment(self):
        first = self.make_doc(Document.Kind.PURCHASE)
        second = self.make_doc(Document.Kind.PURCHASE)

        self.assertEqual(int(second.number[-6:]), int(first.number[-6:]) + 1)

    def test_kinds_have_separate_sequences(self):
        self.make_doc(Document.Kind.PURCHASE)
        sale = self.make_doc(Document.Kind.SALE)

        self.assertTrue(sale.number.startswith('SOT-'))
        self.assertTrue(sale.number.endswith('000001'))


class PackUnitTests(DocumentTestBase):
    """«3 qop» kiritiladi, qoldiq kilogrammda yuritiladi."""

    def test_quantity_converted_to_base_unit(self):
        doc = self.make_doc(Document.Kind.PURCHASE)
        line = docs.build_line(
            doc, variant=self.variant, quantity=D('3'),
            unit_price=D('45000'), unit='qop',
        )

        self.assertEqual(line.factor, D('50'))
        self.assertEqual(line.quantity, D('3'))
        self.assertEqual(line.quantity_base, D('150'))

    def test_unit_price_converted_to_base(self):
        """Qop narxi 45 000 bo'lsa, kilogramm narxi 900."""
        doc = self.make_doc(Document.Kind.PURCHASE)
        line = docs.build_line(
            doc, variant=self.variant, quantity=D('3'),
            unit_price=D('45000'), unit='qop',
        )

        self.assertEqual(line.unit_price_base, D('900'))

    def test_line_total_uses_entered_unit(self):
        doc = self.make_doc(Document.Kind.PURCHASE)
        line = docs.build_line(
            doc, variant=self.variant, quantity=D('3'),
            unit_price=D('45000'), unit='qop',
        )

        self.assertEqual(line.line_total, D('135000'))

    def test_unknown_pack_unit_rejected(self):
        doc = self.make_doc(Document.Kind.PURCHASE)

        with self.assertRaises(ValidationError):
            docs.build_line(
                doc, variant=self.variant, quantity=D('1'),
                unit_price=D('1'), unit='vagon',
            )

    def test_factor_is_snapshot_not_reference(self):
        """Koeffitsient keyin o'zgarsa, eski hujjat qayta hisoblanmaydi.

        Valyuta kursi bilan bir xil mantiq: tasdiqlangan hujjat
        o'z-o'zidan o'zgarmasligi kerak.
        """
        doc = self.make_doc(Document.Kind.PURCHASE)
        line = docs.build_line(
            doc, variant=self.variant, quantity=D('3'),
            unit_price=D('45000'), unit='qop',
        )

        pack = ProductUnit.objects.get(variant=self.variant, unit='qop')
        pack.factor_to_base = D('40')
        pack.save()

        line.refresh_from_db()

        self.assertEqual(line.factor, D('50'))
        self.assertEqual(line.quantity_base, D('150'))

    def test_discount_applied(self):
        doc = self.make_doc(Document.Kind.PURCHASE)
        line = docs.build_line(
            doc, variant=self.variant, quantity=D('10'),
            unit_price=D('1000'), discount_percent=D('15'),
        )

        self.assertEqual(line.line_total, D('8500'))


class ConfirmTests(DocumentTestBase):
    def test_draft_does_not_touch_stock(self):
        self.purchase('10', '900', confirm=False)

        self.assertEqual(self.balance(), D('0'))
        self.assertEqual(StockMovement.objects.count(), 0)

    def test_confirm_posts_to_journal(self):
        doc = self.purchase('3', '45000', unit='qop')

        self.assertEqual(doc.status, Document.Status.CONFIRMED)
        self.assertEqual(self.balance(), D('150'))
        self.assertEqual(StockMovement.objects.count(), 1)

    def test_movement_links_back_to_document(self):
        doc = self.purchase('10', '900')
        movement = StockMovement.objects.get()

        self.assertEqual(movement.document_type, 'document')
        self.assertEqual(movement.document_id, doc.pk)

    def test_multiline_document_creates_movement_per_line(self):
        """Bitta hujjat, bir necha pozitsiya — real yetkazma shunday."""
        other_product = Product.objects.create(
            tenant=self.tenant, category=self.variant.product.category,
            name='Gips', base_unit='kg',
        )
        other = Variant.objects.create(
            tenant=self.tenant, product=other_product, sku='GYP-1'
        )

        doc = self.make_doc(Document.Kind.PURCHASE, partner=self.supplier)
        docs.build_line(doc, variant=self.variant, quantity=D('100'), unit_price=D('900'))
        docs.build_line(doc, variant=other, quantity=D('50'), unit_price=D('930'))
        docs.recalculate_totals(doc)
        docs.confirm(doc)

        self.assertEqual(StockMovement.objects.count(), 2)
        self.assertEqual(doc.total_amount, D('136500'))

    def test_cannot_confirm_twice(self):
        doc = self.purchase('10', '900')

        with self.assertRaises(ValidationError):
            docs.confirm(doc)

    def test_cannot_confirm_empty_document(self):
        doc = self.make_doc(Document.Kind.PURCHASE)

        with self.assertRaises(ValidationError):
            docs.confirm(doc)

    def test_sale_from_transit_warehouse_rejected(self):
        """Tranzitdagi tovar sotuvga chiqmaydi (2-band)."""
        doc = self.make_doc(Document.Kind.SALE, warehouse=self.transit)
        docs.build_line(doc, variant=self.variant, quantity=D('1'), unit_price=D('1'))

        with self.assertRaises(ValidationError):
            docs.confirm(doc)

    def test_sale_without_stock_rejected(self):
        doc = self.make_doc(Document.Kind.SALE, partner=self.customer)
        docs.build_line(doc, variant=self.variant, quantity=D('10'), unit_price=D('1200'))

        with self.assertRaises(ValidationError):
            docs.confirm(doc)


class SaleProfitTests(DocumentTestBase):
    """Sotuv foydasi FIFO tannarxidan hisoblanadi."""

    def test_profit_uses_fifo_cost(self):
        self.purchase('100', '900')
        self.purchase('100', '1100')

        doc = self.make_doc(Document.Kind.SALE, partner=self.customer)
        docs.build_line(doc, variant=self.variant, quantity=D('150'), unit_price=D('1500'))
        docs.recalculate_totals(doc)
        docs.confirm(doc)

        # tannarx: 100×900 + 50×1100 = 145 000
        # summa:   150×1500 = 225 000
        self.assertEqual(doc.total_cost, D('145000'))
        self.assertEqual(doc.total_amount, D('225000'))
        self.assertEqual(doc.profit, D('80000'))

    def test_profit_is_zero_for_purchase(self):
        doc = self.purchase('100', '900')

        self.assertEqual(doc.profit, D('0'))

    def test_draft_sale_has_no_profit(self):
        """Qoralamada tannarx hisoblanmagan — butun summa foyda emas."""
        self.purchase('100', '900')

        doc = self.make_doc(Document.Kind.SALE, partner=self.customer)
        docs.build_line(doc, variant=self.variant, quantity=D('10'), unit_price=D('1500'))
        docs.recalculate_totals(doc)

        self.assertEqual(doc.total_amount, D('15000'))
        self.assertEqual(doc.profit, D('0'))

    def test_line_cost_recorded_per_line(self):
        self.purchase('100', '900')

        doc = self.make_doc(Document.Kind.SALE, partner=self.customer)
        line = docs.build_line(
            doc, variant=self.variant, quantity=D('10'), unit_price=D('1500')
        )
        docs.confirm(doc)
        line.refresh_from_db()

        self.assertEqual(line.line_cost, D('9000'))

    def test_sale_in_pack_units_costs_correctly(self):
        """«2 qop sotildi» — tannarx kilogramm bo'yicha yechiladi."""
        self.purchase('100', '900')  # 100 kg @ 900

        doc = self.make_doc(Document.Kind.SALE, partner=self.customer)
        docs.build_line(
            doc, variant=self.variant, quantity=D('2'),
            unit_price=D('60000'), unit='qop',
        )
        docs.recalculate_totals(doc)
        docs.confirm(doc)

        # 2 qop = 100 kg, tannarx 100 × 900 = 90 000
        self.assertEqual(doc.total_cost, D('90000'))
        self.assertEqual(doc.total_amount, D('120000'))
        self.assertEqual(self.balance(), D('0'))


class BatchAllocationTests(DocumentTestBase):
    """Partiya ko'rsatilmagan sotuvda FEFO — muddati yaqini birinchi."""

    def make_batch(self, code, days=None):
        from datetime import timedelta

        from django.utils import timezone as tz
        from apps.stock.models import Batch

        expiry = tz.localdate() + timedelta(days=days) if days is not None else None

        return Batch.objects.create(
            tenant=self.tenant, variant=self.variant, code=code, expiry_date=expiry
        )

    def buy_batch(self, batch, quantity, price):
        doc = self.make_doc(Document.Kind.PURCHASE, partner=self.supplier)
        docs.build_line(
            doc, variant=self.variant, quantity=D(quantity),
            unit_price=D(price), batch=batch,
        )
        docs.recalculate_totals(doc)

        return docs.confirm(doc)

    def sell(self, quantity, price='1500'):
        doc = self.make_doc(Document.Kind.SALE, partner=self.customer)
        docs.build_line(
            doc, variant=self.variant, quantity=D(quantity), unit_price=D(price)
        )
        docs.recalculate_totals(doc)

        return docs.confirm(doc)

    def test_nearest_expiry_sold_first(self):
        """Muddati yaqin partiya birinchi chiqadi, aks holda u yaroqsiz bo'ladi."""
        late = self.make_batch('LATE', days=200)
        soon = self.make_batch('SOON', days=10)

        self.buy_batch(late, '100', '900')
        self.buy_batch(soon, '100', '1000')

        self.sell('60')

        balances = {
            b.batch.code: b.quantity
            for b in StockBalance.objects.select_related('batch').filter(
                variant=self.variant, warehouse=self.main
            )
        }

        self.assertEqual(balances['SOON'], D('40'))
        self.assertEqual(balances['LATE'], D('100'))

    def test_sale_spans_batches_when_needed(self):
        late = self.make_batch('LATE', days=200)
        soon = self.make_batch('SOON', days=10)

        self.buy_batch(late, '100', '900')
        self.buy_batch(soon, '100', '1000')

        doc = self.sell('150')

        # SOON tugadi (100), LATE dan 50 olindi.
        # Tannarx: 100×1000 + 50×900 = 145 000
        self.assertEqual(doc.total_cost, D('145000'))
        self.assertEqual(
            StockMovement.objects.filter(document_id=doc.pk).count(), 2
        )

    def test_batchless_stock_sold_last(self):
        """Muddati yo'q partiyalar oxirida turadi."""
        soon = self.make_batch('SOON', days=10)

        doc = self.make_doc(Document.Kind.PURCHASE, partner=self.supplier)
        docs.build_line(doc, variant=self.variant, quantity=D('50'), unit_price=D('800'))
        docs.confirm(doc)

        self.buy_batch(soon, '50', '1000')

        self.sell('50')

        balances = {
            (b.batch.code if b.batch else None): b.quantity
            for b in StockBalance.objects.select_related('batch').filter(
                variant=self.variant, warehouse=self.main
            )
        }

        self.assertEqual(balances['SOON'], D('0'))
        self.assertEqual(balances[None], D('50'))

    def test_explicit_batch_is_respected(self):
        late = self.make_batch('LATE', days=200)
        soon = self.make_batch('SOON', days=10)

        self.buy_batch(late, '100', '900')
        self.buy_batch(soon, '100', '1000')

        doc = self.make_doc(Document.Kind.SALE, partner=self.customer)
        docs.build_line(
            doc, variant=self.variant, quantity=D('30'),
            unit_price=D('1500'), batch=late,
        )
        docs.confirm(doc)

        balances = {
            b.batch.code: b.quantity
            for b in StockBalance.objects.select_related('batch').filter(
                variant=self.variant, warehouse=self.main
            )
        }

        self.assertEqual(balances['LATE'], D('70'))
        self.assertEqual(balances['SOON'], D('100'))

    def test_shortage_message_names_the_product(self):
        self.buy_batch(self.make_batch('A'), '10', '900')

        with self.assertRaises(ValidationError) as ctx:
            self.sell('50')

        self.assertIn('Sement', str(ctx.exception))


class CancelTests(DocumentTestBase):
    """Bekor qilish — teskari yozuv bilan, o'chirish emas."""

    def test_cancelling_draft_does_not_create_movements(self):
        doc = self.purchase('10', '900', confirm=False)
        docs.cancel(doc)

        self.assertEqual(doc.status, Document.Status.CANCELLED)
        self.assertEqual(StockMovement.objects.count(), 0)

    def test_cancelling_confirmed_reverses_stock(self):
        doc = self.purchase('100', '900')

        self.assertEqual(self.balance(), D('100'))

        docs.cancel(doc)

        self.assertEqual(self.balance(), D('0'))

    def test_cancellation_keeps_original_movement(self):
        """Jurnal append-only: asl yozuv tarixda qoladi."""
        doc = self.purchase('100', '900')
        docs.cancel(doc)

        movements = StockMovement.objects.filter(document_id=doc.pk).order_by('id')

        self.assertEqual(movements.count(), 2)
        self.assertEqual(movements[0].quantity, D('100'))
        self.assertEqual(movements[1].quantity, D('-100'))
        self.assertEqual(movements[1].meta['reversal_of'], doc.number)

    def test_cannot_cancel_twice(self):
        doc = self.purchase('10', '900')
        docs.cancel(doc)

        with self.assertRaises(ValidationError):
            docs.cancel(doc)

    def test_cancelling_sale_returns_stock(self):
        self.purchase('100', '900')

        doc = self.make_doc(Document.Kind.SALE, partner=self.customer)
        docs.build_line(doc, variant=self.variant, quantity=D('30'), unit_price=D('1500'))
        docs.confirm(doc)

        self.assertEqual(self.balance(), D('70'))

        docs.cancel(doc)

        self.assertEqual(self.balance(), D('100'))


class DocumentIsolationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.tenant_a = Tenant.objects.create(name='A', slug='doc-iso-a')
        cls.tenant_b = Tenant.objects.create(name='B', slug='doc-iso-b')

    def test_documents_are_isolated(self):
        for tenant in (self.tenant_a, self.tenant_b):
            with tenant_context(tenant.id):
                warehouse = Warehouse.objects.create(
                    tenant=tenant, code='W', name='Ombor'
                )
                Document.objects.create(
                    tenant=tenant,
                    kind=Document.Kind.PURCHASE,
                    number='KIR-2026-000001',
                    warehouse=warehouse,
                )

        with tenant_context(self.tenant_a.id):
            self.assertEqual(Document.objects.count(), 1)

    def test_partners_are_isolated(self):
        with tenant_context(self.tenant_a.id):
            Partner.objects.create(
                tenant=self.tenant_a, name='Yetkazuvchi', is_supplier=True
            )

        with tenant_context(self.tenant_b.id):
            self.assertEqual(Partner.objects.count(), 0)
