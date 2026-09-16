"""Loyiha holati: migratsiyalar va namuna ma'lumotlari buyrug'i."""

from io import StringIO

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings

from apps.accounts.models import User
from apps.catalog.models import Product, Variant
from apps.sales.models import Sale


class MigrationStateTests(TestCase):

    def test_no_pending_migrations(self):
        """`makemigrations --check` toza bo'lishi kerak.

        Model bilan migratsiya ajralib qolsa, xavfli holat tug'iladi:
        cheklov bazada bor, model holatida esa yo'q. Keyingi
        `makemigrations` uni jimgina o'chirib yuboradigan migratsiya
        yozadi.
        """
        output = StringIO()

        try:
            call_command(
                'makemigrations', '--check', '--dry-run', stdout=output, stderr=output
            )
        except SystemExit:
            self.fail(
                'Modellar va migratsiyalar mos emas — `makemigrations` ni '
                f'ishga tushiring:\n{output.getvalue()}'
            )


class SeedDemoTests(TestCase):
    """Namuna ma'lumotlari faqat ishlab chiqish uchun."""

    def test_refuses_when_debug_is_off(self):
        """Serverda namuna xodim yaratilmasligi kerak — paroli ochiq."""
        # Testlarda DEBUG allaqachon False
        with self.assertRaises(CommandError) as caught:
            call_command('seed_demo', stdout=StringIO(), stderr=StringIO())

        self.assertIn('DEBUG', str(caught.exception))
        self.assertEqual(User.objects.count(), 0)

    @override_settings(DEBUG=True)
    def test_creates_a_working_shop(self):
        output = StringIO()

        call_command('seed_demo', '--force', stdout=output, stderr=output)

        self.assertEqual(
            set(User.objects.values_list('username', flat=True)), {'admin', 'kassir'}
        )
        self.assertEqual(Product.objects.count(), 4)
        self.assertTrue(Variant.objects.exists())

        # Kirim tasdiqlangan — qoldiq bor
        self.assertTrue(all(
            variant.stock_quantity > 0 for variant in Variant.objects.all()
        ))

        # Ikkita sotuv: biri naqd, biri karta
        self.assertEqual(Sale.objects.count(), 2)

        # Ogohlantirish ko'rinadi
        self.assertIn('faqat lokal', output.getvalue())

    @override_settings(DEBUG=True)
    def test_refuses_to_overwrite_without_force(self):
        call_command('seed_demo', '--force', stdout=StringIO(), stderr=StringIO())

        with self.assertRaises(CommandError) as caught:
            call_command('seed_demo', stdout=StringIO(), stderr=StringIO())

        self.assertIn('--force', str(caught.exception))
