"""Aksiyalar: tanlangan tovar yoki kategoriya muddat davomida arzonlashadi.

Asosiy talablar: aksiyani server qo'llaydi (kassa uni chetlab o'tolmaydi),
muddat tugaganda narx o'zi qaytadi va kassir chegarasi faqat kassir
bergan chegirmaga qo'llanadi.
"""

from datetime import timedelta
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from apps.catalog.models import Category, Promotion
from apps.core.factories import (
    api_client,
    create_admin,
    create_cashier,
    create_product,
    receive_stock,
)
from apps.core.models import ShopSettings
from apps.reports.services import sales_report
from apps.sales.services import create_sale


def promotion(percent='30', *, products=(), categories=(), days=(0, 7), **fields) -> Promotion:
    """Bugundan `days[0]` kun keyin boshlanib, `days[1]` kun keyin tugaydigan aksiya."""
    today = timezone.localdate()
    promo = Promotion.objects.create(
        name=fields.pop('name', 'Kuzgi aksiya'),
        percent=Decimal(percent),
        starts_on=today + timedelta(days=days[0]),
        ends_on=today + timedelta(days=days[1]),
        **fields,
    )
    promo.products.set(products)
    promo.categories.set(categories)

    return promo


class PromotionApiTests(TestCase):

    def setUp(self):
        self.admin = api_client(create_admin())
        self.cashier = api_client(create_cashier())
        self.product = create_product(price='100000')
        self.today = timezone.localdate()

    def payload(self, **extra):
        return {
            'name': 'Kuzgi aksiya',
            'percent': '30',
            'starts_on': str(self.today),
            'ends_on': str(self.today + timedelta(days=7)),
            'products': [self.product.pk],
            **extra,
        }

    def test_admin_creates_promotion(self):
        response = self.admin.post('/api/promotions/', self.payload(), format='json')

        self.assertEqual(response.status_code, 201, response.content)
        self.assertEqual(response.json()['status'], 'running')
        self.assertEqual(response.json()['product_names'], [self.product.name])

    def test_cashier_cannot_manage_promotions(self):
        self.assertEqual(self.cashier.post('/api/promotions/', self.payload(), format='json').status_code, 403)
        self.assertEqual(self.cashier.get('/api/promotions/').status_code, 403)

    def test_promotion_needs_a_target_and_valid_dates(self):
        for extra, reason in (
            ({'products': [], 'categories': []}, 'tovar yoki kategoriya'),
            ({'ends_on': str(self.today - timedelta(days=1))}, 'boshlanishidan oldin'),
            ({'percent': '95'}, '90'),
            ({'percent': '0'}, '1'),
        ):
            response = self.admin.post('/api/promotions/', self.payload(**extra), format='json')

            self.assertEqual(response.status_code, 400, reason)
            self.assertIn(reason, response.content.decode(), reason)

    def test_promotion_is_stopped_not_deleted(self):
        """O'tgan cheklar aksiyaga bog'langan — u o'chirilmaydi, to'xtatiladi."""
        promo = promotion(products=[self.product])

        self.assertEqual(self.admin.delete(f'/api/promotions/{promo.pk}/').status_code, 405)

        response = self.admin.patch(f'/api/promotions/{promo.pk}/', {'is_active': False}, format='json')

        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()['status'], 'stopped')


