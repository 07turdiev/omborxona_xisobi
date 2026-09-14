"""Amallar tarixi testlari."""

from __future__ import annotations

from decimal import Decimal

from django.db import DatabaseError, transaction
from django.test import TestCase, tag
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.audit import services
from apps.audit.models import AuditEvent
from apps.catalog.models import Category, Product, Variant
from apps.core.access import Perm
from apps.core.tenancy import tenant_context
from apps.tenants.models import Membership, Tenant
from apps.users.models import User
from apps.warehouse.models import Warehouse

Role = Membership.Role


class AuditTestBase(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.tenant = Tenant.objects.create(name='Do\'kon', slug='audit-test')

        with tenant_context(cls.tenant.id):
            cls.warehouse = Warehouse.objects.create(
                tenant=cls.tenant, code='MAIN', name='Asosiy'
            )
            category = Category.objects.create(tenant=cls.tenant, name='Sement')
            product = Product.objects.create(
                tenant=cls.tenant, category=category, name='Sement M400', base_unit='kg'
            )
            cls.variant = Variant.objects.create(
                tenant=cls.tenant, product=product, sku='CEM-1',
                purchase_price=Decimal('1000'), sale_price=Decimal('1300'),
            )

    _counter = 0

    def client_for(self, role, permissions=None, first_name=''):
        AuditTestBase._counter += 1
        user = User.objects.create_user(
            username=f'audit{AuditTestBase._counter}', password='x', first_name=first_name
        )
        Membership.objects.create(
            tenant=self.tenant, user=user, role=role, permissions=permissions
        )

        client = APIClient()
        token = RefreshToken.for_user(user).access_token
        client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        client.user = user

        return client

    def events(self, **filters) -> list[AuditEvent]:
        with tenant_context(self.tenant.id):
            return list(AuditEvent.objects.filter(**filters).order_by('id'))


@tag('audit')
class AppendOnlyTests(AuditTestBase):

    def make_event(self):
        with tenant_context(self.tenant.id):
            return services.record('create', 'partner', object_repr='Sinov')

    def test_model_refuses_update_and_delete(self):
        event = self.make_event()

        with self.assertRaises(RuntimeError):
            event.save()

        with self.assertRaises(RuntimeError):
            event.delete()

    def test_database_blocks_update_and_delete(self):
        """Model himoyasini chetlab o'tadigan `update()` va `delete()` ham to'xtaydi."""
        event = self.make_event()

        with tenant_context(self.tenant.id):
            with self.assertRaises(DatabaseError), transaction.atomic():
                AuditEvent.objects.filter(pk=event.pk).update(details='o‘chirilgan iz')

            with self.assertRaises(DatabaseError), transaction.atomic():
                AuditEvent.objects.filter(pk=event.pk).delete()

    def test_deleting_user_keeps_history(self):
        """Xodim o'chirilsa ham tarix "kim qildi" savoliga javob beradi."""
        client = self.client_for(Role.OWNER, first_name='Anvar')
        client.post('/api/partners/', {'name': 'Qurilish MChJ', 'is_supplier': True}, format='json')

        User.objects.filter(pk=client.user.pk).delete()

        [event] = self.events(object_type='partner')
        self.assertEqual(event.user_name, 'Anvar')


@tag('audit')
class RecordingTests(AuditTestBase):

    def test_create_update_delete(self):
        client = self.client_for(Role.OWNER)

        created = client.post(
            '/api/partners/', {'name': 'Qurilish MChJ', 'is_supplier': True}, format='json'
        )
        self.assertEqual(created.status_code, 201, created.content)
        partner_id = created.json()['id']

        client.patch(f'/api/partners/{partner_id}/', {'phone': '+998901112233'}, format='json')
        # Hech narsa o'zgarmagan saqlash tarixni to'ldirmasligi kerak
        client.patch(f'/api/partners/{partner_id}/', {'phone': '+998901112233'}, format='json')
        client.delete(f'/api/partners/{partner_id}/')

        events = self.events(object_type='partner')

        self.assertEqual([e.action for e in events], ['create', 'update', 'delete'])
        self.assertEqual(events[1].changes, {'phone': ['', '+998901112233']})
        self.assertIn('Qurilish MChJ', events[2].object_repr)

    def test_document_lifecycle(self):
        client = self.client_for(Role.OWNER)

        response = client.post('/api/documents/', {
            'kind': 'purchase',
            'warehouse': self.warehouse.pk,
            'items': [{'variant': self.variant.pk, 'quantity': '10', 'unit_price': '1000'}],
        }, format='json')
        self.assertEqual(response.status_code, 201, response.content)
        document_id = response.json()['id']

        self.assertEqual(client.post(f'/api/documents/{document_id}/confirm/').status_code, 200)
        self.assertEqual(
            client.post(
                f'/api/documents/{document_id}/cancel/', {'note': 'Xato kiritilgan'},
                format='json',
            ).status_code,
            200,
        )

        events = self.events(object_type='purchase')

        self.assertEqual([e.action for e in events], ['create', 'confirm', 'cancel'])
        self.assertTrue(all(e.warehouse_name == 'Asosiy' for e in events))
        self.assertEqual(events[2].details, 'Xato kiritilgan')

    def test_settings_change_recorded(self):
        client = self.client_for(Role.OWNER)

        client.patch('/api/tenant/current/', {'phone': '+998712000000'}, format='json')

        [event] = self.events(object_type='settings')
        self.assertEqual(event.changes['phone'], ['', '+998712000000'])

    def test_permission_change_recorded(self):
        """Kim kimga qanday ruxsat berganini keyin bilish mumkin bo'lishi kerak."""
        owner = self.client_for(Role.OWNER)
        target = self.client_for(Role.SALESPERSON)
        membership = Membership.objects.get(user=target.user)

        owner.patch(
            f'/api/members/{membership.pk}/',
            {'permissions': [Perm.SALES, Perm.VIEW_PROFIT]},
            format='json',
        )

        [event] = self.events(object_type='member', action='update')
        self.assertEqual(event.changes['permissions'][1], ['sales', 'view_profit'])


@tag('audit')
class VisibilityTests(AuditTestBase):

    def setUp(self):
        self.owner = self.client_for(Role.OWNER)
        self.cashier = self.client_for(Role.SALESPERSON)

        self.owner.post('/api/partners/', {'name': 'Egasining', 'is_supplier': True}, format='json')
        self.cashier.post('/api/partners/', {'name': 'Kassirning', 'is_customer': True}, format='json')

    def names(self, client, **params):
        response = client.get('/api/history/', params)
        self.assertEqual(response.status_code, 200, response.content)

        return {row['object_repr'] for row in response.json()['results']}

    def test_manager_sees_everyone(self):
        manager = self.client_for(Role.MANAGER)

        self.assertEqual(self.names(manager), {'Egasining', 'Kassirning'})
        self.assertEqual(manager.get('/api/history/meta/').json()['scope'], 'all')

    def test_cashier_sees_only_own(self):
        self.assertEqual(self.names(self.cashier), {'Kassirning'})
        self.assertEqual(self.cashier.get('/api/history/meta/').json()['scope'], 'own')

    def test_user_filter_cannot_widen_own_scope(self):
        """Boshqa xodim ID si bilan filtrlash kassirga uning tarixini ochmaydi."""
        self.assertEqual(
            self.names(self.cashier, user=self.owner.user.pk), {'Kassirning'}
        )

    def test_history_requires_permission(self):
        client = self.client_for(Role.STOREKEEPER, [Perm.STOCK])

        self.assertEqual(client.get('/api/history/').status_code, 403)

    def test_price_change_hidden_without_purchase_price_permission(self):
        self.owner.patch(
            f'/api/variants/{self.variant.pk}/', {'purchase_price': '1200.00'}, format='json'
        )

        manager = self.client_for(Role.MANAGER, [Perm.HISTORY, Perm.PRODUCTS])

        [row] = manager.get('/api/history/', {'object_type': 'variant'}).json()['results']
        [owner_row] = self.owner.get('/api/history/', {'object_type': 'variant'}).json()['results']

        self.assertIsNone(row['changes']['purchase_price'])
        self.assertEqual(owner_row['changes']['purchase_price'], ['1000.00', '1200.00'])
