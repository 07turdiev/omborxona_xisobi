"""Hisobot testlari.

Asosiy e'tibor bitta narsaga: **yo'qotish sotuvdan ajratilishi kerak**.
Prototipda bunday ajratish yo'q edi va foyda haqiqiydan katta bo'lib
chiqardi.
"""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from apps.catalog.models import Category, Product, Variant
from apps.core.tenancy import tenant_context
from apps.documents import services as docs
from apps.documents.models import Document
from apps.partners.models import Partner
from apps.pricing.models import Currency
from apps.reports import services as reports
from apps.stock import services as stock
from apps.stock.enums import MovementReason
from apps.stock.models import Batch
from apps.tenants.models import Tenant
from apps.warehouse.models import Warehouse

D = Decimal


class ReportTestBase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.tenant = Tenant.objects.create(
            name='Do\'kon', slug='report-test', base_currency='UZS'
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

        self.supplier = Partner.objects.create(
            tenant=self.tenant, name='Yetkazuvchi', is_supplier=True
        )
        self.customer = Partner.objects.create(
            tenant=self.tenant, name='Mijoz', is_customer=True
        )

        # Ikki darajali daraxt — hisobot ildiz kategoriya bo'yicha guruhlaydi
        self.root = Category.objects.create(
            tenant=self.tenant, name='Qurilish', default_unit='kg'
        )
        self.child = Category.objects.create(
            tenant=self.tenant, name='Sement', parent=self.root
        )

        product = Product.objects.create(
            tenant=self.tenant, category=self.child, name='Sement', base_unit='kg'
        )
        self.variant = Variant.objects.create(
            tenant=self.tenant, product=product, sku='CEM-1', sale_price=D('1500')
        )

    def tearDown(self):
        self.ctx.__exit__(None, None, None)

    def buy(self, quantity, price, warehouse=None):
        doc = Document.objects.create(
            tenant=self.tenant, kind=Document.Kind.PURCHASE,
            number=docs.next_number(self.tenant, Document.Kind.PURCHASE),
            warehouse=warehouse or self.main, partner=self.supplier,
        )
        docs.build_line(
            doc, variant=self.variant, quantity=D(quantity), unit_price=D(price)
        )
        docs.recalculate_totals(doc)

        return docs.confirm(doc)

    def sell(self, quantity, price, warehouse=None):
        doc = Document.objects.create(
            tenant=self.tenant, kind=Document.Kind.SALE,
            number=docs.next_number(self.tenant, Document.Kind.SALE),
            warehouse=warehouse or self.main, partner=self.customer,
        )
        docs.build_line(
            doc, variant=self.variant, quantity=D(quantity), unit_price=D(price)
        )
        docs.recalculate_totals(doc)

        return docs.confirm(doc)


class PeriodSummaryTests(ReportTestBase):
    def test_revenue_cost_and_profit(self):
        self.buy('100', '900')
        self.sell('60', '1500')

        summary = reports.period_summary()

        self.assertEqual(summary['revenue'], D('90000'))
        self.assertEqual(summary['cost'], D('54000'))
        self.assertEqual(summary['gross_profit'], D('36000'))
        self.assertEqual(summary['margin_percent'], 40.0)

    def test_draft_documents_excluded(self):
        self.buy('100', '900')

        doc = Document.objects.create(
            tenant=self.tenant, kind=Document.Kind.SALE,
            number=docs.next_number(self.tenant, Document.Kind.SALE),
            warehouse=self.main, partner=self.customer,
        )
        docs.build_line(doc, variant=self.variant, quantity=D('10'), unit_price=D('1500'))
        docs.recalculate_totals(doc)

        self.assertEqual(reports.period_summary()['revenue'], D('0'))

    def test_cancelled_documents_excluded(self):
        self.buy('100', '900')
        sale = self.sell('60', '1500')
        docs.cancel(sale)

        self.assertEqual(reports.period_summary()['revenue'], D('0'))

    def test_period_filter_applied(self):
        self.buy('100', '900')
        sale = self.sell('60', '1500')

        yesterday = timezone.localdate() - timedelta(days=1)
        sale.date = yesterday
        sale.save(update_fields=['date'])

        today = timezone.localdate()

        self.assertEqual(reports.period_summary(date_from=today)['revenue'], D('0'))
        self.assertEqual(
            reports.period_summary(date_from=yesterday)['revenue'], D('90000')
        )


class LossReportTests(ReportTestBase):
    """Yo'qotish sotuvdan ajratilishi kerak."""

    def test_write_off_appears_as_loss_not_sale(self):
        self.buy('100', '900')

        stock.record_movement(
            variant=self.variant, warehouse=self.main,
            quantity=D('-10'), reason=MovementReason.WRITE_OFF_DAMAGED,
        )

        summary = reports.period_summary()

        # Yo'qotish tushumga qo'shilmaydi
        self.assertEqual(summary['revenue'], D('0'))
        # Lekin tannarx bo'yicha baholanadi: 10 × 900
        self.assertEqual(summary['loss_amount'], D('9000'))

    def test_net_profit_subtracts_losses(self):
        """Sof foyda yo'qotishni hisobga oladi.

        Prototipda bunday ko'rsatkich yo'q va foyda haqiqiydan katta
        ko'rinardi.
        """
        self.buy('100', '900')
        self.sell('60', '1500')

        stock.record_movement(
            variant=self.variant, warehouse=self.main,
            quantity=D('-10'), reason=MovementReason.WRITE_OFF_DAMAGED,
        )

        summary = reports.period_summary()

        self.assertEqual(summary['gross_profit'], D('36000'))
        self.assertEqual(summary['loss_amount'], D('9000'))
        self.assertEqual(summary['net_profit'], D('27000'))

    def test_stocktake_shortage_counted_as_loss(self):
        self.buy('100', '900')

        stock.stocktake(
            variant=self.variant, warehouse=self.main, counted_quantity=D('95')
        )

        losses = reports.loss_summary()

        self.assertEqual(losses['total'], D('4500'))
        self.assertEqual(
            losses['by_reason'][0]['reason'], MovementReason.STOCKTAKE_CORRECTION
        )

    def test_losses_grouped_by_reason(self):
        self.buy('100', '900')

        stock.record_movement(
            variant=self.variant, warehouse=self.main,
            quantity=D('-5'), reason=MovementReason.WRITE_OFF_DAMAGED,
        )
        stock.record_movement(
            variant=self.variant, warehouse=self.main,
            quantity=D('-3'), reason=MovementReason.WRITE_OFF_EXPIRED,
        )

        reasons = {row['reason'] for row in reports.loss_summary()['by_reason']}

        self.assertEqual(
            reasons,
            {MovementReason.WRITE_OFF_DAMAGED, MovementReason.WRITE_OFF_EXPIRED},
        )

    def test_sale_is_not_a_loss(self):
        self.buy('100', '900')
        self.sell('60', '1500')

        self.assertEqual(reports.loss_summary()['total'], D('0'))


class BreakdownTests(ReportTestBase):
    def test_category_rolls_up_to_root(self):
        """Hisobotda "Sement" emas, "Qurilish" ko'rsatiladi.

        Aks holda diagramma o'nlab ustundan iborat bo'lib ketardi.
        """
        self.buy('100', '900')
        self.sell('60', '1500')

        rows = reports.by_category()

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['name'], 'Qurilish')
        self.assertEqual(rows[0]['revenue'], D('90000'))
        self.assertEqual(rows[0]['profit'], D('36000'))

    def test_warehouse_breakdown(self):
        self.buy('100', '900', warehouse=self.shop)
        self.sell('40', '1500', warehouse=self.shop)

        rows = reports.by_warehouse()

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['name'], 'Do\'kon')
        self.assertEqual(rows[0]['revenue'], D('60000'))

    def test_top_products_sorted_by_revenue(self):
        self.buy('100', '900')
        self.sell('60', '1500')

        rows = reports.top_products()

        self.assertEqual(rows[0]['sku'], 'CEM-1')
        self.assertEqual(rows[0]['revenue'], D('90000'))
        self.assertEqual(rows[0]['profit'], D('36000'))

    def test_daily_sales(self):
        self.buy('100', '900')
        self.sell('60', '1500')

        rows = reports.daily_sales()

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['revenue'], D('90000'))