class PromotionPriceTests(TestCase):
    """Kassa tovarni skanerlaganda aksiya narxini ko'radi."""

    def setUp(self):
        self.cashier = api_client(create_cashier())
        self.category = Category.objects.create(name='Kurtkalar')
        self.product = create_product(price='100000', category=self.category)
        self.variant = self.product.variants.get()

    def scanned(self):
        response = self.cashier.get('/api/variants/by-barcode/', {'code': self.variant.barcode})

        self.assertEqual(response.status_code, 200, response.content)

        return response.json()['promotion']

    def test_no_promotion(self):
        self.assertIsNone(self.scanned())

    def test_product_promotion(self):
        promo = promotion('30', products=[self.product])

        self.assertEqual(self.scanned()['id'], promo.pk)
        self.assertEqual(self.scanned()['price'], '70000.00')

    def test_category_promotion(self):
        promotion('20', categories=[self.category])

        self.assertEqual(self.scanned()['price'], '80000.00')

    def test_biggest_promotion_wins(self):
        """Aksiyalar qo'shilmaydi — eng kattasi olinadi."""
        promotion('20', categories=[self.category])
        promotion('35', products=[self.product], name='Katta')

        self.assertEqual(self.scanned()['name'], 'Katta')
        self.assertEqual(self.scanned()['price'], '65000.00')

    def test_only_running_promotions_apply(self):
        """Boshlanmagan, tugagan va to'xtatilgan aksiya narxga ta'sir qilmaydi."""
        promotion(products=[self.product], days=(1, 5))
        promotion(products=[self.product], days=(-10, -1))
        promotion(products=[self.product], is_active=False)

        self.assertIsNone(self.scanned())

    def test_last_day_still_counts(self):
        promotion(products=[self.product], days=(-3, 0))

        self.assertIsNotNone(self.scanned())


class PromotionSaleTests(TestCase):
    """Sotuvda aksiyani server qo'llaydi va hisobotda ko'rinadi."""

    def setUp(self):
        self.cashier = create_cashier()
        self.product = create_product(price='100000')
        self.variant = self.product.variants.get()
        receive_stock(self.variant, 10, '50000')

        settings = ShopSettings.load()
        settings.max_discount_percent = Decimal('10')
        settings.save()

        self.promo = promotion('30', products=[self.product])

    def sell(self, *, total, discount_percent='0', **line):
        return create_sale(
            user=self.cashier,
            lines=[{
                'variant': self.variant,
                'quantity': 2,
                'unit_price': Decimal('100000'),
                'discount_percent': Decimal(discount_percent),
                **line,
            }],
            cash_amount=Decimal(total),
        )

    def test_promotion_price_is_charged(self):
        sale = self.sell(total='140000', promotion=self.promo.pk)
        line = sale.lines.get()

        self.assertEqual(sale.subtotal, Decimal('200000'))
        self.assertEqual(sale.total, Decimal('140000'))
        self.assertEqual(line.promotion, self.promo)
        self.assertEqual(line.promotion_percent, Decimal('30'))
        self.assertEqual(line.promotion_discount, Decimal('60000'))

    def test_promotion_is_applied_even_if_till_did_not_say(self):
        """Server manba: kassa aksiyani yubormasa ham narx aksiyadagi."""
        sale = self.sell(total='140000')

        self.assertEqual(sale.lines.get().promotion, self.promo)

    def test_cashier_limit_ignores_promotion(self):
        """Aksiya 30 % — kassir chegarasi 10 %, lekin u o'z 5 % ini bera oladi."""
        sale = self.sell(total='130000', discount_percent='5', promotion=self.promo.pk)

        self.assertEqual(sale.discount_total, Decimal('70000'))

        with self.assertRaisesMessage(ValidationError, 'ruxsat etilgani'):
            self.sell(total='110000', discount_percent='15', promotion=self.promo.pk)

    def test_stale_cart_is_rejected(self):
        """Savat aksiya boshlanishidan oldin yig'ilgan — summa kassir aytganidan farq qilmasin."""
        with self.assertRaisesMessage(ValidationError, 'aksiya o‘zgargan'):
            self.sell(total='200000', promotion=None)

    def test_ended_promotion_restores_price(self):
        self.promo.ends_on = timezone.localdate() - timedelta(days=1)
        self.promo.save()

        sale = self.sell(total='200000')

        self.assertIsNone(sale.lines.get().promotion)

    def test_report_shows_promotion(self):
        self.sell(total='140000', promotion=self.promo.pk)

        today = timezone.localdate()
        rows = sales_report(today, today)['by_promotion']

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['name'], 'Kuzgi aksiya')
        self.assertEqual(rows[0]['quantity'], 2)
        self.assertEqual(rows[0]['revenue'], Decimal('140000'))
        self.assertEqual(rows[0]['discount'], Decimal('60000'))
