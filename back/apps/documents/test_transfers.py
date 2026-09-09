"""Omborlararo ko'chirish testlari — promptning 6-bandi."""

from __future__ import annotations

from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase

from apps.catalog.models import Category, Product, ProductUnit, Variant
from apps.core.tenancy import tenant_context
from apps.documents import services as docs
from apps.documents import transfer_services as transfers
from apps.documents.models import Document
from apps.documents.transfer_models import Transfer
from apps.pricing import services as pricing
from apps.pricing.models import Currency
from apps.stock.enums import MovementReason
from apps.stock.models import StockBalance, StockMovement
from apps.tenants.models import Tenant
from apps.warehouse.models import Warehouse

D = Decimal


class TransferTestBase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.tenant = Tenant.objects.create(
            name='Do\'kon', slug='transfer-test', base_currency='UZS'
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
            tenant=self.tenant, category=category, name='Sement', base_unit='kg'
        )
        self.variant = Variant.objects.create(
            tenant=self.tenant, product=product, sku='CEM-1'
        )

        ProductUnit.objects.create(
            tenant=self.tenant, variant=self.variant,
            unit='qop', factor_to_base=D('50'),
        )

        # Boshlang'ich qoldiq: 1000 kg @ 900
        doc = Document.objects.create(
            tenant=self.tenant, kind=Document.Kind.PURCHASE,
            number=docs.next_number(self.tenant, Document.Kind.PURCHASE),
            warehouse=self.main,
        )
        docs.build_line(doc, variant=self.variant, quantity=D('1000'), unit_price=D('900'))
        docs.confirm(doc)

    def tearDown(self):
        self.ctx.__exit__(None, None, None)

    def make_transfer(self, quantity='200', unit='', to=None):
        transfer = Transfer.objects.create(
            tenant=self.tenant,
            number=transfers.next_number(),
            from_warehouse=self.main,
            to_warehouse=to or self.shop,
            transit_warehouse=self.transit,
        )
        transfers.build_line(
            transfer, variant=self.variant, quantity=D(quantity), unit=unit
        )

        return transfer

    def balance(self, warehouse):
        row = StockBalance.objects.filter(
            variant=self.variant, warehouse=warehouse
        ).first()

        return row.quantity if row else D('0')


class TransferFlowTests(TransferTestBase):
    """Ikki bosqichli oqim: jo'natildi → qabul qilindi."""

    def test_draft_does_not_move_stock(self):
        self.make_transfer('200')

        self.assertEqual(self.balance(self.main), D('1000'))
        self.assertEqual(self.balance(self.transit), D('0'))

    def test_send_moves_stock_to_transit(self):
        transfer = self.make_transfer('200')
        transfers.send(transfer)

        self.assertEqual(transfer.status, Transfer.Status.SENT)
        self.assertEqual(self.balance(self.main), D('800'))
        self.assertEqual(self.balance(self.transit), D('200'))
        self.assertEqual(self.balance(self.shop), D('0'))

    def test_stock_in_transit_is_not_sellable(self):
        """Yo'ldagi tovar qoldiqda bor, lekin sotuvga chiqmaydi."""
        transfer = self.make_transfer('200')
        transfers.send(transfer)

        row = StockBalance.objects.get(variant=self.variant, warehouse=self.transit)

        self.assertEqual(row.quantity, D('200'))
        self.assertFalse(row.is_sellable)

    def test_nothing_is_lost_while_in_transit(self):
        transfer = self.make_transfer('200')
        transfers.send(transfer)

        total = sum(
            row.quantity for row in StockBalance.objects.filter(variant=self.variant)
        )

        self.assertEqual(total, D('1000'))

    def test_full_receipt_completes_transfer(self):
        transfer = self.make_transfer('200')
        transfers.send(transfer)
        transfers.receive(transfer)

        self.assertEqual(transfer.status, Transfer.Status.RECEIVED)
        self.assertEqual(self.balance(self.transit), D('0'))
        self.assertEqual(self.balance(self.shop), D('200'))
        self.assertFalse(transfer.has_shortfall)

    def test_pack_units_converted(self):
        """«4 qop» kiritiladi, qoldiq kilogrammda ko'chadi."""
        transfer = self.make_transfer('4', unit='qop')
        line = transfer.lines.get()

        self.assertEqual(line.quantity_sent, D('4'))
        self.assertEqual(line.quantity_sent_base, D('200'))

        transfers.send(transfer)

        self.assertEqual(self.balance(self.transit), D('200'))