class ValuationTests(ReportTestBase):
    def test_cost_value_uses_fifo_layers(self):
        """Turli narxdagi partiyalar to'g'ri hisoblanadi."""
        self.buy('100', '900')
        self.buy('100', '1100')

        valuation = reports.stock_valuation()

        # 100×900 + 100×1100 = 200 000, `200 × 1100` emas
        self.assertEqual(valuation['cost_value'], D('200000'))
        self.assertEqual(valuation['units'], D('200'))

    def test_potential_profit(self):
        self.buy('100', '900')

        valuation = reports.stock_valuation()

        # 100 × 1500 (sotuv narxi) − 100 × 900 (tannarx)
        self.assertEqual(valuation['retail_value'], D('150000'))
        self.assertEqual(valuation['potential_profit'], D('60000'))

    def test_expiring_batches_listed(self):
        batch = Batch.objects.create(
            tenant=self.tenant, variant=self.variant, code='SOON',
            expiry_date=timezone.localdate() + timedelta(days=10),
        )
        stock.record_movement(
            variant=self.variant, warehouse=self.main, batch=batch,
            quantity=D('50'), reason=MovementReason.PURCHASE,
            unit_cost=D('900'), currency='UZS',
        )

        rows = reports.expiring_batches(days=30)

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['batch_code'], 'SOON')
        self.assertEqual(rows[0]['days_left'], 10)
        self.assertFalse(rows[0]['is_expired'])

    def test_low_stock_listed(self):
        self.variant.min_stock = D('60')
        self.variant.save(update_fields=['min_stock'])

        self.buy('50', '900')

        rows = reports.low_stock()

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['sku'], 'CEM-1')


