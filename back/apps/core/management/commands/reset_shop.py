"""Do'kon bazasini butunlay tozalaydi — haqiqiy ish boshlanishidan oldin.

Sinov davrida kiritilgan tovar, kirim, sotuv va xodimlar qoladi va
hisobotni buzadi. Bu buyruq hammasini o'chiradi: do'kon birinchi kunini
toza bazadan boshlaydi.

**Bu amalni ortga qaytarib bo'lmaydi.** Shuning uchun:

- buyruq tasdiqlashsiz ishlamaydi (do'kon nomini yozish so'raladi);
- ishga tushirishdan oldin zaxira nusxa olish eslatiladi
  (`docs/deployment.md`, 7-bo'lim).

Tozalashdan keyin ombor va savdo zali qaytadan yaratiladi — ularsiz
ilova umuman ishlamaydi. Do'kon sozlamalari (nomi, yorliq va chek
o'lchamlari, chegirma chegarasi) ham saqlanib qoladi: ular sinov
ma'lumoti emas, qurilmaga moslab sozlangan qiymatlar. Xodimlar esa
qaytarilmaydi: administratorni qo'lda yaratasiz.

    docker compose exec backend python manage.py reset_shop
    docker compose exec backend python manage.py createsuperuser
"""

import shutil
from pathlib import Path

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db import connection
from django.forms.models import model_to_dict

from apps.core.models import ShopSettings
from apps.inventory.models import Location


class Command(BaseCommand):
    help = 'Bazani butunlay tozalaydi: tovar, hujjatlar va xodimlar o‘chadi'

    def add_arguments(self, parser):
        parser.add_argument(
            '--yes',
            action='store_true',
            help='Tasdiqlash so‘ralmaydi. Faqat skriptdan chaqirilganda ishlating.',
        )
        parser.add_argument(
            '--keep-media',
            action='store_true',
            help='Yuklangan rasmlar o‘chirilmaydi.',
        )

    def handle(self, *args, **options):
        database = connection.settings_dict
        name = database.get('NAME', '?')
        host = database.get('HOST') or 'localhost'

        shop = ShopSettings.load()
        expected = shop.shop_name.strip()

        # Sozlamalar `flush` da o'chadi va standart qiymat bilan qayta
        # yaratilardi. Chekda «Do‘kon» deb chiqib qolmasin, yorliq
        # o'lchami ham adashmasin deb ular saqlab qo'yiladi.
        kept = model_to_dict(shop, exclude=['id'])

        self.stdout.write('')
        self.stdout.write(self.style.WARNING('BAZA BUTUNLAY TOZALANADI'))
        self.stdout.write('')
        self.stdout.write(f'  Baza:  {name} ({host})')
        self.stdout.write(f'  Do‘kon: {expected}')
        self.stdout.write('')
        self.stdout.write('  O‘chadi: mahsulot, qoldiq, kirim, sotuv, qaytarish,')
        self.stdout.write('           ko‘chirish, sanoq, hisobdan chiqarish, xarajat,')
        self.stdout.write('           ta’minotchi, kategoriya, o‘lcham, rang, XODIMLAR')

        if not options['keep_media']:
            self.stdout.write('           va yuklangan rasmlar')

        self.stdout.write('')
        self.stdout.write('  Qoladi:  ombor va savdo zali, do‘kon sozlamalari')
        self.stdout.write(f'           (do‘kon nomi: {expected})')
        self.stdout.write('')
        self.stdout.write(self.style.WARNING('  Ortga qaytarib bo‘lmaydi. Zaxira nusxa oldingizmi?'))
        self.stdout.write('')

        if not options['yes']:
            answer = input(f'Davom etish uchun do‘kon nomini yozing («{expected}»): ')

            if answer.strip() != expected:
                raise CommandError('Nom to‘g‘ri kelmadi — hech narsa o‘chirilmadi.')

        # `flush` hamma jadvalni bo'shatadi va ketma-ket raqamlarni
        # noldan boshlaydi. Undan keyin Django ruxsatlarni o'zi tiklaydi.
        call_command('flush', '--no-input', verbosity=0)

        if not options['keep_media']:
            self._clear_media()

        # Ombor, zal va sozlamalar do'konning tuzilishi: ular yo'q bo'lsa
        # na tovar qabul qilish, na sotish mumkin. Ikkala usul ham
        # yo'q bo'lsa o'zi yaratadi.
        Location.warehouse()
        Location.shop()

        ShopSettings.objects.update_or_create(pk=1, defaults=kept)

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('Baza tozalandi.'))
        self.stdout.write('')
        self.stdout.write('Keyingi qadam — administrator yarating:')
        self.stdout.write('  python manage.py createsuperuser')
        self.stdout.write('')

    def _clear_media(self):
        """Yuklangan rasmlarni o'chiradi.

        Bazadagi qatorlar o'chgach, fayllar egasiz qolib diskni
        to'ldiradi va ularni keyin kimdir qo'lda topib o'chirishi
        kerak bo'lardi.
        """
        root = Path(settings.MEDIA_ROOT)

        if not root.exists():
            return

        for item in root.iterdir():
            if item.is_dir():
                shutil.rmtree(item, ignore_errors=True)
            else:
                item.unlink(missing_ok=True)

        self.stdout.write('Yuklangan rasmlar o‘chirildi.')
