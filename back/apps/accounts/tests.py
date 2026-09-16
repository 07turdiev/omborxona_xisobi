"""Rol testlari: kassir nimani ko'radi va nimani ko'rmaydi."""

from decimal import Decimal

from django.test import TestCase

from apps.core.factories import (
    PASSWORD,
    api_client,
    create_admin,
    create_cashier,
    create_product,
    receive_stock,
)
from apps.sales.models import SaleReturn
from apps.sales.services import create_return, create_sale

#: Kassir javobida umuman uchramasligi kerak bo'lgan kalitlar
FORBIDDEN_KEYS = {
    'average_cost',
    'unit_cost',
    'line_cost',
    'cost',
    'cost_value',
    'profit',
    'gross_profit',
    'net_profit',
    'purchase_price',
    'supplier',
    'supplier_name',
    'balance',
}


def find_forbidden(payload, path='') -> list[str]:
    """JSON ichidan taqiqlangan kalitlarni rekursiv izlaydi."""
    found = []

    if isinstance(payload, dict):
        for key, value in payload.items():
            if key in FORBIDDEN_KEYS:
                found.append(f'{path}.{key}')

            found += find_forbidden(value, f'{path}.{key}')

    elif isinstance(payload, list):
        for index, item in enumerate(payload):
            found += find_forbidden(item, f'{path}[{index}]')

    return found


class LoginTests(TestCase):

    def test_login_returns_token_and_me_shows_role(self):
        cashier = create_cashier()

        response = self.client.post(
            '/api/auth/login/',
            {'username': cashier.username, 'password': PASSWORD},
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 200, response.content)
        self.assertIn('access', response.json())

        me = api_client(cashier).get('/api/auth/me/')

        self.assertEqual(me.status_code, 200)
        self.assertEqual(me.json()['role'], 'cashier')


class CashierAccessTests(TestCase):
    """Kassirga yopiq bo'lim — 403, ochiq bo'limda tannarx ko'rinmaydi."""

    def setUp(self):
        self.admin = create_admin()
        self.cashier = create_cashier()
        self.client_cashier = api_client(self.cashier)

        self.product = create_product(price='250000')
        self.variant = self.product.variants.get()
        receive_stock(self.variant, 10, '150000', user=self.admin)

        self.sale = create_sale(
            user=self.cashier,
            lines=[{'variant': self.variant, 'quantity': 2, 'unit_price': Decimal('250000')}],
            cash_amount=Decimal('500000'),
        )
        self.sale_return = create_return(
            sale=self.sale,
            items=[{'sale_line': self.sale.lines.get(), 'quantity': 1}],
            refund_method=SaleReturn.RefundMethod.CASH,
            user=self.cashier,
        )

    def test_admin_only_sections_are_forbidden(self):
        for url in (
            '/api/purchases/',
            '/api/suppliers/',
            '/api/supplier-payments/',
            '/api/expenses/',
            '/api/movements/',
            '/api/stock-counts/',
            '/api/write-offs/',
            '/api/users/',
            '/api/reports/dashboard/',
            '/api/reports/sales/',
            '/api/reports/stock/',
            '/api/reports/suppliers/',
            '/api/reports/sales/export/',
        ):
            self.assertEqual(self.client_cashier.get(url).status_code, 403, url)

    def test_no_cost_or_profit_fields_anywhere(self):
        """Kassirga ochiq har bir manzil tekshiriladi."""
        urls = [
            '/api/auth/me/',
            '/api/settings/',
            '/api/categories/',
            '/api/sizes/',
            '/api/colors/',
            '/api/products/',
            f'/api/products/{self.product.pk}/',
            '/api/variants/',
            f'/api/variants/{self.variant.pk}/',
            f'/api/variants/by-barcode/?code={self.variant.barcode}',
            '/api/sales/',
            f'/api/sales/{self.sale.pk}/',
            '/api/returns/',
            f'/api/returns/{self.sale_return.pk}/',
        ]

        for url in urls:
            response = self.client_cashier.get(url)

            self.assertEqual(response.status_code, 200, f'{url}: {response.content}')

            leaked = find_forbidden(response.json(), url)
            self.assertEqual(leaked, [], f'{url} da yashirilishi kerak: {leaked}')

    def test_no_cost_fields_in_write_responses(self):
        sale_response = self.client_cashier.post(
            '/api/sales/',
            {
                'lines': [{'variant': self.variant.pk, 'quantity': 1, 'unit_price': '250000'}],
                'cash_amount': '250000',
            },
            format='json',
        )

        self.assertEqual(sale_response.status_code, 201, sale_response.content)
        self.assertEqual(find_forbidden(sale_response.json(), 'sale'), [])

        sale_id = sale_response.json()['id']
        line_id = sale_response.json()['lines'][0]['id']

        return_response = self.client_cashier.post(
            '/api/returns/',
            {
                'sale': sale_id,
                'items': [{'sale_line': line_id, 'quantity': 1}],
                'refund_method': 'cash',
            },
            format='json',
        )

        self.assertEqual(return_response.status_code, 201, return_response.content)
        self.assertEqual(find_forbidden(return_response.json(), 'return'), [])

    def test_admin_does_see_cost_and_profit(self):
        """Yashirish faqat kassirga tegishli."""
        response = api_client(self.admin).get(f'/api/sales/{self.sale.pk}/')

        body = response.json()

        self.assertEqual(response.status_code, 200)
        self.assertIn('profit', body)
        self.assertIn('unit_cost', body['lines'][0])
        self.assertEqual(Decimal(body['lines'][0]['unit_cost']), Decimal('150000.00'))


class UserManagementTests(TestCase):

    def setUp(self):
        self.admin = create_admin()
        self.client_admin = api_client(self.admin)

    def test_admin_creates_and_deactivates_cashier(self):
        created = self.client_admin.post(
            '/api/users/',
            {
                'username': 'yangi_kassir',
                'password': 'Yangi-Parol-2026',
                'role': 'cashier',
                'first_name': 'Dilnoza',
            },
            format='json',
        )

        self.assertEqual(created.status_code, 201, created.content)
        self.assertNotIn('password', created.json())

        user_id = created.json()['id']

        disabled = self.client_admin.patch(
            f'/api/users/{user_id}/', {'is_active': False}, format='json'
        )

        self.assertEqual(disabled.status_code, 200)
        self.assertFalse(disabled.json()['is_active'])

    def test_weak_password_is_rejected(self):
        response = self.client_admin.post(
            '/api/users/',
            {'username': 'zaif', 'password': '12345', 'role': 'cashier'},
            format='json',
        )

        self.assertEqual(response.status_code, 400)

    def test_admin_resets_password(self):
        cashier = create_cashier('kassir2')

        response = self.client_admin.post(
            f'/api/users/{cashier.pk}/set-password/',
            {'password': 'Boshqa-Parol-2026'},
            format='json',
        )

        self.assertEqual(response.status_code, 200, response.content)

        login = self.client.post(
            '/api/auth/login/',
            {'username': 'kassir2', 'password': 'Boshqa-Parol-2026'},
            content_type='application/json',
        )

        self.assertEqual(login.status_code, 200)

    def test_cashier_cannot_manage_users(self):
        response = api_client(create_cashier()).post(
            '/api/users/', {'username': 'x', 'password': 'Parol-2026-x', 'role': 'admin'},
            format='json',
        )

        self.assertEqual(response.status_code, 403)
