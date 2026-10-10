"""Telegram bildirishnomalari.

Asosiy talab: xabar **hech qachon ishni to'xtatmaydi**. Telegram
javob bermasa ham sotuv yakunlanishi kerak. Ikkinchi talab:
tranzaksiya bekor bo'lsa xabar ketmasligi kerak.
"""

from decimal import Decimal
from io import StringIO
from unittest import mock

from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.test import TestCase, override_settings

from apps.core import telegram
from apps.core.factories import (
    api_client,
    create_admin,
    create_product,
    receive_stock,
)
from apps.inventory.models import Location
from apps.inventory.services import create_write_off
from apps.sales.services import create_sale, void_sale

SETTINGS = {'TELEGRAM_BOT_TOKEN': 'sinov-token', 'TELEGRAM_CHAT_IDS': '42,77'}


class TelegramModuleTests(TestCase):

    def test_silent_without_a_token(self):
        """Ishlab chiqish kompyuterida hech narsa yuborilmaydi."""
        with override_settings(TELEGRAM_BOT_TOKEN='', TELEGRAM_CHAT_IDS=''):
            with mock.patch('apps.core.telegram._dispatch') as send:
                telegram.notify('salom')

            self.assertFalse(telegram.configured())
            send.assert_not_called()

    @override_settings(**SETTINGS)
    def test_money_is_grouped_like_on_the_receipt(self):
        self.assertEqual(telegram.money(Decimal('1234567.00')), '1 234 567')

    @override_settings(**SETTINGS)
    def test_every_recipient_gets_the_message(self):
        """Do'konda bir necha rahbar bor, har biri o'z telefonida ko'radi."""
        self.assertEqual(telegram.chats(), ['42', '77'])

        with mock.patch('urllib.request.urlopen') as send:
            telegram._send('salom')

        self.assertEqual(send.call_count, 2)

    @override_settings(**SETTINGS)
    def test_a_broken_connection_does_not_raise(self):
        """Internet uzilgani sotuvni to'xtatmasligi kerak."""
        with mock.patch('urllib.request.urlopen', side_effect=OSError('tarmoq yo‘q')):
            telegram._send('salom')

    @override_settings(**SETTINGS)
    def test_one_broken_chat_does_not_stop_the_others(self):
        calls = []

        def answer(request, timeout=None):
            calls.append(request)

            if len(calls) == 1:
                raise OSError('bu hisob bloklagan')

            raise OSError('qolganiga ham urinildi')

        with mock.patch('urllib.request.urlopen', side_effect=answer):
            telegram._send('salom')

        self.assertEqual(len(calls), 2)


@override_settings(**SETTINGS)
class NotificationTests(TestCase):
    """Qaysi hodisalar xabar yuboradi."""

    def setUp(self):
        self.admin = create_admin()
        self.product = create_product(sizes=('M',), colors=('qora',))
        self.variant = self.product.variants.get()

        receive_stock(self.variant, 5, '100000')

        # `_dispatch` to'xtatiladi: oqim ham, tarmoq ham kerak emas
        patcher = mock.patch('apps.core.telegram._dispatch')

        self.send = patcher.start()
        self.addCleanup(patcher.stop)

    def messages(self) -> str:
        return '\n'.join(call.args[0] for call in self.send.call_args_list)

    def sell(self, quantity=1):
        """Bitta sotuv. `on_commit` testda o'zi ishlamaydi — qo'lda yuritiladi."""
        with self.captureOnCommitCallbacks(execute=True):
            return create_sale(
                user=self.admin,
                lines=[{'variant': self.variant, 'quantity': quantity}],
                cash_amount=Decimal('250000'),
            )

    def test_a_sale_is_announced(self):
        self.sell()

        self.assertIn('Sotuv', self.messages())
        self.assertIn('Kassir', self.messages())

    def test_a_voided_receipt_is_announced(self):
        sale = self.sell()

        self.send.reset_mock()

        with self.captureOnCommitCallbacks(execute=True):
            void_sale(sale, user=self.admin)

        self.assertIn('bekor qilindi', self.messages())

    def test_a_write_off_is_announced(self):
        with self.captureOnCommitCallbacks(execute=True):
            create_write_off(
            variant=self.variant,
                quantity=1,
                reason='Yirtilgan',
                location=Location.shop(),
                user=self.admin,
            )

        self.assertIn('Hisobdan chiqarildi', self.messages())
        self.assertIn('Yirtilgan', self.messages())

    def test_a_price_change_is_announced(self):
        with self.captureOnCommitCallbacks(execute=True):
            api_client(self.admin).patch(
                f'/api/products/{self.product.pk}/', {'sale_price': '999000'}, format='json'
            )

        self.assertIn('Narx o‘zgardi', self.messages())
        self.assertIn('999 000', self.messages())

    def test_nothing_is_sent_when_the_sale_fails(self):
        """Tranzaksiya bekor bo'lsa xabar ham ketmaydi."""
        with self.assertRaises(ValidationError):
            self.sell(quantity=99)

        self.send.assert_not_called()


@override_settings(**SETTINGS)
class TelegramTestCommandTests(TestCase):
    """`telegram_test` buyrug'i har hisobni alohida sinaydi."""

    def run_command(self):
        out = StringIO()

        call_command('telegram_test', stdout=out)

        return out.getvalue()

    def test_every_recipient_is_reported(self):
        with mock.patch('apps.core.telegram.send_to', return_value=(True, 'yuborildi')) as send:
            output = self.run_command()

        self.assertEqual(send.call_count, 2)
        self.assertIn('42', output)
        self.assertIn('77', output)
        self.assertIn('Hammasiga yetib bordi', output)

    def test_the_reason_is_shown(self):
        """«/start» bosilmagan hisob jimgina o'tib ketmasligi kerak."""
        def answer(chat, text):
            return (False, 'chat not found') if chat == '42' else (True, 'yuborildi')

        with mock.patch('apps.core.telegram.send_to', side_effect=answer):
            output = self.run_command()

        self.assertIn('chat not found', output)
        self.assertIn('1 ta hisobga yetib bormadi', output)

    def test_without_settings_it_explains_what_is_missing(self):
        with override_settings(TELEGRAM_BOT_TOKEN='', TELEGRAM_CHAT_IDS=''):
            output = self.run_command()

        self.assertIn('TELEGRAM_BOT_TOKEN qo‘yilmagan', output)
        self.assertIn('.env.production', output)
