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

User = get_user_model()

DEMO_PASSWORD = 'demo12345'

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

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('Demo ma\'lumot tayyor.'))
        self.stdout.write('')
        self.stdout.write('Kirish uchun:')

        for spec in DEMO_TENANTS:
            self.stdout.write(
                f'  {spec["username"]:12} / {DEMO_PASSWORD}   — {spec["name"]}'
            )

    # -- ichki yordamchilar --------------------------------------------

    def _reset(self):
        slugs = [spec['slug'] for spec in DEMO_TENANTS]
        usernames = [spec['username'] for spec in DEMO_TENANTS]

        for tenant in Tenant.objects.filter(slug__in=slugs):
            # CustomUnit RLS bilan himoyalangan — o'chirish ham kontekstda
            with tenant_context(tenant.id), transaction.atomic():
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

            count = CustomUnit.objects.count()

        self.stdout.write(f'  foydalanuvchi: {user.username}, birliklar: {count}')
