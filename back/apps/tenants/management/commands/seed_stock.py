"""Demo qoldiq ma'lumoti: kirim, partiya, sotuv va ko'chirish.

Foydalanish:
    python manage.py seed_stock

Ataylab ko'rsatilgan holatlar:

- partiyali kirim (yaroqlilik muddati bilan) va partiyasiz kirim;
- muddati o'tayotgan partiya — ogohlantirish uchun;
- band qilingan miqdor — "bor" va "sotish mumkin" farqi;
- tugallanmagan ko'chirish — tovar tranzit omborda turibdi;
- kamomad bilan tugagan ko'chirish.
"""

from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.catalog.models import Variant
from apps.core.tenancy import tenant_context
from apps.stock import services
from apps.stock.enums import MovementReason
from apps.stock.models import Batch, StockBalance, StockMovement
from apps.tenants.models import Tenant
from apps.warehouse.models import Warehouse

D = Decimal


class Command(BaseCommand):
    help = 'Demo qoldiq: kirim, partiya, sotuv va ko\'chirish'

    def handle(self, *args, **options):
        self._seed_construction()
        self._seed_clothing()

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('Demo qoldiq tayyor.'))

    def _seed_construction(self):
        tenant = Tenant.objects.filter(slug='qurilish').first()

        if tenant is None:
            return

        with tenant_context(tenant.id):
            if StockMovement.objects.exists():
                self.stdout.write('Qurilish: qoldiq allaqachon bor, o\'tkazib yuborildi')
                return

            main = Warehouse.objects.get(code='MARKAZ')
            shop = Warehouse.objects.get(code='DOKON-1')
            transit = Warehouse.objects.get(code='TRANZIT')

            cement = Variant.objects.get(sku='CEM-M400')
            gypsum = Variant.objects.get(sku='GYP-01')
            profile = Variant.objects.get(sku='PRF-6027')

            today = timezone.localdate()

            # Sement — ikki partiya, biri muddati yaqinlashgan
            fresh = Batch.objects.create(
                tenant=tenant, variant=cement, code='CEM-2026-03',
                expiry_date=today + timedelta(days=150),
                produced_at=today - timedelta(days=30),
            )
            old = Batch.objects.create(
                tenant=tenant, variant=cement, code='CEM-2025-11',
                expiry_date=today + timedelta(days=12),
                produced_at=today - timedelta(days=170),
            )

            services.record_movement(
                variant=cement, warehouse=main, batch=fresh,
                quantity=D('15000'), reason=MovementReason.PURCHASE,
                unit_cost=D('900'), currency='UZS',
                note='Bekabadsement zavodidan',
            )
            services.record_movement(
                variant=cement, warehouse=main, batch=old,
                quantity=D('2400'), reason=MovementReason.PURCHASE,
                unit_cost=D('870'), currency='UZS',
            )

            # Do'konga bir qism ko'chirilgan — to'liq qabul qilingan
            services.transfer_out(
                variant=cement, warehouse=main, transit_warehouse=transit,
                quantity=D('3000'), batch=fresh, note='Chilonzorga',
            )
            services.transfer_in(
                variant=cement, transit_warehouse=transit, warehouse=shop,
                quantity=D('3000'), batch=fresh,
            )

            # Sotuv
            services.record_movement(
                variant=cement, warehouse=shop, batch=fresh,
                quantity=D('-450'), reason=MovementReason.SALE,
            )

            # Band qilingan: 100 qop (5000 kg) buyurtmaga ajratilgan
            services.reserve(cement, main, D('5000'), batch=fresh)

            # Gips — partiyasiz
            services.record_movement(
                variant=gypsum, warehouse=main,
                quantity=D('900'), reason=MovementReason.PURCHASE,
                unit_cost=D('930'), currency='UZS',
            )

            # Profil — do'konda kam qoldi (min_stock bilan)
            profile.min_stock = D('50')
            profile.save(update_fields=['min_stock'])

            services.record_movement(
                variant=profile, warehouse=shop,
                quantity=D('40'), reason=MovementReason.PURCHASE,
                unit_cost=D('32000'), currency='UZS',
            )

            # Tugallanmagan ko'chirish: tovar hozir tranzitda turibdi
            services.transfer_out(
                variant=gypsum, warehouse=main, transit_warehouse=transit,
                quantity=D('300'), note='Yo\'lda',
            )

            summary = (
                f'Qurilish: {StockMovement.objects.count()} harakat, '
                f'{StockBalance.objects.exclude(quantity=0).count()} qoldiq qatori'
            )

        self.stdout.write(summary)

    def _seed_clothing(self):
        tenant = Tenant.objects.filter(slug='kiyim').first()

        if tenant is None:
            return

        with tenant_context(tenant.id):
            if StockMovement.objects.exists():
                self.stdout.write('Kiyim: qoldiq allaqachon bor, o\'tkazib yuborildi')
                return

            warehouse = Warehouse.objects.get(code='SKLAD')
            shop = Warehouse.objects.get(code='BUTIK')

            # Har variantga alohida qoldiq — variantlar shuning uchun kerak
            for index, variant in enumerate(Variant.objects.order_by('sku')):
                services.record_movement(
                    variant=variant, warehouse=warehouse,
                    quantity=D(str(20 + index * 5)),
                    reason=MovementReason.PURCHASE,
                    unit_cost=D('95000'), currency='UZS',
                )

                if index < 3:
                    services.record_movement(
                        variant=variant, warehouse=shop,
                        quantity=D('6'), reason=MovementReason.PURCHASE,
                        unit_cost=D('95000'), currency='UZS',
                    )

            summary = (
                f'Kiyim: {StockMovement.objects.count()} harakat, '
                f'{StockBalance.objects.exclude(quantity=0).count()} qoldiq qatori'
            )

        self.stdout.write(summary)
