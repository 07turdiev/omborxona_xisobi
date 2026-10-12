"""Loyiha holati: migratsiyalar va namuna ma'lumotlari buyrug'i."""

import base64
import shutil
import tempfile
from io import BytesIO, StringIO
from unittest import mock

from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, TransactionTestCase, override_settings
from PIL import Image, ImageDraw

from apps.accounts.models import User
from apps.catalog.models import Product, Variant
from apps.core.factories import create_admin, create_product, receive_stock
from apps.core.models import ShopSettings
from apps.inventory.models import Location, StockMovement, VariantStock
from apps.purchases.models import Purchase
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


class ShopSettingsTests(TestCase):
    """Chek qog'ozi o'lchami — drayverdagi qog'oz bilan bir xil bo'lishi kerak."""

    def setUp(self):
        from apps.core.factories import api_client, create_admin

        self.client_admin = api_client(create_admin())

    def test_defaults(self):
        response = self.client_admin.get('/api/settings/')

        self.assertEqual(response.status_code, 200, response.content)

        body = response.json()

        self.assertEqual(body['receipt_width_mm'], 80)
        self.assertEqual(body['receipt_page_height_mm'], 110)

    def test_admin_can_change_paper(self):
        response = self.client_admin.patch(
            '/api/settings/',
            {'receipt_width_mm': 58, 'receipt_page_height_mm': 150},
            format='json',
        )

        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()['receipt_width_mm'], 58)
        self.assertEqual(response.json()['receipt_page_height_mm'], 150)

    def test_impossible_paper_is_rejected(self):
        for field, value in (
            ('receipt_width_mm', 10),
            ('receipt_width_mm', 500),
            ('receipt_page_height_mm', 5),
            ('receipt_page_height_mm', 900),
        ):
            response = self.client_admin.patch(
                '/api/settings/', {field: value}, format='json'
            )

            self.assertEqual(response.status_code, 400, f'{field}={value}')


def _png(size, draw=None, mode='RGB', background='white') -> SimpleUploadedFile:
    """Sinov rasmi: `draw(ImageDraw)` chizadi."""
    image = Image.new(mode, size, background)

    if draw:
        draw(ImageDraw.Draw(image))

    buffer = BytesIO()
    image.save(buffer, format='PNG')

    return SimpleUploadedFile('logo.png', buffer.getvalue(), content_type='image/png')


def _square() -> SimpleUploadedFile:
    """Eng oddiy logotip: oq fonda qora kvadrat."""
    return _png((100, 100), lambda d: d.rectangle((10, 10, 90, 90), fill='black'))


def _rows(logo) -> list[bytes]:
    """Logotip nuqtalari qatorma-qator (1 — qora)."""
    raster = base64.b64decode(logo['raster'])
    step = logo['width'] // 8

    return [raster[index : index + step] for index in range(0, len(raster), step)]


