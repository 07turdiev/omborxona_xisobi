"""UI testlari uchun alohida baza.

Playwright testlari ilovaga qarshi haqiqiy so'rovlar yuboradi va
mahsulot, kirim, sotuv yaratadi. Ular ishlab chiqish bazasiga tushsa,
ro'yxatlar sinov ma'lumotiga to'lib ketadi — shuning uchun testlar
o'z bazasida yuritiladi (`front/scripts/test-ui.mjs`).

Ikki himoya bor: buyruq faqat `DEBUG=True` da ishlaydi va baza nomida
`test` so'zi bo'lishi shart. Ya'ni ishlab chiqish yoki ishlab chiqarish
bazasi tasodifan ham o'chib ketmaydi.
"""

import psycopg
from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db import connection


class Command(BaseCommand):
    help = 'UI testlari uchun bazani qaytadan yaratadi (nomida "test" bo‘lgan baza)'

    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError('reset_test_db faqat DEBUG=True bo‘lganda ishlaydi.')

        config = settings.DATABASES['default']
        name = config['NAME']

        if 'test' not in name:
            raise CommandError(
                f'«{name}» — test bazasi emas. Nomida "test" bo‘lgan baza kerak, '
                'masalan DATABASE_URL=…/dokon_test_ui'
            )

        # O'z ulanishimiz yopilmasa, bazani o'chirib bo'lmaydi
        connection.close()

        try:
            with psycopg.connect(
                host=config['HOST'] or 'localhost',
                port=config['PORT'] or 5432,
                user=config['USER'],
                password=config['PASSWORD'],
                dbname='postgres',
                autocommit=True,
            ) as maintenance:
                maintenance.execute(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)')
                maintenance.execute(f'CREATE DATABASE "{name}"')
        except psycopg.errors.InsufficientPrivilege as error:
            raise CommandError(
                f'{config["USER"]} foydalanuvchisi baza yarata olmaydi.\n'
                f'Yechim: ALTER ROLE {config["USER"]} CREATEDB;'
            ) from error

        self.stdout.write(f'Baza qaytadan yaratildi: {name}')

        call_command('migrate', verbosity=0)
        call_command('seed_demo', '--force', verbosity=0)

        self.stdout.write(self.style.SUCCESS('Test bazasi tayyor'))
