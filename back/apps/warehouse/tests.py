"""Ombor modeli, izolyatsiya va kirish huquqi testlari."""

from __future__ import annotations

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.core.tenancy import tenant_context
from apps.tenants.models import Membership, Tenant
from apps.warehouse.models import Warehouse, WarehouseAccess

User = get_user_model()


class WarehouseModelTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.tenant_a = Tenant.objects.create(name='A do\'kon', slug='a-wh')
        cls.tenant_b = Tenant.objects.create(name='B do\'kon', slug='b-wh')

    def make(self, tenant, **kwargs):
        defaults = {
            'code': 'MARKAZ',
            'name': 'Markaziy ombor',
            'purpose': Warehouse.Purpose.MAIN,
        }

        with tenant_context(tenant.id):
            return Warehouse.objects.create(tenant=tenant, **{**defaults, **kwargs})

    # -- vazifa va qoldiq mantiqi --------------------------------------

    def test_transit_warehouse_is_not_sellable(self):
        """Tranzitdagi tovar sotuvga chiqmaydi — 2-band talabi."""
        main = self.make(self.tenant_a, code='MAIN', purpose=Warehouse.Purpose.MAIN)
        retail = self.make(self.tenant_a, code='SHOP', purpose=Warehouse.Purpose.RETAIL)
        transit = self.make(self.tenant_a, code='TR', purpose=Warehouse.Purpose.TRANSIT)

        self.assertTrue(main.is_sellable)
        self.assertTrue(retail.is_sellable)
        self.assertFalse(transit.is_sellable)

    def test_inactive_warehouse_is_not_sellable(self):
        warehouse = self.make(self.tenant_a, is_active=False)
        self.assertFalse(warehouse.is_sellable)

    def test_area_is_decimal(self):
        """6-arxitektura qarori: sonlar float emas, Decimal."""
        warehouse = self.make(self.tenant_a, area=Decimal('1200.500'))

        # Bazadan qayta o'qish ham tenant kontekstida bo'lishi kerak —
        # aks holda RLS qatorni ko'rsatmaydi.
        with tenant_context(self.tenant_a.id):
            warehouse.refresh_from_db()

        self.assertIsInstance(warehouse.area, Decimal)
        self.assertEqual(warehouse.area, Decimal('1200.500'))

    # -- tenant izolyatsiyasi ------------------------------------------

    def test_code_unique_within_tenant_only(self):
        """Ikki tashkilot bir xil kod ishlatishi mumkin."""
        self.make(self.tenant_a, code='MARKAZ')
        self.make(self.tenant_b, code='MARKAZ')

        with tenant_context(self.tenant_a.id):
            self.assertEqual(Warehouse.objects.count(), 1)

        with tenant_context(self.tenant_b.id):
            self.assertEqual(Warehouse.objects.count(), 1)

    def test_rls_hides_other_tenant_warehouses(self):
        self.make(self.tenant_a, code='AAA', name='A ombori')
        self.make(self.tenant_b, code='BBB', name='B ombori')

        with tenant_context(self.tenant_a.id):
            self.assertEqual(
                list(Warehouse.objects.values_list('name', flat=True)), ['A ombori']
            )

    def test_rls_is_fail_closed_without_context(self):
        self.make(self.tenant_a)
        self.assertEqual(Warehouse.objects.count(), 0)


class WarehouseAccessTests(TestCase):
    """Ombor darajasidagi cheklov **ixtiyoriy** ekanini qotiradi."""

    @classmethod
    def setUpTestData(cls):
        cls.tenant = Tenant.objects.create(name='Do\'kon', slug='access-test')
        cls.user = User.objects.create_user('xodim', password='x')

        Membership.objects.create(
            tenant=cls.tenant, user=cls.user, role=Membership.Role.STOREKEEPER
        )

    def setUp(self):
        with tenant_context(self.tenant.id):
            self.main = Warehouse.objects.create(
                tenant=self.tenant, code='MAIN', name='Asosiy'
            )
            self.shop = Warehouse.objects.create(
                tenant=self.tenant, code='SHOP', name='Do\'kon',
                purpose=Warehouse.Purpose.RETAIL,
            )

    def test_no_rules_means_all_warehouses_visible(self):
        """Cheklov yozilmagan bo'lsa — hamma omborlar ko'rinadi.

        Bu standart holat: aksariyat do'konlarda ombor soni oz va
        hamma hammasini, jumladan barcha hisobotlarni ko'rishi kerak.
        """
        with tenant_context(self.tenant.id):
            visible = WarehouseAccess.visible_to(self.user)
            self.assertEqual(visible.count(), 2)

    def test_rule_restricts_to_listed_warehouses(self):
        """Bitta qator paydo bo'lishi bilan cheklov kuchga kiradi."""
        with tenant_context(self.tenant.id):
            WarehouseAccess.objects.create(
                tenant=self.tenant,
                warehouse=self.shop,
                user=self.user,
                level=WarehouseAccess.Level.OPERATE,
            )

            visible = WarehouseAccess.visible_to(self.user)

            self.assertEqual(
                list(visible.values_list('code', flat=True)), ['SHOP']
            )

    def test_view_level_cannot_write(self):
        access = WarehouseAccess(level=WarehouseAccess.Level.VIEW)
        self.assertFalse(access.can_write)

        access.level = WarehouseAccess.Level.OPERATE
        self.assertTrue(access.can_write)
