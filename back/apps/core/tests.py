"""Loyiha holati: modellar va migratsiyalar bir-biriga mos bo'lishi kerak."""

from io import StringIO

from django.core.management import call_command
from django.test import TestCase


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
