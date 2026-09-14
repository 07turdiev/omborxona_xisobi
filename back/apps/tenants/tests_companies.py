"""Kompaniyalar (superadmin) va rekvizitlar testlari."""

from __future__ import annotations

import io
import shutil
import tempfile

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings, tag
from PIL import Image
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.audit.models import AuditEvent
from apps.core.tenancy import get_current_tenant_id, tenant_context
from apps.pricing.models import Currency
from apps.tenants.models import Membership, Tenant
from apps.users.models import User
from apps.warehouse.models import Warehouse

MEDIA_ROOT = tempfile.mkdtemp(prefix='omborxona-test-media-')


def client_for(user) -> APIClient:
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f'Bearer {RefreshToken.for_user(user).access_token}')
    return client


def png_file(name='logo.png') -> SimpleUploadedFile:
    buffer = io.BytesIO()
    Image.new('RGB', (40, 20), 'navy').save(buffer, format='PNG')
    return SimpleUploadedFile(name, buffer.getvalue(), content_type='image/png')


@tag('companies')
class TenantContextNestingTests(TestCase):
    """Ichki kontekstdan chiqqach tashqi tashkilot tiklanishi kerak."""

    @classmethod
    def setUpTestData(cls):
        cls.a = Tenant.objects.create(name='A', slug='nest-a')
        cls.b = Tenant.objects.create(name='B', slug='nest-b')

        with tenant_context(cls.a.id):
            Warehouse.objects.create(tenant=cls.a, code='A1', name='A ombor')

    def test_outer_tenant_restored_after_inner_context(self):
        with tenant_context(self.a.id):
            with tenant_context(self.b.id):
                self.assertEqual(Warehouse.objects.count(), 0)

            # Avval bu yerda baza kontekstsiz qolardi va natija 0 bo'lardi
            self.assertEqual(get_current_tenant_id(), self.a.id)
            self.assertEqual(Warehouse.objects.count(), 1)


@tag('companies')
@override_settings(MEDIA_ROOT=MEDIA_ROOT)
class CompanyApiTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.superuser = User.objects.create_superuser('root', password='x')
        cls.existing = Tenant.objects.create(name='Mavjud do‘kon', slug='mavjud', code='MAV')
        cls.owner = User.objects.create_user('ega', password='x')
        Membership.objects.create(tenant=cls.existing, user=cls.owner, role=Membership.Role.OWNER)

        with tenant_context(cls.existing.id):
            Warehouse.objects.create(tenant=cls.existing, code='W1', name='Ombor 1')

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.root = client_for(self.superuser)

    def create(self, **fields):
        payload = {
            'name': 'Qurilish Savdo MChJ',
            'code': 'QS',
            'legal_form': 'llc',
            'inn': '305123456',
            'owner_username': 'yangi_ega',
            'owner_password': 'Kuchli-parol-2026',
            **fields,
        }
        return self.root.post('/api/companies/', payload, format='json')

    def test_superuser_creates_company_with_owner(self):
        response = self.create()

        self.assertEqual(response.status_code, 201, response.content)
        tenant = Tenant.objects.get(code='QS')
        owner = User.objects.get(username='yangi_ega')

        self.assertEqual(tenant.slug, 'qs')
        self.assertEqual(owner.membership_for(tenant.id).role, Membership.Role.OWNER)

        with tenant_context(tenant.id):
            self.assertTrue(Currency.objects.filter(code='UZS', is_base=True).exists())
            # Superadmin amali o'sha tashkilotning o'z tarixida
            self.assertTrue(AuditEvent.objects.filter(object_type='company', action='create').exists())

    def test_existing_user_becomes_owner_without_password(self):
        response = self.create(owner_username='ega', owner_password='')

        self.assertEqual(response.status_code, 201, response.content)
        self.assertEqual(self.owner.memberships.count(), 2)

    def test_new_owner_requires_password(self):
        response = self.create(owner_password='')

        self.assertEqual(response.status_code, 400)
        self.assertIn('owner_password', response.json())

    def test_only_superuser(self):
        response = client_for(self.owner).get('/api/companies/')

        self.assertEqual(response.status_code, 403)

    def test_code_validation(self):
        for code, ok in [('MAV', False), ('juda-uzun-kod', False), ('qs 1', False), ('qs-1', True)]:
            with self.subTest(code=code):
                response = self.create(code=code, owner_username=f'u-{code}'[:20])
                self.assertEqual(response.status_code == 201, ok, response.content)

    def test_inn_mfo_account_formats(self):
        """Xato rekvizit hujjatda chiqib, bank to'lovini qaytarardi."""
        response = self.create(inn='12345678', mfo='001', bank_account='2020800')

        self.assertEqual(response.status_code, 400)
        self.assertEqual(set(response.json()), {'inn', 'mfo', 'bank_account'})

    def test_warehouse_count_respects_rls(self):
        self.create()
        rows = {row['code']: row for row in self.root.get('/api/companies/').json()['results']}

        self.assertEqual(rows['MAV']['warehouse_count'], 1)
        self.assertEqual(rows['QS']['warehouse_count'], 0)
        self.assertEqual(rows['MAV']['owner']['username'], 'ega')

    def test_deactivation_blocks_members(self):
        response = self.root.patch(
            f'/api/companies/{self.existing.id}/', {'is_active': False}, format='json'
        )

        self.assertEqual(response.status_code, 200, response.content)
        self.assertIsNone(self.owner.membership_for(self.existing.id))

    def test_summary(self):
        self.create()

        data = self.root.get('/api/companies/summary/').json()

        self.assertEqual(data['total'], 2)
        self.assertEqual(data['warehouses'], 1)


@tag('companies')
@override_settings(MEDIA_ROOT=MEDIA_ROOT)
class RequisitesTests(TestCase):
    """Do'kon egasi o'z rekvizitlari va logotipini sozlamalardan boshqaradi."""

    @classmethod
    def setUpTestData(cls):
        cls.tenant = Tenant.objects.create(name='Do‘kon', slug='rekvizit')
        cls.owner = User.objects.create_user('ega2', password='x')
        Membership.objects.create(tenant=cls.tenant, user=cls.owner, role=Membership.Role.OWNER)

    def setUp(self):
        self.client_ = client_for(self.owner)

    def test_owner_updates_bank_requisites(self):
        response = self.client_.patch('/api/tenant/current/', {
            'director': 'Karimov A.', 'bank_name': 'Kapitalbank', 'mfo': '01088',
            'bank_account': '20208000900123456001', 'legal_form': 'llc',
        }, format='json')

        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()['legal_form_display'], 'MChJ')

    def test_logo_upload_and_remove(self):
        uploaded = self.client_.patch(
            '/api/tenant/current/', {'logo': png_file()}, format='multipart'
        )

        self.assertEqual(uploaded.status_code, 200, uploaded.content)
        self.assertIn('/media/tenant-logos/', uploaded.json()['logo'])

        removed = self.client_.patch('/api/tenant/current/', {'logo': None}, format='json')

        self.assertIsNone(removed.json()['logo'])

    def test_non_image_logo_rejected(self):
        fake = SimpleUploadedFile('logo.png', b'bu rasm emas', content_type='image/png')

        response = self.client_.patch('/api/tenant/current/', {'logo': fake}, format='multipart')

        self.assertEqual(response.status_code, 400)
