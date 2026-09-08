"""Lokal sinov uchun demo ma'lumot yaratadi.

Foydalanish:
    python manage.py seed_demo
    python manage.py seed_demo --reset     # avval demo ma'lumotni o'chiradi

Yaratiladi:
  - ikkita tashkilot (qurilish mollari va kiyim-kechak do'koni);
  - har biriga admin foydalanuvchi;
  - har biriga o'sha sohaga xos o'lchov birliklari.

Ikkita tashkilot ataylab: tenant izolyatsiyasini brauzerda ham
tekshirib ko'rish mumkin bo'lsin.
"""

from __future__ import annotations

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.core.tenancy import tenant_context
from apps.tenants.models import Membership, Tenant
from apps.units.models import CustomUnit
from apps.warehouse.models import Warehouse

User = get_user_model()

DEMO_PASSWORD = 'demo12345'

# Django admin paneli uchun superuser. U bir vaqtda ikkala demo
# tashkilotning egasi qilinadi, shunda interfeysga ham kira oladi.
SUPERUSER_NAME = 'superadmin'
SUPERUSER_PASSWORD = 'admin12345'

DEMO_TENANTS = [
    {
        'slug': 'qurilish',
        'name': 'Baraka qurilish mollari',
        'business_type': Tenant.BusinessType.CONSTRUCTION,
        'username': 'qurilish',
        'first_name': 'Aziz',
        'last_name': 'Qurilishov',
        'units': [
            # "1 qop = 50 kg" bu yerda YO'Q — u mahsulotga bog'liq va
            # apps/catalog/ProductUnit ga tushadi. Bu yerda faqat
            # mahsulotdan mustaqil, sof geometrik/hajm birliklari.
            ('mashina', '6 * m3', 'msh', 'Bir yuk mashinasi qum yoki shag\'al'),
            ('vagon', '60 * m3', '', 'Temir yo\'l vagoni'),
        ],
        'warehouses': [
            {
                'code': 'MARKAZ', 'name': 'Markaziy ombor',
                'goods_type': Warehouse.GoodsType.CONSTRUCTION,
                'purpose': Warehouse.Purpose.MAIN,
                'manager': 'Akmal Karimov', 'phone': '+998 71 200 10 10',
                'address': 'Toshkent shahri, Sergeli tumani',
                'area': '1200', 'capacity': '25000',
                'temperature': '',
                'notes': 'Asosiy qabul va saqlash ombori.',
            },
            {
                'code': 'DOKON-1', 'name': 'Chilonzor savdo nuqtasi',
                'goods_type': Warehouse.GoodsType.CONSTRUCTION,
                'purpose': Warehouse.Purpose.RETAIL,
                'manager': 'Dilshod Rahimov', 'phone': '+998 71 205 11 44',
                'address': 'Toshkent shahri, Chilonzor 9-kvartal',
                'area': '180', 'capacity': '3000',
                'temperature': '',
                'notes': 'Chakana savdo zali.',
            },
            {
                'code': 'TRANZIT', 'name': "Yo'ldagi tovar",
                'goods_type': Warehouse.GoodsType.CONSTRUCTION,
                'purpose': Warehouse.Purpose.TRANSIT,
                'manager': '', 'phone': '', 'address': '',
                'area': None, 'capacity': None, 'temperature': '',
                'notes': "Omborlar orasida ko'chirilayotgan tovar. Sotuvga chiqmaydi.",
            },
        ],
    },
    {
        'slug': 'kiyim',
        'name': 'Zamon kiyim-kechak',
        'business_type': Tenant.BusinessType.CLOTHING,
        'username': 'kiyim',
        'first_name': 'Malika',
        'last_name': 'Kiyimova',
        'units': [
            ('tup', '10 * dona', '', 'O\'n donalik to\'plam'),
            ('top', '50 * meter', '', 'Bir top mato'),
        ],
        'warehouses': [
            {
                'code': 'SKLAD', 'name': 'Asosiy sklad',
                'goods_type': Warehouse.GoodsType.CLOTHING,
                'purpose': Warehouse.Purpose.MAIN,
                'manager': 'Malika Kiyimova', 'phone': '+998 90 111 22 33',
                'address': 'Toshkent shahri, Yunusobod',
                'area': '400', 'capacity': '12000',
                'temperature': '', 'notes': '',
            },
            {
                'code': 'BUTIK', 'name': 'Butik',
                'goods_type': Warehouse.GoodsType.CLOTHING,
                'purpose': Warehouse.Purpose.RETAIL,
                'manager': 'Nodira Salimova', 'phone': '+998 90 444 55 66',
                'address': "Toshkent shahri, Amir Temur ko'chasi",
                'area': '90', 'capacity': '1500',
                'temperature': '', 'notes': '',
            },
        ],
    },
]