class ShopLogoTests(TestCase):
    """Chek logotipi: yuklangan rasm chek printeri chiza oladigan nuqtalarga aylanadi."""

    def setUp(self):
        from apps.core.factories import api_client, create_admin, create_cashier

        self.admin = api_client(create_admin())
        self.cashier = api_client(create_cashier())

    def upload(self, file, client=None):
        data = {} if file is None else {'logo': file}

        return (client or self.admin).post('/api/settings/logo/', data, format='multipart')

    def test_logo_fits_receipt_and_is_ready_for_printer(self):
        wide = _png((800, 300), lambda d: d.rectangle((100, 50, 700, 250), fill='black'))
        response = self.upload(wide)

        self.assertEqual(response.status_code, 200, response.content)

        logo = response.json()['receipt_logo']

        # Eni 8 ga karrali (printer qatorni baytlab oladi) va 48 × 24 mm dan oshmaydi
        self.assertEqual(logo['width'] % 8, 0)
        self.assertLessEqual(logo['width'], 384)
        self.assertLessEqual(logo['height'], 192)
        self.assertEqual(len(base64.b64decode(logo['raster'])), logo['width'] // 8 * logo['height'])
        self.assertTrue(logo['png'].startswith('data:image/png;base64,'))

        # Hamma o'qiydi: kassa chekni shu yerdan oladi
        self.assertEqual(self.cashier.get('/api/settings/').json()['receipt_logo'], logo)

    def test_empty_margins_are_cut(self):
        """Rasm chetidagi bo'sh joy kesiladi — logotip chekda keraksiz kichik chiqmaydi."""
        logo = self.upload(
            _png((1000, 1000), lambda d: d.rectangle((450, 475, 549, 524), fill='black'))
        ).json()['receipt_logo']

        # 100 × 50 lik to'rtburchak qoldi va chegaragacha kattalashdi
        self.assertEqual((logo['width'], logo['height']), (384, 192))
        self.assertTrue(all(byte == 0xFF for row in _rows(logo) for byte in row))

    def test_transparent_background_is_white_paper(self):
        """Shaffof nuqtalar odatda (0, 0, 0, 0) — kulrangga o'tganda qora bo'lmasin."""
        logo = self.upload(
            _png(
                (400, 400),
                lambda d: d.ellipse((0, 0, 399, 399), fill=(0, 0, 0, 255)),
                mode='RGBA',
                background=(0, 0, 0, 0),
            )
        ).json()['receipt_logo']

        rows = _rows(logo)

        # Doiraning burchaklari — shaffof edi, oq bo'lishi kerak
        self.assertEqual(rows[0][0] & 0x80, 0, 'chap tepa burchak qora chiqdi')
        # Markazi — qora
        middle = rows[len(rows) // 2]
        self.assertEqual(middle[len(middle) // 2], 0xFF)

    def test_cashier_cannot_change_logo(self):
        response = self.upload(_square(), self.cashier)

        self.assertEqual(response.status_code, 403)

    def test_bad_files_are_rejected(self):
        not_image = SimpleUploadedFile('logo.png', b'rasm emas', content_type='image/png')

        for file, reason in (
            (not_image, 'rasm emas'),
            (_png((200, 100)), 'chiziladigan narsa'),
        ):
            response = self.upload(file)

            self.assertEqual(response.status_code, 400, reason)
            self.assertIn(reason, response.json()['logo'][0])

        self.assertEqual(self.upload(None).status_code, 400, 'fayl yo‘q')
        self.assertIsNone(ShopSettings.load().receipt_logo)

    def test_logo_can_be_removed(self):
        self.upload(_square())

        response = self.admin.delete('/api/settings/logo/')

        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.json()['receipt_logo'])
        self.assertIsNone(ShopSettings.load().receipt_logo)

    def test_logo_is_not_changed_through_settings_form(self):
        """Sozlamalar shakli logotipni bilmaydi: saqlanganda u o'chib ketmasin."""
        self.upload(_square())

        response = self.admin.patch(
            '/api/settings/', {'shop_name': 'MADLEN SEN', 'receipt_logo': None}, format='json'
        )

        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()['shop_name'], 'MADLEN SEN')
        self.assertIsNotNone(response.json()['receipt_logo'])


class SeedDemoTests(TestCase):
    """Namuna ma'lumotlari faqat ishlab chiqish uchun."""

    @classmethod
    def setUpClass(cls):
        """Namuna rasmlari vaqtinchalik papkaga tushsin."""
        super().setUpClass()

        cls.media = tempfile.mkdtemp()
        cls.override = override_settings(MEDIA_ROOT=cls.media)
        cls.override.enable()

    @classmethod
    def tearDownClass(cls):
        cls.override.disable()
        shutil.rmtree(cls.media, ignore_errors=True)
        super().tearDownClass()

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
        self.assertEqual(Product.objects.count(), 12)
        self.assertTrue(Variant.objects.exists())

        # Har tovarda bitta asosiy rasm: rasmsiz tovar bo'lmaydi
        self.assertTrue(all(
            product.images.filter(is_primary=True).count() == 1
            for product in Product.objects.all()
        ))

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


class ResetShopTests(TransactionTestCase):
    """Bazani tozalash: hammasi o'chadi, tuzilish qoladi.

    `TransactionTestCase` ataylab: tozalash `TRUNCATE` bilan ishlaydi,
    uni esa oddiy testning tranzaksiyasi ichida bajarib bo'lmaydi
    («pending trigger events»). Jurnalda `DELETE` ni bloklaydigan
    trigger borligi uchun qator-qator o'chirish ham mumkin emas.
    """

    def setUp(self):
        self.admin = create_admin()
        self.product = create_product()

        receive_stock(self.product.variants.first(), 5, '100000')

    def run_reset(self, **options):
        out = StringIO()

        call_command('reset_shop', '--yes', '--keep-media', stdout=out, **options)

        return out.getvalue()

    def test_everything_goes_including_staff(self):
        self.run_reset()

        self.assertEqual(User.objects.count(), 0)
        self.assertEqual(Product.objects.count(), 0)
        self.assertEqual(Variant.objects.count(), 0)
        self.assertEqual(StockMovement.objects.count(), 0)
        self.assertEqual(VariantStock.objects.count(), 0)
        self.assertEqual(Purchase.objects.count(), 0)

    def test_shop_structure_comes_back(self):
        """Ombor va zalsiz ilova umuman ishlamaydi."""
        self.run_reset()

        self.assertEqual(Location.objects.filter(kind=Location.Kind.WAREHOUSE).count(), 1)
        self.assertEqual(Location.objects.filter(kind=Location.Kind.SHOP).count(), 1)
        self.assertEqual(ShopSettings.objects.count(), 1)

    def test_shop_settings_survive(self):
        """Chekdagi nom va yorliq o'lchami sozlangan qiymat bo'lib qolsin."""
        shop = ShopSettings.load()
        shop.shop_name = 'Madlen sen'
        shop.label_width_mm = 58
        shop.save(update_fields=['shop_name', 'label_width_mm'])

        self.run_reset()

        restored = ShopSettings.load()

        self.assertEqual(restored.shop_name, 'Madlen sen')
        self.assertEqual(restored.label_width_mm, 58)

    def test_wrong_name_changes_nothing(self):
        """Tasdiq noto'g'ri bo'lsa baza tegilmaydi."""
        with mock.patch('builtins.input', return_value='boshqa nom'):
            with self.assertRaises(CommandError):
                call_command('reset_shop', '--keep-media', stdout=StringIO())

        self.assertEqual(Product.objects.count(), 1)
        self.assertEqual(User.objects.count(), 1)

    def test_right_name_clears_the_database(self):
        shop = ShopSettings.load()

        with mock.patch('builtins.input', return_value=shop.shop_name):
            call_command('reset_shop', '--keep-media', stdout=StringIO())

        self.assertEqual(Product.objects.count(), 0)