class ReportIsolationTests(TestCase):
    """Hisobot ham RLS ostida — begona tashkilot ma'lumoti kirmaydi."""

    @classmethod
    def setUpTestData(cls):
        cls.tenant_a = Tenant.objects.create(name='A', slug='rep-iso-a')
        cls.tenant_b = Tenant.objects.create(name='B', slug='rep-iso-b')

    def make_sale(self, tenant, price):
        with tenant_context(tenant.id):
            Currency.objects.create(
                tenant=tenant, code='UZS', name='So\'m', is_base=True
            )
            warehouse = Warehouse.objects.create(
                tenant=tenant, code='W', name='Ombor'
            )
            category = Category.objects.create(tenant=tenant, name='Tovar')
            product = Product.objects.create(
                tenant=tenant, category=category, name='Tovar', base_unit='dona'
            )
            variant = Variant.objects.create(
                tenant=tenant, product=product, sku='S-1'
            )

            purchase = Document.objects.create(
                tenant=tenant, kind=Document.Kind.PURCHASE,
                number=docs.next_number(tenant, Document.Kind.PURCHASE),
                warehouse=warehouse,
            )
            docs.build_line(
                purchase, variant=variant, quantity=D('10'), unit_price=D('100')
            )
            docs.confirm(purchase)

            sale = Document.objects.create(
                tenant=tenant, kind=Document.Kind.SALE,
                number=docs.next_number(tenant, Document.Kind.SALE),
                warehouse=warehouse,
            )
            docs.build_line(
                sale, variant=variant, quantity=D('5'), unit_price=D(price)
            )
            docs.recalculate_totals(sale)
            docs.confirm(sale)

    def test_revenue_is_isolated(self):
        self.make_sale(self.tenant_a, '200')
        self.make_sale(self.tenant_b, '999')

        with tenant_context(self.tenant_a.id):
            self.assertEqual(reports.period_summary()['revenue'], D('1000'))

        with tenant_context(self.tenant_b.id):
            self.assertEqual(reports.period_summary()['revenue'], D('4995'))