class Command(BaseCommand):
    help = 'Lokal sinov uchun demo tashkilot, foydalanuvchi va birliklar yaratadi'

    def add_arguments(self, parser):
        parser.add_argument(
            '--reset',
            action='store_true',
            help='Avval mavjud demo ma\'lumotni o\'chiradi',
        )

    def handle(self, *args, **options):
        if options['reset']:
            self._reset()

        for spec in DEMO_TENANTS:
            self._create_tenant(spec)

        self._create_superuser()

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('Demo ma\'lumot tayyor.'))
        self.stdout.write('')
        self.stdout.write('Kirish uchun:')

        for spec in DEMO_TENANTS:
            self.stdout.write(
                f'  {spec["username"]:12} / {DEMO_PASSWORD}   — {spec["name"]}'
            )

        self.stdout.write(
            f'  {SUPERUSER_NAME:12} / {SUPERUSER_PASSWORD}   '
            '— superadmin (Django admin + ikkala tashkilot)'
        )

    def _create_superuser(self):
        """Superuser yaratadi va uni ikkala tashkilotga ega qilib qo'shadi.

        Django superuser huquqi faqat /admin/ ga taalluqli. Interfeysda
        ma'lumot ko'rish uchun a'zolik kerak, chunki PostgreSQL RLS
        superuserga ham qo'llanadi (jadvallarda FORCE ROW LEVEL SECURITY).
        """
        user, created = User.objects.get_or_create(
            username=SUPERUSER_NAME,
            defaults={
                'first_name': 'Bosh',
                'last_name': 'administrator',
                'email': 'superadmin@example.uz',
                'is_staff': True,
                'is_superuser': True,
            },
        )

        if created:
            user.set_password(SUPERUSER_PASSWORD)
            user.save(update_fields=['password'])

        for tenant in Tenant.objects.filter(
            slug__in=[spec['slug'] for spec in DEMO_TENANTS]
        ):
            Membership.objects.get_or_create(
                tenant=tenant,
                user=user,
                defaults={'role': Membership.Role.OWNER},
            )

        verb = 'yaratildi' if created else 'mavjud'
        self.stdout.write(f'Superadmin {verb}: {user.username}')

    # -- ichki yordamchilar --------------------------------------------

    def _reset(self):
        slugs = [spec['slug'] for spec in DEMO_TENANTS]
        usernames = [spec['username'] for spec in DEMO_TENANTS] + [SUPERUSER_NAME]

        for tenant in Tenant.objects.filter(slug__in=slugs):
            # CustomUnit RLS bilan himoyalangan — o'chirish ham kontekstda
            with tenant_context(tenant.id), transaction.atomic():
                Warehouse.objects.all().delete()
                CustomUnit.objects.all().delete()

        deleted, _ = Tenant.objects.filter(slug__in=slugs).delete()
        User.objects.filter(username__in=usernames).delete()

        self.stdout.write(f'Eski demo ma\'lumot o\'chirildi ({deleted} yozuv).')

    @transaction.atomic
    def _create_tenant(self, spec: dict):
        tenant, created = Tenant.objects.get_or_create(
            slug=spec['slug'],
            defaults={
                'name': spec['name'],
                'business_type': spec['business_type'],
            },
        )

        verb = 'yaratildi' if created else 'mavjud'
        self.stdout.write(f'Tashkilot {verb}: {tenant.name}')

        user, user_created = User.objects.get_or_create(
            username=spec['username'],
            defaults={
                'first_name': spec['first_name'],
                'last_name': spec['last_name'],
                'email': f'{spec["username"]}@example.uz',
            },
        )

        if user_created:
            user.set_password(DEMO_PASSWORD)
            user.save(update_fields=['password'])

        Membership.objects.get_or_create(
            tenant=tenant,
            user=user,
            defaults={'role': Membership.Role.OWNER},
        )

        # Birliklar RLS ostida — tenant kontekstisiz yozib bo'lmaydi.
        with tenant_context(tenant.id):
            for name, definition, symbol, description in spec['units']:
                CustomUnit.objects.get_or_create(
                    tenant=tenant,
                    name=name,
                    defaults={
                        'definition': definition,
                        'symbol': symbol,
                        'description': description,
                    },
                )

            unit_count = CustomUnit.objects.count()

            for warehouse in spec.get('warehouses', []):
                Warehouse.objects.get_or_create(
                    tenant=tenant,
                    code=warehouse['code'],
                    defaults={k: v for k, v in warehouse.items() if k != 'code'},
                )

            warehouse_count = Warehouse.objects.count()

        self.stdout.write(
            f'  foydalanuvchi: {user.username}, '
            f'birliklar: {unit_count}, omborlar: {warehouse_count}'
        )
