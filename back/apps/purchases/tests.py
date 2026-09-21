"""Kirim testlari: tasdiqlash, bekor qilish va ta'minotchi balansi."""

from decimal import Decimal

from django.test import TestCase

from apps.catalog.models import Variant
from apps.core.factories import (
    api_client,
    create_admin,
    create_cashier,
    create_product,
    receive_stock,
)
from apps.inventory.models import MovementReason, StockMovement
from apps.purchases.models import Purchase, Supplier
from apps.purchases.services import supplier_balance
from apps.sales.services import create_sale


class PurchaseFlowTests(TestCase):

    def setUp(self):
        self.admin = create_admin()
        self.client_admin = api_client(self.admin)
        self.variant = create_product().variants.get()
        self.supplier = Supplier.objects.create(name='Toshkent ulgurji')

    def _create_purchase(self, quantity=5, unit_cost='150000', supplier=True):
        return self.client_admin.post(
            '/api/purchases/',
            {
                'date': '2026-06-10',
                'supplier': self.supplier.pk if supplier else None,
                'lines': [
                    {'variant': self.variant.pk, 'quantity': quantity, 'unit_cost': unit_cost}
                ],
            },
            format='json',
        )

    def test_confirm_adds_stock_and_total(self):
        created = self._create_purchase()
        self.assertEqual(created.status_code, 201, created.content)

        body = created.json()
        self.assertEqual(body['status'], 'draft')
        self.assertEqual(Decimal(body['total']), Decimal('750000.00'))
        self.assertTrue(body['number'].startswith('KIR-'))

        confirmed = self.client_admin.post(f'/api/purchases/{body["id"]}/confirm/')

        self.assertEqual(confirmed.status_code, 200, confirmed.content)
        self.assertEqual(confirmed.json()['status'], 'confirmed')
        self.assertEqual(Variant.objects.get(pk=self.variant.pk).stock_quantity, 5)

    def test_purchase_without_supplier_is_allowed(self):
        """Do'kon ochilishida javondagi tovar ta'minotchisiz kiritiladi."""
        created = self._create_purchase(supplier=False)

        self.assertEqual(created.status_code, 201, created.content)
        self.assertIsNone(created.json()['supplier'])

        self.client_admin.post(f'/api/purchases/{created.json()["id"]}/confirm/')

        self.assertEqual(Variant.objects.get(pk=self.variant.pk).stock_quantity, 5)

    def test_confirmed_purchase_cannot_be_edited(self):
        created = self._create_purchase()
        purchase_id = created.json()['id']
        self.client_admin.post(f'/api/purchases/{purchase_id}/confirm/')

        response = self.client_admin.patch(
            f'/api/purchases/{purchase_id}/', {'note': 'yangi'}, format='json'
        )

        self.assertEqual(response.status_code, 400)

    def test_cancel_returns_stock_with_reverse_movements(self):
        created = self._create_purchase()
        purchase_id = created.json()['id']
        self.client_admin.post(f'/api/purchases/{purchase_id}/confirm/')

        cancelled = self.client_admin.post(f'/api/purchases/{purchase_id}/cancel/')

        self.assertEqual(cancelled.status_code, 200, cancelled.content)
        self.assertEqual(cancelled.json()['status'], 'cancelled')
        self.assertEqual(Variant.objects.get(pk=self.variant.pk).stock_quantity, 0)

        # Yozuvlar o'chirilmaydi: kirim + teskari yozuv
        self.assertEqual(StockMovement.objects.count(), 2)
        self.assertTrue(
            StockMovement.objects.filter(reason=MovementReason.PURCHASE_CANCEL).exists()
        )

    def test_cancel_is_blocked_when_stock_already_sold(self):
        created = self._create_purchase(quantity=2)
        purchase_id = created.json()['id']
        self.client_admin.post(f'/api/purchases/{purchase_id}/confirm/')

        create_sale(
            user=self.admin,
            lines=[{'variant': self.variant, 'quantity': 2, 'unit_price': Decimal('250000')}],
            cash_amount=Decimal('500000'),
        )

        response = self.client_admin.post(f'/api/purchases/{purchase_id}/cancel/')

        self.assertEqual(response.status_code, 400)
        self.assertIn('yetarli emas', ' '.join(response.json()['detail']))

        # Hech narsa o'zgarmadi: kirim tasdiqlangan holatda qoladi
        self.assertEqual(
            Purchase.objects.get(pk=purchase_id).status, Purchase.Status.CONFIRMED
        )
        self.assertEqual(Variant.objects.get(pk=self.variant.pk).stock_quantity, 0)

    def test_cashier_cannot_see_purchases(self):
        response = api_client(create_cashier()).get('/api/purchases/')

        self.assertEqual(response.status_code, 403)


class SupplierBalanceTests(TestCase):

    def setUp(self):
        self.admin = create_admin()
        self.client_admin = api_client(self.admin)
        self.supplier = Supplier.objects.create(name='Andijon tekstil')
        self.variant = create_product().variants.get()

    def test_balance_counts_purchases_payments_and_ignores_supplierless(self):
        purchase = receive_stock(
            self.variant, 10, '100000', user=self.admin, supplier=self.supplier
        )
        purchase.amount_paid = Decimal('300000')
        purchase.save(update_fields=['amount_paid'])

        # Ta'minotchisiz kirim balansga tushmaydi
        receive_stock(self.variant, 5, '90000', user=self.admin)

        self.assertEqual(supplier_balance(self.supplier), Decimal('700000.00'))

        self.client_admin.post(
            '/api/supplier-payments/',
            {'supplier': self.supplier.pk, 'date': '2026-06-12', 'amount': '200000'},
            format='json',
        )

        self.assertEqual(supplier_balance(self.supplier), Decimal('500000.00'))

    def test_purchase_debt_only_for_supplier_and_not_cancelled(self):
        """Qarz faqat ta'minotchili va bekor qilinmagan kirimda bo'ladi."""
        purchase = receive_stock(
            self.variant, 4, '200000', user=self.admin, supplier=self.supplier
        )
        purchase.amount_paid = Decimal('300000')
        purchase.save(update_fields=['amount_paid'])

        self.assertEqual(purchase.debt, Decimal('500000.00'))

        # Boshlang'ich qoldiq — hech kimga qarz emas
        own_stock = receive_stock(self.variant, 4, '200000', user=self.admin)

        self.assertEqual(own_stock.debt, Decimal('0'))

        cancelled = self.client_admin.post(f'/api/purchases/{purchase.pk}/cancel/')

        self.assertEqual(cancelled.status_code, 200, cancelled.content)
        self.assertEqual(Decimal(cancelled.json()['debt']), Decimal('0'))
        self.assertEqual(Purchase.objects.get(pk=purchase.pk).debt, Decimal('0'))

    def test_purchase_list_shows_no_debt_without_supplier(self):
        receive_stock(self.variant, 2, '100000', user=self.admin)

        rows = self.client_admin.get('/api/purchases/').json()['results']

        self.assertEqual(Decimal(rows[0]['debt']), Decimal('0'))

    def test_supplier_list_shows_balance(self):
        receive_stock(self.variant, 1, '50000', user=self.admin, supplier=self.supplier)

        response = self.client_admin.get('/api/suppliers/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(Decimal(response.json()['results'][0]['balance']), Decimal('50000.00'))