class ShortfallTests(TransferTestBase):
    """Kamomad alohida ko'rinishi kerak — 6-bandning asosiy talabi."""

    def test_shortfall_recorded_as_loss(self):
        transfer = self.make_transfer('200')
        transfers.send(transfer)

        line = transfer.lines.get()
        transfers.receive(transfer, received={line.pk: D('185')})

        line.refresh_from_db()

        self.assertEqual(line.quantity_sent_base, D('200'))
        self.assertEqual(line.quantity_received_base, D('185'))
        self.assertEqual(line.shortfall, D('15'))
        self.assertTrue(transfer.has_shortfall)

    def test_shortfall_creates_transit_loss_movement(self):
        """Farq jimgina yutilmaydi — jurnalda alohida yozuv.

        InvenTree bu farqni `min()` bilan yutib yuboradi
        (order/models.py:4235) va u hech qayerda ko'rinmaydi.
        """
        transfer = self.make_transfer('200')
        transfers.send(transfer)

        line = transfer.lines.get()
        transfers.receive(transfer, received={line.pk: D('185')})

        losses = StockMovement.objects.filter(
            reason=MovementReason.TRANSIT_LOSS, document_id=transfer.pk
        )

        self.assertEqual(losses.count(), 1)
        self.assertEqual(losses.first().quantity, D('-15'))

    def test_transit_is_emptied_after_shortfall(self):
        transfer = self.make_transfer('200')
        transfers.send(transfer)

        line = transfer.lines.get()
        transfers.receive(transfer, received={line.pk: D('185')})

        self.assertEqual(self.balance(self.transit), D('0'))
        self.assertEqual(self.balance(self.shop), D('185'))

    def test_nothing_arrived_writes_off_everything(self):
        transfer = self.make_transfer('200')
        transfers.send(transfer)

        line = transfer.lines.get()
        transfers.receive(transfer, received={line.pk: D('0')})

        self.assertEqual(self.balance(self.transit), D('0'))
        self.assertEqual(self.balance(self.shop), D('0'))
        self.assertEqual(line.transfer.total_shortfall, D('200'))

    def test_cannot_receive_more_than_sent(self):
        transfer = self.make_transfer('200')
        transfers.send(transfer)

        line = transfer.lines.get()

        with self.assertRaises(ValidationError):
            transfers.receive(transfer, received={line.pk: D('250')})


class PrefetchStalenessTests(TransferTestBase):
    """Obyekt `prefetch_related` bilan yuklanganda ham to'g'ri javob berishi kerak.

    API `get_object()` ni `prefetch_related('lines...')` bilan chaqiradi.
    Amal bajarilgach `transfer.lines.all()` keshdagi **eski** nusxalarni
    qaytaradi — ular yangilangan `quantity_received_base` ni bilmaydi va
    kamomad nol bo'lib ko'rinadi.

    Bu xato dastlab testlar ushlamagan edi, chunki testlarda obyektlar
    to'g'ridan-to'g'ri yaratilardi.
    """

    def test_shortfall_correct_on_prefetched_object(self):
        transfer = self.make_transfer('200')
        transfers.send(transfer)

        line_id = transfer.lines.get().pk

        # API dagi kabi prefetch bilan yuklaymiz
        prefetched = (
            Transfer.objects.prefetch_related('lines__variant__product')
            .get(pk=transfer.pk)
        )

        # Keshni to'ldiramiz (serializer ham shunday qiladi)
        list(prefetched.lines.all())

        transfers.receive(prefetched, received={line_id: D('185')})

        # Javobdan oldin qayta o'qish shart — API `_reload()` shuni qiladi
        fresh = Transfer.objects.get(pk=transfer.pk)

        self.assertEqual(fresh.total_shortfall, D('15'))
        self.assertTrue(fresh.has_shortfall)


class DocumentPrefetchStalenessTests(TransferTestBase):
    """Hujjat summasi ham prefetch keshiga tayanmasligi kerak."""

    def test_total_cost_correct_on_prefetched_document(self):
        from apps.documents.models import DocumentLine

        sale = Document.objects.create(
            tenant=self.tenant, kind=Document.Kind.SALE,
            number=docs.next_number(self.tenant, Document.Kind.SALE),
            warehouse=self.main,
        )
        docs.build_line(sale, variant=self.variant, quantity=D('100'), unit_price=D('1500'))

        prefetched = (
            Document.objects.prefetch_related('lines__variant__product')
            .get(pk=sale.pk)
        )
        list(prefetched.lines.all())

        docs.confirm(prefetched)

        fresh = Document.objects.get(pk=sale.pk)

        # 100 × 900 tannarx, 100 × 1500 summa
        self.assertEqual(fresh.total_cost, D('90000'))
        self.assertEqual(fresh.total_amount, D('150000'))
        self.assertEqual(
            DocumentLine.objects.get(document=fresh).line_cost, D('90000')
        )


