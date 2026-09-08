"""Demo kontragentlar va hujjatlar.

Foydalanish:
    python manage.py seed_documents

Yaratiladi: yetkazib beruvchilar, mijozlar, ko'p qatorli kirim va
sotuv hujjatlari. Sotuvda foyda FIFO tannarxidan avtomatik chiqadi.
"""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.catalog.models import Variant
from apps.core.tenancy import tenant_context
from apps.documents import services as docs
from apps.documents.models import Document
from apps.partners.models import Partner
from apps.tenants.models import Tenant
from apps.warehouse.models import Warehouse

D = Decimal

PARTNERS = {
    'qurilish': [
        ('Bekabadsement AJ', True, False, '301234567', '+998 71 300 10 10'),
        ('Knauf Gips Buxoro', True, False, '302345678', '+998 65 220 30 40'),
        ('Qurilish Servis MCHJ', False, True, '303456789', '+998 90 123 45 67'),
        ('Baraka Qurilish', True, True, '304567890', '+998 91 234 56 78'),
    ],
    'kiyim': [
        ('Textile Import LLC', True, False, '305678901', '+998 71 250 11 22'),
        ('Zamon Butik', False, True, '306789012', '+998 90 555 66 77'),
    ],
}


class Command(BaseCommand):
    help = 'Demo kontragent va hujjatlarni yaratadi'

    def handle(self, *args, **options):
        for slug in ('qurilish', 'kiyim'):
            self._seed(slug)

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('Demo hujjatlar tayyor.'))

    def _seed(self, slug: str):
        tenant = Tenant.objects.filter(slug=slug).first()

        if tenant is None:
            return

        with tenant_context(tenant.id):
            for name, supplier, customer, inn, phone in PARTNERS[slug]:
                Partner.objects.get_or_create(
                    tenant=tenant, name=name,
                    defaults={
                        'is_supplier': supplier,
                        'is_customer': customer,
                        'inn': inn,
                        'phone': phone,
                    },
                )

            if Document.objects.exists():
                summary = f'{tenant.name}: hujjatlar allaqachon bor'
            else:
                summary = self._create_documents(tenant, slug)

        self.stdout.write(summary)

    def _create_documents(self, tenant: Tenant, slug: str) -> str:
        today = timezone.localdate()

        if slug == 'qurilish':
            warehouse = Warehouse.objects.get(code='MARKAZ')
            shop = Warehouse.objects.get(code='DOKON-1')
            supplier = Partner.objects.get(name='Bekabadsement AJ')
            customer = Partner.objects.get(name='Qurilish Servis MCHJ')

            cement = Variant.objects.get(sku='CEM-M400')
            gypsum = Variant.objects.get(sku='GYP-01')
            profile = Variant.objects.get(sku='PRF-6027')

            # Ko'p qatorli kirim: bitta yuk xati, uch pozitsiya.
            # Miqdorlar o'ram birligida — dizaynda bu imkoniyat yo'q edi.
            purchase = self._document(
                tenant, Document.Kind.PURCHASE, warehouse, supplier,
                date=today - timedelta(days=5),
                external_number='BKS-2026-1180',
            )
            docs.build_line(purchase, variant=cement, quantity=D('40'),
                            unit_price=D('46000'), unit='qop', position=1)
            docs.build_line(purchase, variant=gypsum, quantity=D('30'),
                            unit_price=D('28500'), unit='qop', position=2)
            docs.build_line(purchase, variant=profile, quantity=D('120'),
                            unit_price=D('32500'), position=3)
            docs.confirm(purchase)

            # Sotuv: foyda FIFO tannarxidan chiqadi
            sale = self._document(
                tenant, Document.Kind.SALE, shop, customer,
                date=today - timedelta(days=1),
            )
            docs.build_line(sale, variant=cement, quantity=D('12'),
                            unit_price=D('58000'), unit='qop', position=1)
            docs.confirm(sale)

            # Qoralama — hali qoldiqqa tegmagan
            draft = self._document(
                tenant, Document.Kind.SALE, shop, customer, date=today
            )
            docs.build_line(draft, variant=cement, quantity=D('5'),
                            unit_price=D('58000'), unit='qop', position=1)
            docs.recalculate_totals(draft)

            return (
                f'{tenant.name}: {Partner.objects.count()} kontragent, '
                f'{Document.objects.count()} hujjat '
                f'(sotuv foydasi {sale.profit:,.0f})'
            )

        warehouse = Warehouse.objects.get(code='SKLAD')
        shop = Warehouse.objects.get(code='BUTIK')
        supplier = Partner.objects.get(name='Textile Import LLC')
        customer = Partner.objects.get(name='Zamon Butik')

        shirts = list(Variant.objects.order_by('sku')[:3])

        purchase = self._document(
            tenant, Document.Kind.PURCHASE, warehouse, supplier,
            date=today - timedelta(days=4),
        )
        for position, variant in enumerate(shirts, start=1):
            docs.build_line(purchase, variant=variant, quantity=D('15'),
                            unit_price=D('96000'), position=position)
        docs.confirm(purchase)

        sale = self._document(
            tenant, Document.Kind.SALE, shop, customer, date=today
        )
        docs.build_line(sale, variant=shirts[0], quantity=D('3'),
                        unit_price=D('149000'), position=1)
        docs.confirm(sale)

        return (
            f'{tenant.name}: {Partner.objects.count()} kontragent, '
            f'{Document.objects.count()} hujjat'
        )

    def _document(self, tenant, kind, warehouse, partner, *, date, external_number=''):
        return Document.objects.create(
            tenant=tenant,
            kind=kind,
            number=docs.next_number(tenant, kind, date),
            date=date,
            warehouse=warehouse,
            partner=partner,
            external_number=external_number,
        )
