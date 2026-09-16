"""Hisobot testlari: sof tushum, tannarx, yo'qotish va sof foyda."""

from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from apps.core.factories import (
    api_client,
    create_admin,
    create_cashier,
    create_product,
    receive_stock,
)
from apps.expenses.models import Expense
from apps.inventory.services import create_write_off
from apps.reports.services import sales_report, stock_report, top_products
from apps.sales.models import SaleReturn
from apps.sales.services import create_return, create_sale


class SalesReportTests(TestCase):

    def setUp(self):
        self.admin = create_admin()
        self.cashier = create_cashier()
        self.today = timezone.localdate()

        self.variant = create_product(price='250000').variants.get()
        receive_stock(self.variant, 10, '150000', user=self.admin)

        # 2 dona sotildi, 10 % chegirma: 450 000, tannarx 300 000
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

    def report(self):
        return sales_report(self.today, self.today)

    def test_sale_numbers(self):
        report = self.report()

        self.assertEqual(report['revenue'], Decimal('450000.00'))
        self.assertEqual(report['receipts'], 1)
        self.assertEqual(report['discounts'], Decimal('50000.00'))
        self.assertEqual(report['cost'], Decimal('300000.00'))
        self.assertEqual(report['gross_profit'], Decimal('150000.00'))
        self.assertEqual(report['net_profit'], Decimal('150000.00'))
        self.assertEqual(report['payments']['cash'], Decimal('450000.00'))

    def test_return_reduces_revenue_and_cost(self):
        create_return(
            sale=self.sale,
            items=[{'sale_line': self.sale.lines.get(), 'quantity': 1}],
            refund_method=SaleReturn.RefundMethod.CASH,
            user=self.cashier,
        )

        report = self.report()

        self.assertEqual(report['returns'], Decimal('225000.00'))
        self.assertEqual(report['net_revenue'], Decimal('225000.00'))
        self.assertEqual(report['cost'], Decimal('150000.00'))
        self.assertEqual(report['gross_profit'], Decimal('75000.00'))
        self.assertEqual(report['payments']['cash'], Decimal('225000.00'))

    def test_write_off_counts_as_loss(self):
        create_write_off(
            variant=self.variant, quantity=1, reason='Buzilgan', user=self.admin
        )

        report = self.report()

        self.assertEqual(report['losses'], Decimal('150000.00'))
        self.assertEqual(report['net_profit'], Decimal('0.00'))

    def test_count_shortage_counts_as_loss(self):
        client = api_client(self.admin)

        created = client.post(
            '/api/stock-counts/',
            {
                'date': str(self.today),
                'lines': [{'variant': self.variant.pk, 'counted_quantity': 6}],
            },
            format='json',
        )
        client.post(f'/api/stock-counts/{created.json()["id"]}/confirm/')

        report = self.report()

        # 8 kutilgan, 6 topildi → 2 dona × 150 000
        self.assertEqual(report['losses'], Decimal('300000.00'))
        self.assertEqual(report['net_profit'], Decimal('-150000.00'))

    def test_expenses_reduce_net_profit(self):
        Expense.objects.create(
            date=self.today,
            category=Expense.Category.RENT,
            amount=Decimal('100000'),
            created_by=self.admin,
        )

        report = self.report()

        self.assertEqual(report['expenses'], Decimal('100000.00'))
        self.assertEqual(report['net_profit'], Decimal('50000.00'))

    def test_breakdowns(self):
        report = self.report()

        self.assertEqual(report['by_category'][0]['revenue'], Decimal('450000.00'))
        self.assertEqual(report['by_category'][0]['profit'], Decimal('150000.00'))
        self.assertEqual(report['by_cashier'][0]['name'], self.cashier.username)
        self.assertEqual(report['by_cashier'][0]['receipts'], 1)

    def test_top_products(self):
        rows = top_products(self.today, self.today)

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['quantity'], 2)
        self.assertEqual(rows[0]['profit'], Decimal('150000.00'))
        self.assertEqual(len(rows[0]['variants']), 1)


class StockReportTests(TestCase):

    def test_stock_value_at_cost_and_retail(self):
        admin = create_admin()
        variant = create_product(price='250000').variants.get()
        receive_stock(variant, 4, '150000', user=admin)

        report = stock_report()

        self.assertEqual(report['positions'], 1)
        self.assertEqual(report['units'], 4)
        self.assertEqual(report['cost_value'], Decimal('600000.00'))
        self.assertEqual(report['retail_value'], Decimal('1000000.00'))
        self.assertEqual(report['potential_profit'], Decimal('400000.00'))


class ReportAccessTests(TestCase):

    def test_admin_can_open_reports_and_export(self):
        client = api_client(create_admin())

        for url in ('/api/reports/dashboard/', '/api/reports/sales/', '/api/reports/stock/'):
            self.assertEqual(client.get(url).status_code, 200, url)

        export = client.get('/api/reports/sales/export/')

        self.assertEqual(export.status_code, 200)
        self.assertIn('spreadsheetml', export['Content-Type'])

    def test_cashier_cannot_open_reports(self):
        client = api_client(create_cashier())

        for url in ('/api/reports/dashboard/', '/api/reports/sales/', '/api/reports/stock/'):
            self.assertEqual(client.get(url).status_code, 403, url)
