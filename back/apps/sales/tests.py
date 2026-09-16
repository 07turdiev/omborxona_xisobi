"""Kassa testlari: sotuv, qaytarish, almashtirish, bekor qilish."""

from decimal import Decimal
from threading import Thread
from uuid import uuid4

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
from apps.reports.services import sales_report
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

        june_15 = timezone.datetime(2026, 6, 15).date()
        june_16 = timezone.datetime(2026, 6, 16).date()

        self.assertEqual(sales_report(june_15, june_15)['revenue'], Decimal('100000.00'))
        self.assertEqual(sales_report(june_16, june_16)['revenue'], Decimal('0'))


class IdempotencyTests(TestCase):
    """Tugma ikki marta bosilsa, ikkinchi hujjat yaratilmaydi."""

    def setUp(self):
        self.cashier = create_cashier()
        self.client_cashier = api_client(self.cashier)

        product = create_product(sizes=('M', 'L'), price='250000')
        self.medium = product.variants.get(size__name='M')
        self.large = product.variants.get(size__name='L')

        receive_stock(self.medium, 5, '150000')
        receive_stock(self.large, 5, '150000')

    def test_repeated_sale_returns_the_same_receipt(self):
        payload = {
            'lines': [{'variant': self.medium.pk, 'quantity': 1, 'unit_price': '250000'}],
            'cash_amount': '250000',
            'request_key': str(uuid4()),
        }

        first = self.client_cashier.post('/api/sales/', payload, format='json')
        second = self.client_cashier.post('/api/sales/', payload, format='json')

        self.assertEqual(first.status_code, 201, first.content)
        self.assertEqual(second.status_code, 200, second.content)
        self.assertEqual(first.json()['id'], second.json()['id'])
        self.assertEqual(first.json()['number'], second.json()['number'])

        self.assertEqual(Sale.objects.count(), 1)
        # Tovar bir marta chiqadi
        self.assertEqual(Variant.objects.get(pk=self.medium.pk).stock_quantity, 4)

    def test_repeated_return_returns_the_same_document(self):
        sale = create_sale(
            user=self.cashier,
            lines=[{'variant': self.medium, 'quantity': 2, 'unit_price': Decimal('250000')}],
            cash_amount=Decimal('500000'),
        )

        payload = {
            'sale': sale.pk,
            'items': [{'sale_line': sale.lines.get().pk, 'quantity': 1}],
            'refund_method': 'cash',
            'request_key': str(uuid4()),
        }

        first = self.client_cashier.post('/api/returns/', payload, format='json')
        second = self.client_cashier.post('/api/returns/', payload, format='json')

        self.assertEqual(first.status_code, 201, first.content)
        self.assertEqual(second.status_code, 200, second.content)
        self.assertEqual(first.json()['id'], second.json()['id'])

        self.assertEqual(SaleReturn.objects.count(), 1)
        self.assertEqual(Variant.objects.get(pk=self.medium.pk).stock_quantity, 4)

    def test_repeated_exchange_returns_the_same_pair(self):
        sale = create_sale(
            user=self.cashier,
            lines=[{'variant': self.medium, 'quantity': 1, 'unit_price': Decimal('250000')}],
            cash_amount=Decimal('250000'),
        )

        payload = {
            'sale': sale.pk,
            'items': [{'sale_line': sale.lines.get().pk, 'quantity': 1}],
            'lines': [{'variant': self.large.pk, 'quantity': 1, 'unit_price': '300000'}],
            'refund_method': 'cash',
            'cash_amount': '300000',
            'request_key': str(uuid4()),
        }

        first = self.client_cashier.post('/api/exchanges/', payload, format='json')
        second = self.client_cashier.post('/api/exchanges/', payload, format='json')

        self.assertEqual(first.status_code, 201, first.content)
        self.assertEqual(second.status_code, 200, second.content)
        self.assertEqual(first.json()['sale']['id'], second.json()['sale']['id'])
        self.assertEqual(
            first.json()['sale_return']['id'], second.json()['sale_return']['id']
        )

        # Bitta sotuv (asl chek + almashtirish) va bitta qaytarish
        self.assertEqual(Sale.objects.count(), 2)
        self.assertEqual(SaleReturn.objects.count(), 1)
        self.assertEqual(Variant.objects.get(pk=self.large.pk).stock_quantity, 4)


