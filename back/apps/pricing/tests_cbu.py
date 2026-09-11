"""Markaziy bank kurslarini olish va sinxronlash testlari.

Tarmoqqa hech qachon chiqilmaydi: `fetch_rates` va `urlopen` soxtalashtiriladi.
"""

from __future__ import annotations

import io
import json
from datetime import date
from decimal import Decimal
from unittest import mock

from django.core.management import CommandError, call_command
from django.test import SimpleTestCase, TestCase
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.core.tenancy import tenant_context
from apps.pricing import services as pricing
from apps.pricing.cbu import CBU_SOURCE, CbuError, CbuRate, fetch_rates, parse_rates
from apps.pricing.models import Currency, ExchangeRate
from apps.pricing.rate_sync import sync_rates_from_cbu
from apps.pricing.tasks import sync_all_tenants, sync_cbu_rates
from apps.tenants.models import Membership, Tenant
from apps.users.models import User

D = Decimal
DAY = date(2026, 9, 11)


def cbu_row(code, rate, nominal='1', day='11.09.2026'):
    """Markaziy bank javobidagi bitta yozuv (keraksiz maydonlarsiz)."""
    return {'Ccy': code, 'Nominal': nominal, 'Rate': rate, 'Date': day}


def rates(**codes) -> dict[str, CbuRate]:
    """`rates(USD='11783.47')` -> `fetch_rates()` natijasi ko'rinishida."""
    return {code: CbuRate(code, D(value), DAY) for code, value in codes.items()}


# ---------------------------------------------------------------------
# Javobni tahlil qilish
# ---------------------------------------------------------------------

class ParseRatesTests(SimpleTestCase):

    def test_parses_rate_as_decimal_and_date(self):
        result = parse_rates([cbu_row('USD', '11783.47')])

        self.assertEqual(result['USD'].rate, D('11783.47'))
        self.assertIsInstance(result['USD'].rate, Decimal)
        self.assertEqual(result['USD'].valid_from, DAY)

    def test_rate_divided_by_nominal(self):
        """IDR 10 birlik uchun beriladi: "10 rupiya = 6.72 so'm".

        Bo'lmasdan olinsa kurs 10 barobar oshib ketadi va xato hech
        qayerda ko'rinmaydi — tannarx jimgina noto'g'ri bo'ladi.
        """
        result = parse_rates([cbu_row('IDR', '6.72', nominal='10')])

        self.assertEqual(result['IDR'].rate, D('0.672'))

    def test_rate_rounded_to_factor_precision(self):
        """`FactorField` 6 kasr saqlaydi — ko'prog'i yaxlitlanadi."""
        result = parse_rates([cbu_row('XYZ', '1', nominal='3')])

        self.assertEqual(result['XYZ'].rate, D('0.333333'))

    def test_malformed_rows_skipped_rest_kept(self):
        """Bitta buzuq yozuv qolgan valyutalarni to'xtatmasligi kerak."""
        result = parse_rates([
            cbu_row('USD', '11783.47'),
            cbu_row('EUR', 'abc'),
            cbu_row('RUB', '139.70', day='2026-09-11'),   # ISO sana — kutilmagan format
            cbu_row('KZT', '0'),                         # nol kurs
            cbu_row('GBP', '-5'),                        # manfiy kurs
            cbu_row('JPY', '76.44', nominal='0'),        # nolga bo'lish
            {'Ccy': 'CNY'},                              # maydonlar yo'q
            'satr',                                      # yozuv emas
        ])

        self.assertEqual(set(result), {'USD'})

    def test_code_normalized_to_upper(self):
        result = parse_rates([cbu_row(' usd ', '11783.47')])

        self.assertIn('USD', result)

    def test_not_a_list_rejected(self):
        with self.assertRaises(CbuError):
            parse_rates({'error': 'bad request'})

    def test_no_valid_rows_rejected(self):
        """Bo'sh javobni "kurslar yo'q" deb jimgina qabul qilmaymiz."""
        for payload in [[], [cbu_row('USD', 'abc')]]:
            with self.subTest(payload=payload):
                with self.assertRaises(CbuError):
                    parse_rates(payload)


