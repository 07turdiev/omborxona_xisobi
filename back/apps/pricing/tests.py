"""FIFO tannarx va valyuta kursi testlari."""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from apps.catalog.models import Category, Product, Variant
from apps.core.tenancy import tenant_context
from apps.pricing import services as pricing
from apps.pricing.models import CostConsumption, CostLayer, Currency, ExchangeRate
from apps.stock import services as stock
from apps.stock.enums import MovementReason
from apps.stock.models import Batch
from apps.tenants.models import Tenant
from apps.warehouse.models import Warehouse

D = Decimal


class PricingTestBase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.tenant = Tenant.objects.create(
            name='Do\'kon', slug='pricing-test', base_currency='UZS'
        )

    def setUp(self):
        self.ctx = tenant_context(self.tenant.id)
        self.ctx.__enter__()

        self.uzs = Currency.objects.create(
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

        category = Category.objects.create(tenant=self.tenant, name='Sement')
        product = Product.objects.create(
            tenant=self.tenant, category=category, name='Sement', base_unit='kg'
        )
        self.variant = Variant.objects.create(
            tenant=self.tenant, product=product, sku='CEM-1'
        )

    def tearDown(self):
        self.ctx.__exit__(None, None, None)

    def buy(self, quantity, cost, warehouse=None, batch=None, currency='UZS', when=None):
        return stock.record_movement(
            variant=self.variant,
            warehouse=warehouse or self.main,
            batch=batch,
            quantity=D(quantity),
            reason=MovementReason.PURCHASE,
            unit_cost=D(cost),
            currency=currency,
            occurred_at=when,
        )

    def sell(self, quantity, warehouse=None, batch=None):
        return stock.record_movement(
            variant=self.variant,
            warehouse=warehouse or self.main,
            batch=batch,
            quantity=-D(quantity),
            reason=MovementReason.SALE,
        )


class FifoTests(PricingTestBase):
    """FIFO — eng eski qatlam birinchi yechiladi."""

    def test_purchase_creates_layer(self):
        movement = self.buy('100', '900')
        layer = CostLayer.objects.get(movement=movement)

        self.assertEqual(layer.quantity_initial, D('100'))
        self.assertEqual(layer.quantity_remaining, D('100'))
        self.assertEqual(layer.unit_cost_base, D('900'))

    def test_sale_consumes_oldest_layer_first(self):
        self.buy('100', '900')
        self.buy('100', '1100')

        movement = self.sell('60')

        # 60 × 900 = 54 000 — faqat birinchi qatlamdan
        self.assertEqual(pricing.movement_cost(movement), D('54000'))

        first, second = CostLayer.objects.order_by('acquired_at', 'id')
        self.assertEqual(first.quantity_remaining, D('40'))
        self.assertEqual(second.quantity_remaining, D('100'))

    def test_sale_spans_multiple_layers(self):
        """Bir sotuv bir necha qatlamni yechishi mumkin."""
        self.buy('100', '900')
        self.buy('100', '1100')

        movement = self.sell('150')

        # 100 × 900 + 50 × 1100 = 90 000 + 55 000 = 145 000
        self.assertEqual(pricing.movement_cost(movement), D('145000'))

        self.assertEqual(CostConsumption.objects.filter(movement=movement).count(), 2)

    def test_consumption_records_which_layer(self):
        """«Bu chekning tannarxi nega shuncha?» savoliga javob bo'lishi kerak."""
        self.buy('100', '900')
        self.buy('100', '1100')

        movement = self.sell('150')
        rows = CostConsumption.objects.filter(movement=movement).order_by('id')

        self.assertEqual([(r.quantity, r.unit_cost_base) for r in rows],
                         [(D('100.000'), D('900.00')), (D('50.000'), D('1100.00'))])

    def test_layers_are_per_warehouse(self):
        """Bir ombordagi qatlam boshqasining sotuvida yechilmaydi."""
        self.buy('100', '900', warehouse=self.main)
        self.buy('100', '1500', warehouse=self.shop)

        movement = self.sell('10', warehouse=self.shop)

        self.assertEqual(pricing.movement_cost(movement), D('15000'))

    def test_layers_are_per_batch(self):
        first = Batch.objects.create(
            tenant=self.tenant, variant=self.variant, code='B-1'
        )
        second = Batch.objects.create(
            tenant=self.tenant, variant=self.variant, code='B-2'
        )

        self.buy('100', '900', batch=first)
        self.buy('100', '1300', batch=second)

        movement = self.sell('10', batch=second)

        self.assertEqual(pricing.movement_cost(movement), D('13000'))

    def test_sale_without_layers_has_no_cost(self):
        """Tannarxsiz kirilgan tovar sotilsa, tannarx nol bo'ladi.

        Bu xato emas: boshlang'ich qoldiq tannarxsiz kiritilishi mumkin.
        Hisobotda bunday sotuv alohida ko'rinishi kerak.
        """
        stock.record_movement(
            variant=self.variant, warehouse=self.main,
            quantity=D('50'), reason=MovementReason.OPENING_BALANCE,
        )

        movement = self.sell('10')

        self.assertEqual(pricing.movement_cost(movement), D('0'))

    def test_stock_value_uses_real_layer_costs(self):
        """Qoldiq qiymati turli narxdagi partiyalarni hisobga oladi.

        `qoldiq × joriy narx` noto'g'ri javob berardi: 200 × 1100 =
        220 000, aslida esa 100×900 + 100×1100 = 200 000.
        """
        self.buy('100', '900')
        self.buy('100', '1100')

        self.assertEqual(pricing.stock_value(self.variant, self.main), D('200000'))

    def test_rebuild_matches_incremental(self):
        """Qatlamlar ham hosila: jurnaldan qayta qurish mumkin."""
        self.buy('100', '900')
        self.buy('100', '1100')
        self.sell('150')

        before = pricing.stock_value(self.variant, self.main)

        pricing.rebuild_layers(self.variant)

        self.assertEqual(pricing.stock_value(self.variant, self.main), before)
        self.assertEqual(before, D('55000'))  # qolgan 50 × 1100


class ExchangeRateTests(PricingTestBase):
    """Kurs tarixi — 6-arxitektura qarori."""

    def setUp(self):
        super().setUp()

        self.usd = Currency.objects.create(
            tenant=self.tenant, code='USD', name='Dollar'
        )

        ExchangeRate.objects.create(
            tenant=self.tenant, currency=self.usd,
            rate=D('12000'), valid_from=date(2026, 1, 1),
        )
        ExchangeRate.objects.create(
            tenant=self.tenant, currency=self.usd,
            rate=D('12650'), valid_from=date(2026, 6, 1),
        )

    def test_rate_is_looked_up_by_date(self):
        self.assertEqual(
            pricing.rate_on('USD', date(2026, 3, 15), self.tenant), D('12000')
        )
        self.assertEqual(
            pricing.rate_on('USD', date(2026, 9, 1), self.tenant), D('12650')
        )

    def test_rate_stays_valid_until_next_one(self):
        """Kurs keyingisi paydo bo'lgunicha kuchda qoladi."""
        self.assertEqual(
            pricing.rate_on('USD', date(2026, 5, 31), self.tenant), D('12000')
        )

    def test_base_currency_rate_is_one(self):
        self.assertEqual(pricing.rate_on('UZS', date(2026, 3, 1), self.tenant), D('1'))

    def test_missing_rate_raises(self):
        with self.assertRaises(ValidationError):
            pricing.rate_on('USD', date(2025, 12, 31), self.tenant)

    def test_layer_cost_frozen_at_purchase_rate(self):
        """Kurs keyin o'zgarsa ham eski qatlam tannarxi o'zgarmaydi.

        Aks holda eski sotuvlarning foydasi o'z-o'zidan qayta
        hisoblanib ketardi. `django-money` ning `Rate` jadvali faqat
        joriy kursni saqlagani uchun bunga imkon bermasdi.
        """
        when = timezone.make_aware(
            timezone.datetime(2026, 3, 15, 10, 0)
        )
        self.buy('10', '100', currency='USD', when=when)

        layer = CostLayer.objects.get()

        self.assertEqual(layer.exchange_rate, D('12000'))
        self.assertEqual(layer.unit_cost_base, D('1200000'))

        # Yangi kurs qo'shamiz — eski qatlam o'zgarmasligi kerak
        ExchangeRate.objects.create(
            tenant=self.tenant, currency=self.usd,
            rate=D('20000'), valid_from=timezone.localdate() + timedelta(days=1),
        )
        layer.refresh_from_db()

        self.assertEqual(layer.unit_cost_base, D('1200000'))


class TransferCostTests(PricingTestBase):
    """Ko'chirishda tannarx tovar bilan birga yuradi."""

    def test_transfer_moves_cost_not_creates_new(self):
        """Ombordan omborga ko'chirish xarid emas — tannarx o'zgarmaydi."""
        self.buy('100', '900')

        stock.transfer_out(
            variant=self.variant, warehouse=self.main,
            transit_warehouse=self.transit, quantity=D('40'),
        )

        transit_value = pricing.stock_value(self.variant, self.transit)
        main_value = pricing.stock_value(self.variant, self.main)

        self.assertEqual(transit_value, D('36000'))  # 40 × 900
        self.assertEqual(main_value, D('54000'))     # 60 × 900
        self.assertEqual(transit_value + main_value, D('90000'))

    def test_cost_survives_full_transfer(self):
        self.buy('100', '900')

        stock.transfer_out(
            variant=self.variant, warehouse=self.main,
            transit_warehouse=self.transit, quantity=D('40'),
        )
        stock.transfer_in(
            variant=self.variant, transit_warehouse=self.transit,
            warehouse=self.shop, quantity=D('40'),
        )

        self.assertEqual(pricing.stock_value(self.variant, self.shop), D('36000'))
        self.assertEqual(pricing.stock_value(self.variant, self.transit), D('0'))

    def test_fifo_order_preserved_after_transfer(self):
        """Ko'chirilgan qatlam o'z yoshini saqlaydi.

        Aks holda arzon eski tovar ko'chirilgach "yangi" bo'lib qolib,
        FIFO tartibi buzilardi.
        """
        self.buy('50', '900')
        self.buy('50', '1500')

        stock.transfer_out(
            variant=self.variant, warehouse=self.main,
            transit_warehouse=self.transit, quantity=D('100'),
        )
        stock.transfer_in(
            variant=self.variant, transit_warehouse=self.transit,
            warehouse=self.shop, quantity=D('100'),
        )

        movement = self.sell('50', warehouse=self.shop)

        # Eng eski (900 lik) qatlam birinchi yechilishi kerak
        self.assertEqual(pricing.movement_cost(movement), D('45000'))

    def test_rebuild_preserves_transferred_cost(self):
        """Qayta qurishda ko'chirilgan tovarning tannarxi yo'qolmasligi kerak.

        Ko'chirish ikki omborni bog'laydi, shuning uchun qayta qurish
        ombor kesimida emas, **variant kesimida** bo'lishi shart.
        Ombor bo'yicha qayta qurganda maqsad ombordagi tovar tannarxsiz
        qolib ketardi.
        """
        self.buy('100', '900')
        stock.transfer_out(
            variant=self.variant, warehouse=self.main,
            transit_warehouse=self.transit, quantity=D('40'),
        )
        stock.transfer_in(
            variant=self.variant, transit_warehouse=self.transit,
            warehouse=self.shop, quantity=D('40'),
        )

        before_main = pricing.stock_value(self.variant, self.main)
        before_shop = pricing.stock_value(self.variant, self.shop)

        pricing.rebuild_layers(self.variant)

        self.assertEqual(pricing.stock_value(self.variant, self.main), before_main)
        self.assertEqual(pricing.stock_value(self.variant, self.shop), before_shop)
        self.assertEqual(before_shop, D('36000'))

    def test_rebuild_preserves_cost_after_shortfall(self):
        """Kamomad bilan tugagan ko'chirishda ham qiymat izchil qoladi."""
        self.buy('100', '900')
        stock.transfer_out(
            variant=self.variant, warehouse=self.main,
            transit_warehouse=self.transit, quantity=D('40'),
        )
        stock.transfer_in(
            variant=self.variant, transit_warehouse=self.transit,
            warehouse=self.shop, quantity=D('37'),
        )

        before = {
            w.pk: pricing.stock_value(self.variant, w)
            for w in (self.main, self.shop, self.transit)
        }

        pricing.rebuild_layers(self.variant)

        after = {
            w.pk: pricing.stock_value(self.variant, w)
            for w in (self.main, self.shop, self.transit)
        }

        self.assertEqual(before, after)
        self.assertEqual(after[self.shop.pk], D('33300'))  # 37 × 900
        self.assertEqual(after[self.transit.pk], D('0'))


class PricingIsolationTests(TestCase):
    """Tannarx ma'lumoti ham RLS bilan himoyalangan."""

    @classmethod
    def setUpTestData(cls):
        cls.tenant_a = Tenant.objects.create(name='A', slug='price-iso-a')
        cls.tenant_b = Tenant.objects.create(name='B', slug='price-iso-b')

    def test_currencies_are_isolated(self):
        with tenant_context(self.tenant_a.id):
            Currency.objects.create(
                tenant=self.tenant_a, code='USD', name='Dollar'
            )

        with tenant_context(self.tenant_b.id):
            self.assertEqual(Currency.objects.count(), 0)

    def test_same_currency_code_allowed_in_both(self):
        for tenant in (self.tenant_a, self.tenant_b):
            with tenant_context(tenant.id):
                Currency.objects.create(tenant=tenant, code='USD', name='Dollar')

        with tenant_context(self.tenant_a.id):
            self.assertEqual(Currency.objects.count(), 1)
