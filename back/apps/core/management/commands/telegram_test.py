"""Telegram bildirishnomalarini tekshiradi.

Sozlash to'g'ri qilinganini bilishning yagona ishonchli yo'li — haqiqiy
xabar yuborib ko'rish. Odatda bitta narsa esdan chiqadi: qabul
qiluvchi botga `/start` bosmagan bo'ladi va Telegram xabarni rad
etadi. Kundalik ishda bu jimgina o'tadi (xato faqat jurnalga
yoziladi), shuning uchun shu buyruq har hisobni alohida sinaydi va
sababini aytadi.

    docker compose exec backend python manage.py telegram_test
"""

from django.core.management.base import BaseCommand

from apps.core import telegram


class Command(BaseCommand):
    help = 'Har bir qabul qiluvchiga sinov xabarini yuboradi'

    def add_arguments(self, parser):
        parser.add_argument(
            '--text',
            default='Sinov xabari — bildirishnomalar ishlayapti.',
            help='Yuboriladigan matn',
        )
        parser.add_argument(
            '--photo',
            action='store_true',
            help='Tovar rasmi bilan yuboradi (sotuvdagi kabi)',
        )

    def handle(self, *args, **options):
        token = getattr(telegram.settings, 'TELEGRAM_BOT_TOKEN', '')
        recipients = telegram.chats()

        self.stdout.write('')

        if not token:
            self.stdout.write(self.style.ERROR('TELEGRAM_BOT_TOKEN qo‘yilmagan.'))

        if not recipients:
            self.stdout.write(self.style.ERROR('TELEGRAM_CHAT_IDS qo‘yilmagan.'))

        if not telegram.configured():
            self.stdout.write('')
            self.stdout.write('Sozlama serverda `.env.production` da turadi:')
            self.stdout.write('  TELEGRAM_BOT_TOKEN=...')
            self.stdout.write('  TELEGRAM_CHAT_IDS=...,...')
            self.stdout.write('')
            self.stdout.write('O‘zgartirgandan keyin: docker compose up -d')
            self.stdout.write('')

            return

        self.stdout.write(f'Token bor, qabul qiluvchilar: {len(recipients)} ta')

        photo = self._photo() if options['photo'] else b''

        if options['photo']:
            self.stdout.write(
                f'Rasm: {len(photo)} bayt JPEG' if photo else 'Rasm topilmadi — matn yuboriladi'
            )

        self.stdout.write('')

        failed = 0
        file_id = ''

        for chat in recipients:
            if photo:
                ok, detail, sent = telegram.send_photo_to(
                    chat, options['text'], photo=b'' if file_id else photo, file_id=file_id
                )
                file_id = file_id or (sent if ok else '')
            else:
                ok, detail = telegram.send_to(chat, options['text'])

            if ok:
                self.stdout.write(self.style.SUCCESS(f'  {chat:<14} {detail}'))
            else:
                failed += 1
                self.stdout.write(self.style.ERROR(f'  {chat:<14} {detail}'))

        self.stdout.write('')

        if failed:
            self.stdout.write(
                self.style.WARNING(
                    f'{failed} ta hisobga yetib bormadi. Eng ko‘p uchraydigan sabab: '
                    'o‘sha odam botni topib «Start» bosmagan.'
                )
            )

            link = telegram.bot_link()

            if link:
                self.stdout.write('')
                self.stdout.write(f'Shu havolani ularga yuboring: {link}')
                self.stdout.write('Ochib «Start» bosishsa yetarli.')
        else:
            self.stdout.write(self.style.SUCCESS('Hammasiga yetib bordi.'))

        self.stdout.write('')

    def _photo(self) -> bytes:
        """Sinov uchun rasm: bazadagi birinchi mahsulot surati.

        Aynan haqiqiy yo'l sinaladi — WebP fayl JPEG ga o'giriladi va
        `multipart` bilan yuklanadi. Rasm bo'lmasa bo'sh qaytadi.
        """
        from apps.catalog.models import ProductImage

        image = ProductImage.objects.order_by('id').first()

        return telegram.photo_bytes(image.medium) if image else b''