class FetchRatesTests(SimpleTestCase):

    def _response(self, payload):
        body = io.BytesIO(json.dumps(payload).encode())
        body.__enter__ = lambda s: s
        body.__exit__ = lambda s, *a: None
        return body

    @mock.patch('apps.pricing.cbu.urllib.request.urlopen')
    def test_latest_url(self, urlopen):
        urlopen.return_value = self._response([cbu_row('USD', '11783.47')])

        fetch_rates()

        self.assertTrue(urlopen.call_args.args[0].full_url.endswith('/json/'))

    @mock.patch('apps.pricing.cbu.urllib.request.urlopen')
    def test_date_url(self, urlopen):
        urlopen.return_value = self._response([cbu_row('USD', '11783.47')])

        fetch_rates(date(2026, 9, 1))

        self.assertIn('/json/all/2026-09-01/', urlopen.call_args.args[0].full_url)

    @mock.patch('apps.pricing.cbu.urllib.request.urlopen', side_effect=OSError('timeout'))
    def test_network_error_becomes_cbu_error(self, urlopen):
        with self.assertRaises(CbuError):
            fetch_rates()

    @mock.patch('apps.pricing.cbu.urllib.request.urlopen')
    def test_non_json_becomes_cbu_error(self, urlopen):
        body = io.BytesIO(b'<html>502 Bad Gateway</html>')
        body.__enter__ = lambda s: s
        body.__exit__ = lambda s, *a: None
        urlopen.return_value = body

        with self.assertRaises(CbuError):
            fetch_rates()


# ---------------------------------------------------------------------
# Tashkilot kurs tarixiga yozish
# ---------------------------------------------------------------------