class CashierReceiptAccessTests(TestCase):
    """Kassir ro'yxatda faqat o'zining bugungi cheklarini ko'radi."""

    def setUp(self):
        self.cashier = create_cashier('kassir_bir')
        self.other = create_cashier('kassir_ikki')
        self.admin = create_admin()

        self.variant = create_product(price='100000').variants.get()
        receive_stock(self.variant, 20, '40000')

    def _sell(self, user):
        return create_sale(
            user=user,
            lines=[{'variant': self.variant, 'quantity': 1, 'unit_price': Decimal('100000')}],
            cash_amount=Decimal('100000'),
        )

    def test_list_shows_only_own_receipts_from_today(self):
        mine = self._sell(self.cashier)
        theirs = self._sell(self.other)

        with freeze_time('2026-06-15 10:00:00+05:00'):
            yesterday = self._sell(self.cashier)

        numbers = {
            row['number']
            for row in api_client(self.cashier).get('/api/sales/').json()['results']
        }

        self.assertIn(mine.number, numbers)
        self.assertNotIn(theirs.number, numbers)
        self.assertNotIn(yesterday.number, numbers)

    def test_cashier_can_find_any_receipt_by_number(self):
        """Qaytarish uchun: chekdagi raqam bo'yicha istalgan chek topiladi."""
        theirs = self._sell(self.other)

        with freeze_time('2026-06-15 10:00:00+05:00'):
            old = self._sell(self.cashier)

        client = api_client(self.cashier)

        for sale in (theirs, old):
            response = client.get(f'/api/sales/?number={sale.number}')

            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()['count'], 1, sale.number)
            self.assertEqual(response.json()['results'][0]['number'], sale.number)

    def test_admin_sees_every_receipt(self):
        mine = self._sell(self.cashier)
        theirs = self._sell(self.other)

        numbers = {
            row['number']
            for row in api_client(self.admin).get('/api/sales/').json()['results']
        }

        self.assertEqual(numbers, {mine.number, theirs.number})


class DrawerCashTests(TestCase):
    """Kun oxirida kassadagi naqd hisobotdagi naqd bilan bir xil bo'lishi kerak."""

    def test_cash_matches_after_card_sale_cash_return_and_exchange(self):
        cashier = create_cashier()
        client = api_client(cashier)

        product = create_product(sizes=('M', 'L'), price='200000')
        medium = product.variants.get(size__name='M')
        large = product.variants.get(size__name='L')

        receive_stock(medium, 5, '100000')
        receive_stock(large, 5, '100000')

        # 1) Karta bilan sotuv — kassaga naqd tushmaydi
        card_sale = create_sale(
            user=cashier,
            lines=[{'variant': medium, 'quantity': 1, 'unit_price': Decimal('200000')}],
            card_amount=Decimal('200000'),
        )

        # 2) Naqd sotuv va uni to'liq qaytarish — kassa nolga qaytadi
        cash_sale = create_sale(
            user=cashier,
            lines=[{'variant': medium, 'quantity': 1, 'unit_price': Decimal('150000')}],
            cash_amount=Decimal('150000'),
        )
        create_return(
            sale=cash_sale,
            items=[{'sale_line': cash_sale.lines.get(), 'quantity': 1}],
            refund_method=SaleReturn.RefundMethod.CASH,
            user=cashier,
        )

        # 3) Almashtirish: 200 000 lik tovar qaytdi, 250 000 lik olindi.
        #    Kassir mijozdan faqat farqni — 50 000 — naqd oladi.
        exchange = client.post(
            '/api/exchanges/',
            {
                'sale': card_sale.pk,
                'items': [{'sale_line': card_sale.lines.get().pk, 'quantity': 1}],
                'lines': [{'variant': large.pk, 'quantity': 1, 'unit_price': '250000'}],
                'refund_method': 'cash',
                'cash_amount': '250000',
                'request_key': str(uuid4()),
            },
            format='json',
        )

        self.assertEqual(exchange.status_code, 201, exchange.content)
        self.assertEqual(Decimal(exchange.json()['difference']), Decimal('50000.00'))

        # Kassadagi haqiqiy naqd: sotuvlardagi naqd − naqd qaytarishlar
        drawer = sum(
            sale.cash_amount for sale in Sale.objects.filter(status=Sale.Status.COMPLETED)
        ) - sum(
            item.total
            for item in SaleReturn.objects.filter(
                refund_method=SaleReturn.RefundMethod.CASH
            )
        )

        today = timezone.localdate()
        report = sales_report(today, today)

        self.assertEqual(drawer, Decimal('50000.00'))
        self.assertEqual(report['payments']['cash'], drawer)
        self.assertEqual(report['payments']['card'], Decimal('200000.00'))

        # Qoldiq ham to'g'ri: M — 5 ta joyida, L — bittasi sotildi
        self.assertEqual(Variant.objects.get(pk=medium.pk).stock_quantity, 5)
        self.assertEqual(Variant.objects.get(pk=large.pk).stock_quantity, 4)


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
