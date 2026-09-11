"""Markaziy bank kurslarini qo'lda yoki cron orqali olish.

Namunalar:

    python manage.py sync_exchange_rates
    python manage.py sync_exchange_rates --date 2026-09-01
    python manage.py sync_exchange_rates --from 2026-08-01 --to 2026-08-31
    python manage.py sync_exchange_rates --tenant qurilish-dokon

Ishlab chiqarishda bu ishni Celery beat har kuni bajaradi. Buyruq
lokal ishlab chiqish (Redis yo'q), o'tgan davrni to'ldirish va
Celery'siz serverlar (oddiy cron) uchun.
"""

from __future__ import annotations

from datetime import date, timedelta

from django.core.management.base import BaseCommand, CommandError

from apps.pricing.cbu import CbuError, fetch_rates
from apps.pricing.tasks import sync_all_tenants

#: Bir buyruqda so'raladigan eng ko'p kun. Markaziy bank saytiga
#: keraksiz yuk bermaslik va xato bilan "10 yil" so'rab qo'ymaslik uchun.
MAX_DAYS = 400


class Command(BaseCommand):
    help = 'Markaziy bank valyuta kurslarini tashkilotlar kurs tarixiga yozadi.'

    def add_arguments(self, parser):
        parser.add_argument('--date', type=date.fromisoformat, help='Bitta sana, YYYY-MM-DD')
        parser.add_argument('--from', dest='date_from', type=date.fromisoformat,
                            help='Davr boshi, YYYY-MM-DD')
        parser.add_argument('--to', dest='date_to', type=date.fromisoformat,
                            help='Davr oxiri, YYYY-MM-DD (standart: bugun)')
        parser.add_argument('--tenant', help='Faqat shu tashkilot (slug)')

    def handle(self, *args, **options):
        dates = self._dates(options)

        for on_date in dates:
            label = on_date.isoformat() if on_date else 'joriy'

            try:
                rates = fetch_rates(on_date)
            except CbuError as exc:
                raise CommandError(f'{label}: {exc}') from exc

            summary = sync_all_tenants(rates, tenant_slug=options['tenant'])

            if not summary:
                raise CommandError('Mos faol tashkilot topilmadi.')

            for slug, result in summary.items():
                self.stdout.write(self._format(label, slug, result))

    def _dates(self, options) -> list[date | None]:
        if options['date'] and options['date_from']:
            raise CommandError('--date va --from ni birga berib bo\'lmaydi.')

        if options['date']:
            return [options['date']]

        if not options['date_from']:
            return [None]  # joriy kurs

        start = options['date_from']
        end = options['date_to'] or date.today()

        if end < start:
            raise CommandError('--to sanasi --from dan oldin.')

        days = (end - start).days + 1

        if days > MAX_DAYS:
            raise CommandError(f'Davr juda uzun ({days} kun), eng ko\'pi {MAX_DAYS}.')

        return [start + timedelta(days=i) for i in range(days)]

    def _format(self, label: str, slug: str, result: dict) -> str:
        if 'error' in result:
            return self.style.ERROR(f'[{label}] {slug}: XATO — {result["error"]}')

        if result['skipped_reason']:
            return self.style.WARNING(f'[{label}] {slug}: o\'tkazildi — {result["skipped_reason"]}')

        parts = []

        if result['created']:
            parts.append('yozildi: ' + ', '.join(result['created']))
        if result['already_present']:
            parts.append('bor edi: ' + ', '.join(result['already_present']))
        if result['missing']:
            parts.append('bankda yo\'q: ' + ', '.join(result['missing']))

        text = f'[{label}] {slug} ({result["valid_from"] or "—"}): ' + ('; '.join(parts) or 'valyuta yo\'q')

        return self.style.SUCCESS(text) if result['created'] else text