class SyncTestBase(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.tenant = Tenant.objects.create(name='Qurilish', slug='cbu-a', base_currency='UZS')
        cls.other = Tenant.objects.create(name='Kiyim', slug='cbu-b', base_currency='UZS')

    def add_currencies(self, tenant, *codes, inactive=()):
        with tenant_context(tenant.id):
            Currency.objects.create(tenant=tenant, code='UZS', name='So\'m', is_base=True)

            for code in codes:
                Currency.objects.create(tenant=tenant, code=code, name=code)

            for code in inactive:
                Currency.objects.create(tenant=tenant, code=code, name=code, is_active=False)

    def rate_rows(self, tenant):
        with tenant_context(tenant.id):
            return {
                (r.currency.code, r.valid_from): (r.rate, r.source)
                for r in ExchangeRate.objects.select_related('currency')
            }

    def sync(self, tenant, cbu_rates):
        with tenant_context(tenant.id):
            return sync_rates_from_cbu(tenant, cbu_rates)


class SyncRatesTests(SyncTestBase):

    def test_creates_rates_for_enabled_currencies(self):
        self.add_currencies(self.tenant, 'USD', 'EUR')

        result = self.sync(self.tenant, rates(USD='11783.47', EUR='13688.86', RUB='139.70'))

        self.assertEqual(result.created, ['EUR', 'USD'])
        self.assertEqual(result.valid_from, DAY)
        self.assertEqual(
            self.rate_rows(self.tenant),
            {
                ('USD', DAY): (D('11783.47'), CBU_SOURCE),
                ('EUR', DAY): (D('13688.86'), CBU_SOURCE),
            },
        )

    def test_does_not_create_currencies_tenant_did_not_enable(self):
        """Bank 70+ valyuta beradi — faqat tashkilot qo'shganlari yoziladi."""
        self.add_currencies(self.tenant, 'USD')

        self.sync(self.tenant, rates(USD='11783.47', RUB='139.70'))

        with tenant_context(self.tenant.id):
            self.assertFalse(Currency.objects.filter(code='RUB').exists())

    def test_inactive_currency_skipped(self):
        self.add_currencies(self.tenant, 'USD', inactive=['EUR'])

        result = self.sync(self.tenant, rates(USD='11783.47', EUR='13688.86'))

        self.assertEqual(result.created, ['USD'])

    def test_currency_not_published_by_bank_reported(self):
        self.add_currencies(self.tenant, 'USD', 'XAU')

        result = self.sync(self.tenant, rates(USD='11783.47'))

        self.assertEqual(result.missing, ['XAU'])

    def test_second_run_writes_nothing(self):
        """Jadval kuniga uch marta ishlaydi — takroriy chaqiruv xavfsiz bo'lishi shart."""
        self.add_currencies(self.tenant, 'USD')
        self.sync(self.tenant, rates(USD='11783.47'))

        result = self.sync(self.tenant, rates(USD='11783.47'))

        self.assertEqual(result.created, [])
        self.assertEqual(result.already_present, ['USD'])
        self.assertEqual(len(self.rate_rows(self.tenant)), 1)

    def test_manual_rate_never_overwritten(self):
        """Buxgalter o'sha kunga o'z kursini kiritgan bo'lsa, bank kursi uni bosmaydi."""
        self.add_currencies(self.tenant, 'USD')

        with tenant_context(self.tenant.id):
            ExchangeRate.objects.create(
                tenant=self.tenant, currency=Currency.objects.get(code='USD'),
                rate=D('11900'), valid_from=DAY, source='Qo\'lda',
            )

        result = self.sync(self.tenant, rates(USD='11783.47'))

        self.assertEqual(result.already_present, ['USD'])
        self.assertEqual(self.rate_rows(self.tenant)[('USD', DAY)], (D('11900'), 'Qo\'lda'))

    def test_non_uzs_base_currency_skipped(self):
        """Bank kurslari so'mga nisbatan — asosiy valyutasi dollar bo'lsa yozilmaydi."""
        tenant = Tenant.objects.create(name='Dubay', slug='cbu-usd', base_currency='USD')

        with tenant_context(tenant.id):
            Currency.objects.create(tenant=tenant, code='USD', name='Dollar', is_base=True)
            Currency.objects.create(tenant=tenant, code='EUR', name='Yevro')

        result = self.sync(tenant, rates(EUR='13688.86'))

        self.assertIn('USD', result.skipped_reason)
        self.assertEqual(self.rate_rows(tenant), {})

    def test_synced_rate_used_by_rate_on(self):
        """Yozilgan kurs tannarx hisobida haqiqatan ishlatiladi."""
        self.add_currencies(self.tenant, 'USD')

        with tenant_context(self.tenant.id):
            ExchangeRate.objects.create(
                tenant=self.tenant, currency=Currency.objects.get(code='USD'),
                rate=D('11000'), valid_from=date(2026, 8, 1), source='Qo\'lda',
            )

            # Sinxronlashdan oldin: bugungi hujjat bir oy oldingi kursni oladi
            self.assertEqual(pricing.rate_on('USD', DAY, self.tenant), D('11000'))

        self.sync(self.tenant, rates(USD='11783.47'))

        with tenant_context(self.tenant.id):
            self.assertEqual(pricing.rate_on('USD', DAY, self.tenant), D('11783.47'))


class SyncAllTenantsTests(SyncTestBase):

    def test_each_tenant_gets_own_rows(self):
        """RLS ostida har tashkilot faqat o'z valyutalariga yozadi."""
        self.add_currencies(self.tenant, 'USD')
        self.add_currencies(self.other, 'EUR')

        summary = sync_all_tenants(rates(USD='11783.47', EUR='13688.86'))

        self.assertEqual(summary['cbu-a']['created'], ['USD'])
        self.assertEqual(summary['cbu-b']['created'], ['EUR'])
        self.assertEqual(set(self.rate_rows(self.tenant)), {('USD', DAY)})
        self.assertEqual(set(self.rate_rows(self.other)), {('EUR', DAY)})

    def test_failure_in_one_tenant_does_not_stop_others(self):
        self.add_currencies(self.tenant, 'USD')
        self.add_currencies(self.other, 'USD')

        real = sync_rates_from_cbu

        def flaky(tenant, cbu_rates):
            if tenant.slug == 'cbu-a':
                raise RuntimeError('buzuq ma\'lumot')
            return real(tenant, cbu_rates)

        with mock.patch('apps.pricing.tasks.sync_rates_from_cbu', side_effect=flaky):
            summary = sync_all_tenants(rates(USD='11783.47'))

        self.assertIn('error', summary['cbu-a'])
        self.assertEqual(summary['cbu-b']['created'], ['USD'])

    def test_inactive_tenant_skipped(self):
        self.add_currencies(self.other, 'USD')
        self.other.is_active = False
        self.other.save()

        summary = sync_all_tenants(rates(USD='11783.47'))

        self.assertNotIn('cbu-b', summary)

    def test_task_fetches_once_for_all_tenants(self):
        self.add_currencies(self.tenant, 'USD')
        self.add_currencies(self.other, 'USD')

        with mock.patch('apps.pricing.tasks.fetch_rates', return_value=rates(USD='1')) as fetch:
            sync_cbu_rates()

        fetch.assert_called_once_with(None)

    def test_task_passes_date(self):
        with mock.patch('apps.pricing.tasks.fetch_rates', return_value=rates(USD='1')) as fetch:
            sync_cbu_rates('2026-09-01')

        fetch.assert_called_once_with(date(2026, 9, 1))

    def test_task_retries_on_bank_error(self):
        """Bank sayti ishlamasa vazifa qayta urinadi, tashkilotlarga tegmaydi."""
        self.assertIn(CbuError, sync_cbu_rates.autoretry_for)
        self.assertGreater(sync_cbu_rates.max_retries, 0)


class SyncCommandTests(SyncTestBase):

    def test_command_syncs_current(self):
        self.add_currencies(self.tenant, 'USD')
        out = io.StringIO()

        with mock.patch('apps.pricing.management.commands.sync_exchange_rates.fetch_rates',
                        return_value=rates(USD='11783.47')):
            call_command('sync_exchange_rates', stdout=out)

        self.assertIn('yozildi: USD', out.getvalue())

    def test_command_date_range_fetches_each_day(self):
        with mock.patch('apps.pricing.management.commands.sync_exchange_rates.fetch_rates',
                        return_value=rates(USD='1')) as fetch:
            call_command('sync_exchange_rates', '--from', '2026-09-01', '--to', '2026-09-03',
                         stdout=io.StringIO())

        self.assertEqual(
            [c.args[0] for c in fetch.call_args_list],
            [date(2026, 9, 1), date(2026, 9, 2), date(2026, 9, 3)],
        )

    def test_command_rejects_bad_ranges(self):
        for args in [
            ['--from', '2026-09-05', '--to', '2026-09-01'],
            ['--date', '2026-09-01', '--from', '2026-09-01'],
            ['--from', '2020-01-01', '--to', '2026-01-01'],
        ]:
            with self.subTest(args=args):
                with self.assertRaises(CommandError):
                    call_command('sync_exchange_rates', *args, stdout=io.StringIO())

    def test_command_reports_bank_error(self):
        with mock.patch('apps.pricing.management.commands.sync_exchange_rates.fetch_rates',
                        side_effect=CbuError('ulanib bo\'lmadi')):
            with self.assertRaises(CommandError):
                call_command('sync_exchange_rates', stdout=io.StringIO())


# ---------------------------------------------------------------------
# API — sozlamalardagi tugma
# ---------------------------------------------------------------------

class SyncApiTests(SyncTestBase):
    """Haqiqiy JWT bilan to'liq so'rov.

    `force_authenticate` bu yerda yaramaydi: `TenantMiddleware` tokenni
    DRF'dan oldin o'zi o'qiydi va tenantni shundan oladi. Soxta
    autentifikatsiya bilan tenant o'rnatilmay, RLS bo'sh natija berardi —
    test esa noto'g'ri sababdan o'tib yoki yiqilib qolardi.
    """

    URL = '/api/exchange-rates/sync-cbu/'

    def client_for(self, role):
        user = User.objects.create_user(username=f'u-{role}', password='x')
        Membership.objects.create(tenant=self.tenant, user=user, role=role)

        client = APIClient()
        token = RefreshToken.for_user(user).access_token
        client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')

        return client

    def setUp(self):
        self.add_currencies(self.tenant, 'USD')

    def test_admin_can_sync(self):
        client = self.client_for(Membership.Role.MANAGER)

        with mock.patch('apps.pricing.api.fetch_rates', return_value=rates(USD='11783.47')):
            response = client.post(self.URL)

        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()['created'], ['USD'])
        self.assertIn(('USD', DAY), self.rate_rows(self.tenant))

    def test_non_admin_forbidden(self):
        for role in [Membership.Role.STOREKEEPER, Membership.Role.VIEWER]:
            with self.subTest(role=role):
                client = self.client_for(role)

                with mock.patch('apps.pricing.api.fetch_rates') as fetch:
                    response = client.post(self.URL)

                self.assertEqual(response.status_code, 403)
                fetch.assert_not_called()

    def test_bank_error_returns_502(self):
        client = self.client_for(Membership.Role.OWNER)

        with mock.patch('apps.pricing.api.fetch_rates', side_effect=CbuError('ulanib bo\'lmadi')):
            response = client.post(self.URL)

        self.assertEqual(response.status_code, 502)
        self.assertIn('ulanib', response.json()['detail'])

    def test_only_own_tenant_written(self):
        """Tugma boshqa tashkilotning kursiga tegmaydi."""
        self.add_currencies(self.other, 'USD')
        client = self.client_for(Membership.Role.OWNER)

        with mock.patch('apps.pricing.api.fetch_rates', return_value=rates(USD='11783.47')):
            client.post(self.URL)

        self.assertEqual(self.rate_rows(self.other), {})


