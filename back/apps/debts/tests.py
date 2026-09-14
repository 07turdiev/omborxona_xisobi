"""Qarzga sotuv va qarz to'lovlari testlari.

Hammasi haqiqiy oqim orqali: kirim hujjati → tasdiqlash → qarzga sotuv →
tasdiqlash → to'lov. Qarzni to'g'ridan-to'g'ri yaratish qarz va sotuv
o'rtasidagi bog'liqlikni (summa, ustama, bekor qilish) tekshirmasdi.
"""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

from django.db import DatabaseError, transaction
from django.test import TestCase, tag
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.audit.models import AuditEvent
from apps.catalog.models import Category, Product, Variant
from apps.core.tenancy import tenant_context
from apps.debts.models import Debt, DebtPayment
from apps.partners.models import Partner
from apps.tenants.models import Membership, Tenant
from apps.users.models import User
from apps.warehouse.models import Warehouse

Role = Membership.Role
D = Decimal


def money(value) -> Decimal:
    """API javobidagi summa — satr yoki son bo'lishi mumkin."""
    return Decimal(str(value))


class DebtTestBase(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.tenant = Tenant.objects.create(
            name='Do\'kon', slug='debt-test', debt_default_days=30
        )

        with tenant_context(cls.tenant.id):
            cls.shop = Warehouse.objects.create(
                tenant=cls.tenant, code='SHOP', name='Do\'kon',
                purpose=Warehouse.Purpose.RETAIL,
            )
            category = Category.objects.create(tenant=cls.tenant, name='Sement')
            product = Product.objects.create(
                tenant=cls.tenant, category=category, name='Sement M400', base_unit='qop'
            )
            cls.variant = Variant.objects.create(
                tenant=cls.tenant, product=product, sku='CEM-1',
                purchase_price=D('1000'), sale_price=D('1300'),
            )
            cls.partner = Partner.objects.create(
                tenant=cls.tenant, name='Qurilish MChJ', is_customer=True,
                phone='+998901112233',
            )

    _counter = 0

    def client_for(self, role, permissions=None):
        DebtTestBase._counter += 1
        user = User.objects.create_user(username=f'debt{DebtTestBase._counter}', password='x')
        Membership.objects.create(
            tenant=self.tenant, user=user, role=role, permissions=permissions
        )

        client = APIClient()
        client.credentials(
            HTTP_AUTHORIZATION=f'Bearer {RefreshToken.for_user(user).access_token}'
        )

        return client

    def setUp(self):
        self.owner = self.client_for(Role.OWNER)

        # Sotish uchun omborda tovar bo'lishi kerak: 100 qop, 1000 so'mdan
        purchase = self.owner.post('/api/documents/', {
            'kind': 'purchase',
            'warehouse': self.shop.pk,
            'items': [{'variant': self.variant.pk, 'quantity': '100', 'unit_price': '1000'}],
        }, format='json')
        self.assertEqual(purchase.status_code, 201, purchase.content)
        confirmed = self.owner.post(f"/api/documents/{purchase.json()['id']}/confirm/")
        self.assertEqual(confirmed.status_code, 200, confirmed.content)

    def sale(self, *, confirm=True, client=None, quantity='10', **fields):
        """Sotuv hujjati: 10 qop × 1300. Qaytaradi: (javob, hujjat_id, qarz)."""
        client = client or self.owner

        response = client.post('/api/documents/', {
            'kind': 'sale',
            'warehouse': self.shop.pk,
            'items': [{'variant': self.variant.pk, 'quantity': quantity, 'unit_price': '1300'}],
            **fields,
        }, format='json')

        if response.status_code != 201:
            return response, None, None

        document_id = response.json()['id']

        if confirm:
            confirmed = client.post(f'/api/documents/{document_id}/confirm/')
            self.assertEqual(confirmed.status_code, 200, confirmed.content)

        with tenant_context(self.tenant.id):
            debt = Debt.objects.filter(document_id=document_id).first()

        return response, document_id, debt

    def credit_sale(self, **fields):
        return self.sale(is_credit=True, partner=self.partner.pk, **fields)

    def pay(self, debt, amount, client=None, **extra):
        return (client or self.owner).post(
            f'/api/debts/{debt.pk}/pay/', {'amount': amount, **extra}, format='json'
        )

    def reload(self, debt) -> Debt:
        with tenant_context(self.tenant.id):
            return Debt.objects.get(pk=debt.pk)


@tag('debts')
class CreditSaleTests(DebtTestBase):

    def test_credit_sale_creates_debt_with_markup(self):
        _, _, debt = self.credit_sale(credit_markup_percent='10')

        self.assertIsNotNone(debt)
        self.assertEqual(debt.base_amount, D('13000.00'))
        self.assertEqual(debt.amount, D('14300.00'))
        self.assertEqual(debt.markup_amount, D('1300.00'))
        self.assertTrue(debt.number.startswith('QRZ-'))
        self.assertEqual(debt.customer_name, 'Qurilish MChJ')
        self.assertEqual(debt.customer_phone, '+998901112233')

    def test_due_date_defaults_to_tenant_setting(self):
        _, _, debt = self.credit_sale()

        self.assertEqual(debt.due_date, debt.issued_date + timedelta(days=30))

    def test_markup_is_revenue_and_profit(self):
        """Ustama — do'kon daromadi: tushum va foydada ko'rinishi kerak."""
        _, document_id, _ = self.credit_sale(credit_markup_percent='10')

        data = self.owner.get(f'/api/documents/{document_id}/').json()

        self.assertEqual(money(data['total_amount']), D('14300.00'))
        # Tannarx FIFO bo'yicha: 10 × 1000
        self.assertEqual(money(data['profit']), D('4300.00'))
        self.assertEqual(data['debt']['number'], self.reload_first_debt().number)

    def reload_first_debt(self):
        with tenant_context(self.tenant.id):
            return Debt.objects.get()

    def test_plain_sale_has_no_debt(self):
        _, _, debt = self.sale()

        self.assertIsNone(debt)

    def test_credit_sale_needs_customer(self):
        response, _, _ = self.sale(is_credit=True)

        self.assertEqual(response.status_code, 400)
        self.assertIn('customer_name', response.json())

    def test_retail_customer_by_name_and_phone(self):
        _, _, debt = self.sale(
            is_credit=True, customer_name='Aziz Karimov', customer_phone='+998935556677',
            customer_document='AB1234567',
        )

        self.assertEqual(debt.customer_type, 'retail')
        self.assertEqual(debt.customer_document, 'AB1234567')

    def test_purchase_cannot_be_credit(self):
        response = self.owner.post('/api/documents/', {
            'kind': 'purchase', 'warehouse': self.shop.pk, 'is_credit': True,
            'partner': self.partner.pk,
            'items': [{'variant': self.variant.pk, 'quantity': '1', 'unit_price': '1000'}],
        }, format='json')

        self.assertEqual(response.status_code, 400)

    def test_deferred_payment_not_allowed_for_sale(self):
        response, _, _ = self.sale(payment_method='deferred')

        self.assertEqual(response.status_code, 400)
        self.assertIn('payment_method', response.json())

    def test_markup_change_on_draft_recalculates_lines(self):
        response, document_id, _ = self.credit_sale(confirm=False)
        self.assertEqual(money(response.json()['total_amount']), D('13000.00'))

        patched = self.owner.patch(
            f'/api/documents/{document_id}/', {'credit_markup_percent': '20'}, format='json'
        )

        self.assertEqual(patched.status_code, 200, patched.content)
        self.assertEqual(money(patched.json()['total_amount']), D('15600.00'))


@tag('debts')
class PaymentTests(DebtTestBase):

    def test_partial_then_full_payment(self):
        _, _, debt = self.credit_sale(credit_markup_percent='10')

        first = self.pay(debt, '5000')
        self.assertEqual(first.status_code, 200, first.content)
        self.assertEqual(money(first.json()['remaining']), D('9300.00'))
        self.assertEqual(first.json()['status'], 'active')

        second = self.pay(debt, '9300', method='card')
        self.assertEqual(second.json()['status'], 'paid')
        self.assertEqual(len(second.json()['payments']), 2)
        self.assertIsNotNone(self.reload(debt).paid_at)

        self.assertEqual(self.pay(debt, '1').status_code, 400)

    def test_overpayment_rejected(self):
        _, _, debt = self.credit_sale()

        self.assertEqual(self.pay(debt, '20000').status_code, 400)
        self.assertEqual(self.reload(debt).paid_amount, D('0'))

    def test_duplicate_request_counts_once(self):
        """Tugma ikki marta bosilsa ham pul bir marta yoziladi — tarixda ham."""
        _, _, debt = self.credit_sale()

        self.pay(debt, '5000', request_key='oyna-1')
        repeated = self.pay(debt, '5000', request_key='oyna-1')

        self.assertEqual(repeated.status_code, 200)
        self.assertEqual(self.reload(debt).paid_amount, D('5000.00'))

        with tenant_context(self.tenant.id):
            self.assertEqual(DebtPayment.objects.filter(debt=debt).count(), 1)
            self.assertEqual(
                AuditEvent.objects.filter(object_type='debt', action='payment').count(), 1
            )

    def test_payment_record_is_immutable_in_database(self):
        _, _, debt = self.credit_sale()
        self.pay(debt, '1000')

        with tenant_context(self.tenant.id):
            with self.assertRaises(DatabaseError), transaction.atomic():
                DebtPayment.objects.filter(debt=debt).update(amount=D('1'))

    def test_cashier_can_pay_storekeeper_cannot_see(self):
        _, _, debt = self.credit_sale()

        cashier = self.client_for(Role.SALESPERSON)
        storekeeper = self.client_for(Role.STOREKEEPER)

        self.assertEqual(self.pay(debt, '1000', client=cashier).status_code, 200)
        self.assertEqual(storekeeper.get('/api/debts/').status_code, 403)


@tag('debts')
class OverdueAndCancelTests(DebtTestBase):

    def test_overdue_filter_and_summary(self):
        past = (timezone.localdate() - timedelta(days=5)).isoformat()
        self.credit_sale(due_date=past)
        self.credit_sale()  # muddati hali o'tmagan

        overdue = self.owner.get('/api/debts/', {'status': 'overdue'}).json()['results']
        summary = self.owner.get('/api/debts/summary/').json()

        self.assertEqual(len(overdue), 1)
        self.assertEqual(overdue[0]['overdue_days'], 5)
        self.assertEqual(overdue[0]['display_status'], 'overdue')
        self.assertEqual(summary['active_count'], 2)
        self.assertEqual(summary['overdue_count'], 1)
        self.assertEqual(money(summary['overdue_amount']), D('13000.00'))

    def test_cannot_cancel_sale_with_payment(self):
        """Olingan pul hech narsaga bog'lanmay qolmasligi kerak."""
        _, document_id, debt = self.credit_sale()
        self.pay(debt, '1000')

        response = self.owner.post(f'/api/documents/{document_id}/cancel/')

        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.reload(debt).status, Debt.Status.ACTIVE)

    def test_cancel_sale_without_payment_cancels_debt(self):
        _, document_id, debt = self.credit_sale()

        response = self.owner.post(f'/api/documents/{document_id}/cancel/')

        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(self.reload(debt).status, Debt.Status.CANCELLED)
