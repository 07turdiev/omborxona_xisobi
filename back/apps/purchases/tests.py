"""Kirim testlari: tasdiqlash, bekor qilish va ta'minotchi balansi."""

from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from apps.catalog.models import Category, Color, Size, Variant
from apps.inventory.models import Location
from apps.inventory.services import create_transfer
from apps.core.factories import (
    api_client,
    create_admin,
    create_cashier,
    create_product,
    receive_stock,
)
from apps.inventory.models import MovementReason, StockMovement, VariantStock
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

        # Tovar zalga chiqarildi va sotildi — endi ombordan qaytarib
        # bo'lmaydi, chunki u yerda qolmagan
        create_transfer(
            source=Location.warehouse(),
            target=Location.shop(),
            lines=[{'variant': self.variant, 'quantity': 2}],
            user=self.admin,
        )

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
        # Bekor qilinadigan kirim omborda qoladi: zalga chiqarilgan tovarni
        # ombordan qaytarib bo'lmaydi
        purchase = receive_stock(
            self.variant,
            4,
            '200000',
            user=self.admin,
            supplier=self.supplier,
            location=Location.warehouse(),
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


class PurchaseReceivingTests(TestCase):
    """Kirim ekranidan model qabul qilish: bitta tannarx, yangi sotuv narxi.

    Do'konga tovar shtrix-kodsiz keladi, shuning uchun kirim ekrani
    modelning o'lcham × rang katakchasini to'ldirib yuboradi: bitta
    tannarx hamma qatorga tushadi, kerak bo'lsa qatorda o'zgartiriladi.
    """

    def setUp(self):
        self.admin = create_admin()
        self.client_admin = api_client(self.admin)

        self.product = create_product(
            name='Bahorgi kurtka', price='400000', sizes=('S', 'M'), colors=('Oq',)
        )
        self.variants = list(self.product.variants.order_by('pk'))

    def _post(self, lines):
        return self.client_admin.post(
            '/api/purchases/',
            {'date': '2026-06-10', 'supplier': None, 'lines': lines},
            format='json',
        )

    def test_one_cost_for_every_line_and_line_override(self):
        first, second = self.variants

        created = self._post([
            {'variant': first.pk, 'quantity': 3, 'unit_cost': '200000'},
            # Shu qatorda tannarx boshqacha — modelnikini bosib o'tadi
            {'variant': second.pk, 'quantity': 2, 'unit_cost': '250000'},
        ])

        self.assertEqual(created.status_code, 201, created.content)

        body = created.json()
        costs = {line['variant']: Decimal(line['unit_cost']) for line in body['lines']}

        self.assertEqual(costs[first.pk], Decimal('200000.00'))
        self.assertEqual(costs[second.pk], Decimal('250000.00'))
        self.assertEqual(Decimal(body['total']), Decimal('1100000.00'))

    def test_new_sale_price_is_saved_only_on_confirm(self):
        created = self._post([
            {
                'variant': variant.pk,
                'quantity': 2,
                'unit_cost': '200000',
                'new_sale_price': '320000',
            }
            for variant in self.variants
        ])

        self.assertEqual(created.status_code, 201, created.content)

        # Qoralama — do'konda hali eski narx ishlaydi
        self.product.refresh_from_db()
        self.assertEqual(self.product.sale_price, Decimal('400000.00'))

        confirmed = self.client_admin.post(f'/api/purchases/{created.json()["id"]}/confirm/')

        self.assertEqual(confirmed.status_code, 200, confirmed.content)

        self.product.refresh_from_db()
        self.assertEqual(self.product.sale_price, Decimal('320000.00'))

        for variant in self.variants:
            variant.refresh_from_db()
            self.assertEqual(variant.stock_quantity, 2)
            # Variantning o'z narxi yo'q — model narxi ishlaydi
            self.assertEqual(variant.price, Decimal('320000.00'))

    def test_purchase_without_new_price_leaves_product_price(self):
        created = self._post([
            {'variant': self.variants[0].pk, 'quantity': 1, 'unit_cost': '200000'}
        ])

        self.client_admin.post(f'/api/purchases/{created.json()["id"]}/confirm/')

        self.product.refresh_from_db()
        self.assertEqual(self.product.sale_price, Decimal('400000.00'))

    def test_line_carries_product_and_price_for_the_grid_and_labels(self):
        """Qoralamani qayta ochish va yorliq uchun qo'shimcha so'rov kerak emas."""
        created = self._post([
            {'variant': self.variants[0].pk, 'quantity': 1, 'unit_cost': '200000'}
        ])

        line = created.json()['lines'][0]

        self.assertEqual(line['product'], self.product.pk)
        self.assertEqual(Decimal(line['price']), Decimal('400000.00'))
        self.assertTrue(line['barcode'])

    def test_line_carries_size_and_color_for_the_grouped_grid(self):
        """Ochilgan hujjatda qatorlar model bo'yicha katakchaga yig'iladi."""
        created = self._post([
            {'variant': self.variants[0].pk, 'quantity': 1, 'unit_cost': '200000'}
        ])

        line = created.json()['lines'][0]

        self.assertEqual(line['size'], self.variants[0].size_id)
        self.assertEqual(line['size_name'], self.variants[0].size.name)
        self.assertEqual(line['color_name'], self.variants[0].color.name)

    def test_purchase_shows_who_created_it(self):
        """«Oxirgi kirimlar» jadvalidagi Xodim ustuni."""
        self.admin.first_name = 'Gulnora'
        self.admin.last_name = 'Karimova'
        self.admin.save(update_fields=['first_name', 'last_name'])

        created = self._post([
            {'variant': self.variants[0].pk, 'quantity': 1, 'unit_cost': '200000'}
        ])

        self.assertEqual(created.json()['created_by_name'], 'Gulnora Karimova')

    def test_zero_new_sale_price_is_rejected(self):
        response = self._post([
            {
                'variant': self.variants[0].pk,
                'quantity': 1,
                'unit_cost': '200000',
                'new_sale_price': '0',
            }
        ])

        self.assertEqual(response.status_code, 400, response.content)

    def test_draft_can_be_edited_and_confirmed_later(self):
        """Qoralama saqlanadi, keyin davom ettiriladi."""
        created = self._post([
            {'variant': self.variants[0].pk, 'quantity': 1, 'unit_cost': '200000'}
        ])
        purchase_id = created.json()['id']

        updated = self.client_admin.patch(
            f'/api/purchases/{purchase_id}/',
            {
                'lines': [
                    {'variant': variant.pk, 'quantity': 4, 'unit_cost': '210000'}
                    for variant in self.variants
                ]
            },
            format='json',
        )

        self.assertEqual(updated.status_code, 200, updated.content)
        self.assertEqual(len(updated.json()['lines']), 2)
        self.assertEqual(Decimal(updated.json()['total']), Decimal('1680000.00'))

        self.client_admin.post(f'/api/purchases/{purchase_id}/confirm/')

        for variant in self.variants:
            variant.refresh_from_db()
            self.assertEqual(variant.stock_quantity, 4)


class ProductFromPurchaseTests(TestCase):
    """Kirim ekranida yangi model yaratish: matritsa va skanerlangan kod."""

    def setUp(self):
        self.admin = create_admin()
        self.client_admin = api_client(self.admin)

        self.category = Category.objects.create(name='Kurtkalar')
        self.sizes = [
            Size.objects.create(name=name, position=index)
            for index, name in enumerate(('S', 'M', 'L'))
        ]
        self.colors = [
            Color.objects.create(name=name, hex_code='#808080') for name in ('Oq', 'Qora')
        ]

    def test_new_model_creates_the_whole_matrix(self):
        response = self.client_admin.post(
            '/api/products/',
            {
                'category': self.category.pk,
                'name': 'Yangi kurtka',
                'sale_price': '500000',
                'size_ids': [size.pk for size in self.sizes],
                'color_ids': [color.pk for color in self.colors],
            },
            format='json',
        )

        self.assertEqual(response.status_code, 201, response.content)

        variants = response.json()['variants']

        self.assertEqual(len(variants), 6)
        # Har variantning o'z shtrix-kodi bor — yorliq shu koddan chiqadi
        self.assertEqual(len({variant['barcode'] for variant in variants}), 6)

    def test_unknown_barcode_becomes_the_code_of_the_new_variant(self):
        scanned = '4780000123456'

        created = self.client_admin.post(
            '/api/products/',
            {'category': self.category.pk, 'name': 'Sumka', 'sale_price': '150000'},
            format='json',
        )

        self.assertEqual(created.status_code, 201, created.content)

        variants = created.json()['variants']
        self.assertEqual(len(variants), 1, 'o‘lchamsiz mahsulotda bitta variant bo‘ladi')

        response = self.client_admin.patch(
            f'/api/variants/{variants[0]["id"]}/', {'barcode': scanned}, format='json'
        )

        self.assertEqual(response.status_code, 200, response.content)

        found = self.client_admin.get('/api/variants/by-barcode/', {'code': scanned})

        self.assertEqual(found.status_code, 200)
        self.assertEqual(found.json()['product_name'], 'Sumka')


class PurchaseLocationTests(TestCase):
    """Kirim omborga ham, to'g'ridan-to'g'ri zalga ham tushishi mumkin."""

    def setUp(self):
        self.admin = create_admin()
        self.variant = create_product().variants.get()
        self.client = api_client(self.admin)

    def create(self, location=None) -> dict:
        payload = {
            'date': str(timezone.localdate()),
            'supplier': None,
            'lines': [
                {'variant': self.variant.pk, 'quantity': 4, 'unit_cost': '100000'}
            ],
        }

        if location is not None:
            payload['location'] = location.pk

        response = self.client.post('/api/purchases/', payload, format='json')

        self.assertEqual(response.status_code, 201, response.content)

        return response.json()

    def stock(self, location) -> int:
        row = VariantStock.objects.filter(variant=self.variant, location=location).first()

        return row.quantity if row else 0

    def test_without_a_location_it_goes_to_the_warehouse(self):
        purchase = self.create()

        self.assertEqual(purchase['location_name'], Location.warehouse().name)

        self.client.post(f'/api/purchases/{purchase["id"]}/confirm/')

        self.assertEqual(self.stock(Location.warehouse()), 4)
        self.assertEqual(self.stock(Location.shop()), 0)

    def test_goods_can_land_straight_on_the_shop_floor(self):
        """Kichik partiya ombordan o'tmay javonga qo'yiladi."""
        purchase = self.create(Location.shop())

        self.client.post(f'/api/purchases/{purchase["id"]}/confirm/')

        self.assertEqual(self.stock(Location.shop()), 4)
        self.assertEqual(self.stock(Location.warehouse()), 0)

    def test_cancelling_takes_it_back_from_the_same_place(self):
        purchase = self.create(Location.shop())

        self.client.post(f'/api/purchases/{purchase["id"]}/confirm/')
        response = self.client.post(f'/api/purchases/{purchase["id"]}/cancel/')

        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(self.stock(Location.shop()), 0)