class BeatScheduleTests(SimpleTestCase):

    def test_scheduled_tasks_are_registered(self):
        """Jadvaldagi har vazifa nomi haqiqatan mavjud bo'lishi kerak.

        Nom xato bo'lsa (vazifa ko'chirilgan yoki qayta nomlangan), beat
        uni navbatga qo'yaveradi, worker esa "noma'lum vazifa" deb
        tashlab yuboradi — kurs yangilanmay qoladi va buni hech kim
        sezmaydi.
        """
        import importlib

        from django.conf import settings

        from config.celery import app

        # `app.autodiscover_tasks()` bilan bir xil: har ilovaning tasks.py si.
        # `app.loader.import_default_modules()` ishlatilmaydi — Celery'ning
        # Django moslamasi u yerda model tekshiruvini ishga tushiradi va
        # bazaga murojaat qiladi, SimpleTestCase esa buni taqiqlaydi.
        for app_name in settings.INSTALLED_APPS:
            try:
                importlib.import_module(f'{app_name}.tasks')
            except ModuleNotFoundError as exc:
                if exc.name != f'{app_name}.tasks':
                    raise  # tasks.py bor, lekin ichida buzuq import

        for name, entry in settings.CELERY_BEAT_SCHEDULE.items():
            with self.subTest(schedule=name):
                self.assertIn(entry['task'], app.tasks)