class TransferCostTests(TransferTestBase):
    """Ko'chirish xarid emas — tannarx o'zgarmaydi."""

    def test_cost_follows_the_goods(self):
        transfer = self.make_transfer('200')
        transfers.send(transfer)
        transfers.receive(transfer)

        # 200 × 900 tannarx do'konga ko'chdi, yangi tannarx paydo bo'lmadi
        self.assertEqual(pricing.stock_value(self.variant, self.shop), D('180000'))
        self.assertEqual(pricing.stock_value(self.variant, self.main), D('720000'))
        self.assertEqual(pricing.stock_value(self.variant, self.transit), D('0'))

    def test_total_value_unchanged_by_transfer(self):
        before = pricing.stock_value(self.variant)

        transfer = self.make_transfer('200')
        transfers.send(transfer)
        transfers.receive(transfer)

        self.assertEqual(pricing.stock_value(self.variant), before)


class TransferValidationTests(TransferTestBase):
    def test_same_warehouse_rejected(self):
        transfer = Transfer(
            tenant=self.tenant, number='X',
            from_warehouse=self.main, to_warehouse=self.main,
            transit_warehouse=self.transit,
        )

        with self.assertRaises(ValidationError):
            transfer.clean()

    def test_non_transit_warehouse_rejected_as_transit(self):
        """Tranzit sifatida oddiy ombor tanlansa, yo'ldagi tovar sotilib ketardi."""
        transfer = Transfer(
            tenant=self.tenant, number='X',
            from_warehouse=self.main, to_warehouse=self.shop,
            transit_warehouse=self.shop,
        )

        with self.assertRaises(ValidationError):
            transfer.clean()

    def test_cannot_send_empty_transfer(self):
        transfer = Transfer.objects.create(
            tenant=self.tenant, number=transfers.next_number(),
            from_warehouse=self.main, to_warehouse=self.shop,
            transit_warehouse=self.transit,
        )

        with self.assertRaises(ValidationError):
            transfers.send(transfer)

    def test_cannot_send_twice(self):
        transfer = self.make_transfer('200')
        transfers.send(transfer)

        with self.assertRaises(ValidationError):
            transfers.send(transfer)

    def test_cannot_receive_before_sending(self):
        transfer = self.make_transfer('200')

        with self.assertRaises(ValidationError):
            transfers.receive(transfer)

    def test_cannot_send_more_than_available(self):
        transfer = self.make_transfer('5000')

        with self.assertRaises(ValidationError):
            transfers.send(transfer)


class TransferCancelTests(TransferTestBase):
    def test_cancelling_draft_changes_nothing(self):
        transfer = self.make_transfer('200')
        transfers.cancel(transfer)

        self.assertEqual(transfer.status, Transfer.Status.CANCELLED)
        self.assertEqual(self.balance(self.main), D('1000'))

    def test_cancelling_sent_returns_stock_to_source(self):
        """Yo'ldagi tovar manba omborga qaytariladi."""
        transfer = self.make_transfer('200')
        transfers.send(transfer)

        self.assertEqual(self.balance(self.main), D('800'))

        transfers.cancel(transfer)

        self.assertEqual(self.balance(self.main), D('1000'))
        self.assertEqual(self.balance(self.transit), D('0'))

    def test_cannot_cancel_received(self):
        transfer = self.make_transfer('200')
        transfers.send(transfer)
        transfers.receive(transfer)

        with self.assertRaises(ValidationError):
            transfers.cancel(transfer)


class TransferIsolationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.tenant_a = Tenant.objects.create(name='A', slug='tr-iso-a')
        cls.tenant_b = Tenant.objects.create(name='B', slug='tr-iso-b')

    def test_transfers_are_isolated(self):
        for tenant in (self.tenant_a, self.tenant_b):
            with tenant_context(tenant.id):
                main = Warehouse.objects.create(tenant=tenant, code='M', name='Asosiy')
                shop = Warehouse.objects.create(
                    tenant=tenant, code='S', name='Do\'kon',
                    purpose=Warehouse.Purpose.RETAIL,
                )
                transit = Warehouse.objects.create(
                    tenant=tenant, code='T', name='Yo\'lda',
                    purpose=Warehouse.Purpose.TRANSIT,
                )
                Transfer.objects.create(
                    tenant=tenant, number='KOCH-2026-000001',
                    from_warehouse=main, to_warehouse=shop,
                    transit_warehouse=transit,
                )

        with tenant_context(self.tenant_a.id):
            self.assertEqual(Transfer.objects.count(), 1)
