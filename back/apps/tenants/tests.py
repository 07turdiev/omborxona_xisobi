"""Tashkilot sozlamalari va a'zoliklar testlari."""

from __future__ import annotations

from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.core.tenancy import tenant_context
from apps.documents import services as docs
from apps.documents.models import Document
from apps.tenants.models import Membership, Tenant
from apps.warehouse.models import Warehouse

User = get_user_model()


class MembershipRoleTests(TestCase):
    """Rol tashkilot kesimida saqlanadi, foydalanuvchida emas."""

    @classmethod
    def setUpTestData(cls):
        cls.tenant_a = Tenant.objects.create(name='A do\'kon', slug='member-a')
        cls.tenant_b = Tenant.objects.create(name='B do\'kon', slug='member-b')
        cls.user = User.objects.create_user('xodim', password='x')

    def test_same_user_can_have_different_roles(self):
        """Bir odam A da direktor, B da omborchi bo'lishi mumkin."""
        Membership.objects.create(
            tenant=self.tenant_a, user=self.user, role=Membership.Role.OWNER
        )
        Membership.objects.create(
            tenant=self.tenant_b, user=self.user, role=Membership.Role.STOREKEEPER
        )

        self.assertTrue(self.user.membership_for(self.tenant_a.id).is_admin)
        self.assertFalse(self.user.membership_for(self.tenant_b.id).is_admin)

    def test_write_roles(self):
        for role, expected in [
            (Membership.Role.OWNER, True),
            (Membership.Role.MANAGER, True),
            (Membership.Role.STOREKEEPER, True),
            (Membership.Role.SALESPERSON, True),
            (Membership.Role.VIEWER, False),
        ]:
            with self.subTest(role=role):
                membership = Membership(role=role, is_active=True)
                self.assertEqual(membership.can_write, expected)

    def test_admin_roles(self):
        for role, expected in [
            (Membership.Role.OWNER, True),
            (Membership.Role.MANAGER, True),
            (Membership.Role.STOREKEEPER, False),
            (Membership.Role.SALESPERSON, False),
            (Membership.Role.VIEWER, False),
        ]:
            with self.subTest(role=role):
                membership = Membership(role=role, is_active=True)
                self.assertEqual(membership.is_admin, expected)

    def test_inactive_membership_has_no_rights(self):
        membership = Membership(role=Membership.Role.OWNER, is_active=False)

        self.assertFalse(membership.can_write)
        self.assertFalse(membership.is_admin)

    def test_membership_for_ignores_inactive(self):
        Membership.objects.create(
            tenant=self.tenant_a, user=self.user,
            role=Membership.Role.OWNER, is_active=False,
        )

        self.assertIsNone(self.user.membership_for(self.tenant_a.id))

    def test_membership_for_ignores_inactive_tenant(self):
        self.tenant_a.is_active = False
        self.tenant_a.save(update_fields=['is_active'])

        Membership.objects.create(
            tenant=self.tenant_a, user=self.user, role=Membership.Role.OWNER
        )

        self.assertIsNone(self.user.membership_for(self.tenant_a.id))


class DocumentPrefixTests(TestCase):
    """Hujjat prefiksi tashkilot sozlamasidan olinadi."""

    @classmethod
    def setUpTestData(cls):
        cls.tenant = Tenant.objects.create(
            name='Do\'kon', slug='prefix-test',
            purchase_prefix='KRM', sale_prefix='STV',
        )

    def test_prefix_from_settings(self):
        with tenant_context(self.tenant.id):
            purchase = docs.next_number(self.tenant, Document.Kind.PURCHASE)
            sale = docs.next_number(self.tenant, Document.Kind.SALE)

        self.assertTrue(purchase.startswith('KRM-'))
        self.assertTrue(sale.startswith('STV-'))

    def test_changing_prefix_does_not_renumber_old_documents(self):
        """Prefiks o'zgarsa eski hujjat o'z raqamini saqlaydi.

        Raqam yaratilganda bir marta yoziladi — aks holda hujjat
        raqamlariga tashqi havolalar buzilardi.
        """
        with tenant_context(self.tenant.id):
            warehouse = Warehouse.objects.create(
                tenant=self.tenant, code='W', name='Ombor'
            )
            document = Document.objects.create(
                tenant=self.tenant,
                kind=Document.Kind.PURCHASE,
                number=docs.next_number(self.tenant, Document.Kind.PURCHASE),
                warehouse=warehouse,
            )

            old_number = document.number

            self.tenant.purchase_prefix = 'BOSHQA'
            self.tenant.save(update_fields=['purchase_prefix'])

            document.refresh_from_db()

        self.assertEqual(document.number, old_number)
        self.assertTrue(old_number.startswith('KRM-'))

    def test_falls_back_to_default_prefix(self):
        blank = Tenant.objects.create(
            name='Bo\'sh', slug='prefix-blank', purchase_prefix=''
        )

        with tenant_context(blank.id):
            number = docs.next_number(blank, Document.Kind.PURCHASE)

        self.assertTrue(number.startswith('KIR-'))


class TenantSettingsTests(TestCase):
    def test_defaults(self):
        tenant = Tenant.objects.create(name='Yangi', slug='defaults')

        self.assertEqual(tenant.base_currency, 'UZS')
        self.assertEqual(tenant.purchase_prefix, 'KIR')
        self.assertEqual(tenant.sale_prefix, 'SOT')
        self.assertEqual(tenant.transfer_prefix, 'KOCH')
        self.assertEqual(tenant.expiry_warning_days, 30)

    def test_slug_is_unique(self):
        Tenant.objects.create(name='Birinchi', slug='takror')

        with self.assertRaises(Exception):
            Tenant.objects.create(name='Ikkinchi', slug='takror')
