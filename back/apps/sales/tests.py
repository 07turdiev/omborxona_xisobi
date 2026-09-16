"""Kassa testlari: sotuv, qaytarish, almashtirish, bekor qilish."""

from decimal import Decimal
from threading import Thread

from django.core.exceptions import ValidationError
from django.db import connections
from django.test import TestCase, TransactionTestCase
from django.utils import timezone
from freezegun import freeze_time

from apps.catalog.models import Variant
from apps.core.factories import (
    api_client,
    create_admin,
    create_cashier,
    create_product,
    receive_stock,
)
from apps.core.models import ShopSettings
from apps.inventory.models import MovementReason, StockMovement
from apps.sales.models import Sale, SaleReturn
from apps.sales.services import create_return, create_sale, void_sale


class SaleMathTests(TestCase):

    def setUp(self):
        self.cashier = create_cashier()
        self.client_cashier = api_client(self.cashier)
        self.variant = create_product(price='250000').variants.get()
        receive_stock(self.variant, 10, '150000')

    def test_sale_with_line_discount(self):
        """2 dona × 250 000, 10 % chegirma bilan."""
        response = self.client_cashier.post(
            '/api/sales/',
            {
                'lines': [
                    {
                        'variant': self.variant.pk,
                        'quantity': 2,
                        'unit_price': '250000',
                        'discount_percent': '10',
                    }
                ],
                'cash_amount': '450000',
            },
            format='json',
        )

        self.assertEqual(response.status_code, 201, response.content)

        body = response.json()
        self.assertEqual(Decimal(body['subtotal']), Decimal('500000.00'))
        self.assertEqual(Decimal(body['discount_total']), Decimal('50000.00'))
        self.assertEqual(Decimal(body['total']), Decimal('450000.00'))

        sale = Sale.objects.get(pk=body['id'])
        line = sale.lines.get()

        self.assertEqual(line.line_total, Decimal('450000.00'))
        self.assertEqual(line.unit_cost, Decimal('150000.00'))
        self.assertEqual(line.line_cost, Decimal('300000.00'))
        self.assertEqual(line.profit, Decimal('150000.00'))

        self.assertEqual(Variant.objects.get(pk=self.variant.pk).stock_quantity, 8)

    def test_receipt_discount_is_shared_between_lines(self):
        other = create_product(name='Yubka', price='100000').variants.get()
        receive_stock(other, 5, '40000')

        sale = create_sale(
            user=self.cashier,
            lines=[
                {'variant': self.variant, 'quantity': 1, 'unit_price': Decimal('250000')},
                {'variant': other, 'quantity': 1, 'unit_price': Decimal('100000')},
            ],
            discount_amount=Decimal('35000'),
            cash_amount=Decimal('315000'),
        )

        self.assertEqual(sale.total, Decimal('315000.00'))
        self.assertEqual(sale.discount_total, Decimal('35000.00'))
        self.assertEqual(
            sum(line.discount_amount for line in sale.lines.all()), Decimal('35000.00')
        )
        self.assertEqual(
            sum(line.line_total for line in sale.lines.all()), Decimal('315000.00')
        )

    def test_selling_more_than_stock_writes_nothing(self):
        response = self.client_cashier.post(
            '/api/sales/',
            {
                'lines': [{'variant': self.variant.pk, 'quantity': 11, 'unit_price': '250000'}],
                'cash_amount': '2750000',
            },
            format='json',
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn('yetarli emas', ' '.join(response.json()['detail']))

        self.assertEqual(Sale.objects.count(), 0)
        self.assertEqual(Variant.objects.get(pk=self.variant.pk).stock_quantity, 10)
        self.assertFalse(StockMovement.objects.filter(reason=MovementReason.SALE).exists())

    def test_payment_must_match_total(self):
        response = self.client_cashier.post(
            '/api/sales/',
            {
                'lines': [{'variant': self.variant.pk, 'quantity': 1, 'unit_price': '250000'}],
                'cash_amount': '200000',
            },
            format='json',
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(Sale.objects.count(), 0)

    def test_mixed_payment_is_allowed(self):
        sale = create_sale(
            user=self.cashier,
            lines=[{'variant': self.variant, 'quantity': 1, 'unit_price': Decimal('250000')}],
            cash_amount=Decimal('100000'),
            card_amount=Decimal('150000'),
        )

        self.assertEqual(sale.total, Decimal('250000.00'))

    def test_cashier_discount_limit(self):
        settings = ShopSettings.load()
        settings.max_discount_percent = Decimal('10')
        settings.save()

        with self.assertRaises(ValidationError):
            create_sale(
                user=self.cashier,
                lines=[
                    {
                        'variant': self.variant,
                        'quantity': 1,
                        'unit_price': Decimal('250000'),
                        'discount_percent': Decimal('20'),
                    }
                ],
                cash_amount=Decimal('200000'),
            )

        # Administratorga cheklov yo'q
        sale = create_sale(
            user=create_admin(),
            lines=[
                {
                    'variant': self.variant,
                    'quantity': 1,
                    'unit_price': Decimal('250000'),
                    'discount_percent': Decimal('20'),
                }
            ],
            cash_amount=Decimal('200000'),
        )

        self.assertEqual(sale.total, Decimal('200000.00'))


class ReturnTests(TestCase):

    def setUp(self):
        self.cashier = create_cashier()
        self.client_cashier = api_client(self.cashier)
        self.variant = create_product(price='250000').variants.get()
        receive_stock(self.variant, 10, '150000')

        self.sale = create_sale(
            user=self.cashier,
            lines=[
                {
                    'variant': self.variant,
                    'quantity': 2,
                    'unit_price': Decimal('250000'),
                    'discount_percent': Decimal('10'),
                }
            ],
            cash_amount=Decimal('450000'),
        )
        self.line = self.sale.lines.get()

    def test_return_restores_stock_at_original_cost(self):
        response = self.client_cashier.post(
            '/api/returns/',
            {
                'sale': self.sale.pk,
                'items': [{'sale_line': self.line.pk, 'quantity': 1}],
                'refund_method': 'cash',
            },
            format='json',
        )

        self.assertEqual(response.status_code, 201, response.content)

        body = response.json()
        # Chegirmali narx qaytadi: 450 000 / 2 = 225 000
        self.assertEqual(Decimal(body['total']), Decimal('225000.00'))
        self.assertTrue(body['number'].startswith('QAY-'))

        self.assertEqual(Variant.objects.get(pk=self.variant.pk).stock_quantity, 9)

        movement = StockMovement.objects.filter(reason=MovementReason.RETURN).get()
        self.assertEqual(movement.quantity, 1)
        self.assertEqual(movement.unit_cost, Decimal('150000.00'))

    def test_cannot_return_more_than_sold_across_returns(self):
        create_return(
            sale=self.sale,
            items=[{'sale_line': self.line, 'quantity': 1}],
            refund_method=SaleReturn.RefundMethod.CASH,
            user=self.cashier,
        )

        response = self.client_cashier.post(
            '/api/returns/',
            {
                'sale': self.sale.pk,
                'items': [{'sale_line': self.line.pk, 'quantity': 2}],
                'refund_method': 'cash',
            },
            format='json',
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(SaleReturn.objects.count(), 1)
        self.assertEqual(Variant.objects.get(pk=self.variant.pk).stock_quantity, 9)

    def test_full_return_refunds_exact_line_total(self):
        """Uch donani birma-bir qaytarganda tiyin yo'qolmaydi."""
        variant = create_product(name='Futbolka', price='100000').variants.get()
        receive_stock(variant, 5, '40000')

        sale = create_sale(
            user=self.cashier,
            lines=[
                {
                    'variant': variant,
                    'quantity': 3,
                    'unit_price': Decimal('100000'),
                    'discount_amount': Decimal('10000'),
                }
            ],
            cash_amount=Decimal('290000'),
        )
        line = sale.lines.get()

        refunds = [
            create_return(
                sale=sale,
                items=[{'sale_line': line, 'quantity': 1}],
                refund_method=SaleReturn.RefundMethod.CASH,
                user=self.cashier,
            ).total
            for _ in range(3)
        ]

        self.assertEqual(sum(refunds), line.line_total)
        self.assertEqual(Variant.objects.get(pk=variant.pk).stock_quantity, 5)


class ExchangeTests(TestCase):

    def test_exchange_moves_stock_and_shows_difference(self):
        cashier = create_cashier()
        client = api_client(cashier)

        product = create_product(sizes=('M', 'L'), price='250000')
        medium = product.variants.get(size__name='M')
        large = product.variants.get(size__name='L')

        receive_stock(medium, 3, '150000')
        receive_stock(large, 3, '150000')

        sale = create_sale(
            user=cashier,
            lines=[{'variant': medium, 'quantity': 1, 'unit_price': Decimal('250000')}],
            cash_amount=Decimal('250000'),
        )
        line = sale.lines.get()

        response = client.post(
            '/api/exchanges/',
            {
                'sale': sale.pk,
                'items': [{'sale_line': line.pk, 'quantity': 1}],
                'lines': [{'variant': large.pk, 'quantity': 1, 'unit_price': '300000'}],
                'refund_method': 'cash',
                'cash_amount': '300000',
            },
            format='json',
        )

        self.assertEqual(response.status_code, 201, response.content)

        body = response.json()
        self.assertEqual(Decimal(body['difference']), Decimal('50000.00'))

        self.assertEqual(Variant.objects.get(pk=medium.pk).stock_quantity, 3)
        self.assertEqual(Variant.objects.get(pk=large.pk).stock_quantity, 2)


class VoidTests(TestCase):

    def setUp(self):
        self.admin = create_admin()
        self.cashier = create_cashier()
        self.variant = create_product(price='250000').variants.get()
        receive_stock(self.variant, 5, '150000')

    def _sell(self):
        return create_sale(
            user=self.cashier,
            lines=[{'variant': self.variant, 'quantity': 1, 'unit_price': Decimal('250000')}],
            cash_amount=Decimal('250000'),
        )

    def test_admin_can_void_today(self):
        sale = self._sell()

        response = api_client(self.admin).post(f'/api/sales/{sale.pk}/void/')

        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()['status'], 'voided')
        self.assertEqual(Variant.objects.get(pk=self.variant.pk).stock_quantity, 5)

    def test_cashier_cannot_void(self):
        sale = self._sell()

        response = api_client(self.cashier).post(f'/api/sales/{sale.pk}/void/')

        self.assertEqual(response.status_code, 403)
        self.assertEqual(Sale.objects.get(pk=sale.pk).status, Sale.Status.COMPLETED)

    def test_yesterdays_sale_cannot_be_voided(self):
        """Kunlik kassa yopilgan — eski chek uchun qaytarish ishlatiladi."""
        with freeze_time('2026-06-15 10:00:00+05:00'):
            sale = self._sell()

        with freeze_time('2026-06-16 09:00:00+05:00'):
            response = api_client(self.admin).post(f'/api/sales/{sale.pk}/void/')

        self.assertEqual(response.status_code, 400)
        self.assertIn('sotilgan kuni', ' '.join(response.json()['detail']))

    def test_sale_with_return_cannot_be_voided(self):
        sale = self._sell()
        create_return(
            sale=sale,
            items=[{'sale_line': sale.lines.get(), 'quantity': 1}],
            refund_method=SaleReturn.RefundMethod.CASH,
            user=self.cashier,
        )

        with self.assertRaises(ValidationError):
            void_sale(sale, user=self.admin)


class LocalDayTests(TestCase):

    def test_sale_at_2330_belongs_to_local_day(self):
        """Toshkent vaqti bilan 23:30 — o'sha kunning hisobotida."""
        cashier = create_cashier()
        variant = create_product(price='100000').variants.get()
        receive_stock(variant, 5, '40000')

        with freeze_time('2026-06-15 23:30:00+05:00'):
            sale = create_sale(
                user=cashier,
                lines=[{'variant': variant, 'quantity': 1, 'unit_price': Decimal('100000')}],
                cash_amount=Decimal('100000'),
            )

            self.assertEqual(timezone.localdate(), timezone.localdate(sale.created_at))

        from apps.reports.services import sales_report

        june_15 = timezone.datetime(2026, 6, 15).date()
        june_16 = timezone.datetime(2026, 6, 16).date()

        self.assertEqual(sales_report(june_15, june_15)['revenue'], Decimal('100000.00'))
        self.assertEqual(sales_report(june_16, june_16)['revenue'], Decimal('0'))


class ConcurrentSaleTests(TransactionTestCase):
    """Oxirgi donani ikki kassir bir vaqtda sotmoqchi bo'lsa."""

    reset_sequences = True

    def test_only_one_of_two_parallel_sales_succeeds(self):
        cashier = create_cashier()
        variant = create_product(price='250000').variants.get()
        receive_stock(variant, 1, '150000')

        results = []

        def sell():
            try:
                create_sale(
                    user=cashier,
                    lines=[
                        {'variant': variant, 'quantity': 1, 'unit_price': Decimal('250000')}
                    ],
                    cash_amount=Decimal('250000'),
                )
                results.append('ok')
            except ValidationError:
                results.append('rad etildi')
            finally:
                connections.close_all()

        threads = [Thread(target=sell) for _ in range(2)]

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join()

        self.assertEqual(results.count('ok'), 1, results)
        self.assertEqual(results.count('rad etildi'), 1, results)
        self.assertEqual(Variant.objects.get(pk=variant.pk).stock_quantity, 0)
        self.assertEqual(Sale.objects.count(), 1)
