"""Katalog testlari: variant matritsasi, shtrix-kod, rasm va katalog API."""

import os
import shutil
import tempfile
from io import BytesIO

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from PIL import Image

from apps.catalog.images import MAX_UPLOAD_BYTES
from apps.catalog.models import Color, Product, ProductImage, Size, Variant
from apps.catalog.services import (
    add_variant,
    ean13_check_digit,
    next_internal_barcode,
    unique_slug,
)
from apps.core.factories import (
    api_client,
    create_admin,
    create_cashier,
    create_product,
    receive_stock,
)
from apps.inventory.models import Location
from apps.inventory.services import create_transfer


def image_upload(name='rasm.jpg', size=(1200, 900), orientation=None) -> SimpleUploadedFile:
    """Sinov uchun haqiqiy JPEG fayl."""
    buffer = BytesIO()
    image = Image.new('RGB', size, '#336699')

    if orientation is None:
        image.save(buffer, format='JPEG')
    else:
        exif = Image.Exif()
        exif[0x0112] = orientation  # Orientation
        image.save(buffer, format='JPEG', exif=exif)

    return SimpleUploadedFile(name, buffer.getvalue(), content_type='image/jpeg')


def is_valid_ean13(code: str) -> bool:
    """Kod 13 xonali va nazorat raqami to'g'rimi."""
    return (
        len(code) == 13
        and code.isdigit()
        and ean13_check_digit(code[:12]) == code[12]
    )


class BarcodeTests(TestCase):

    def test_check_digit_matches_known_codes(self):
        """Nazorat raqami standart namunalarga mos."""
        # Haqiqiy EAN-13 kodlari: oxirgi raqam nazorat raqami
        self.assertEqual(ean13_check_digit('590123412345'), '7')
        self.assertEqual(ean13_check_digit('400638133393'), '1')
        self.assertEqual(ean13_check_digit('978014300723'), '4')

    def test_generated_barcodes_are_valid_and_unique(self):
        codes = {next_internal_barcode() for _ in range(50)}

        self.assertEqual(len(codes), 50)

        for code in codes:
            self.assertTrue(is_valid_ean13(code), code)
            self.assertTrue(code.startswith('200'))


class VariantMatrixTests(TestCase):

    def test_three_sizes_and_two_colors_make_six_variants(self):
        product = create_product(sizes=('S', 'M', 'L'), colors=('qora', 'oq'))

        variants = list(product.variants.all())

        self.assertEqual(len(variants), 6)

        pairs = {(variant.size.name, variant.color.name) for variant in variants}
        self.assertEqual(
            pairs,
            {
                ('S', 'qora'), ('S', 'oq'),
                ('M', 'qora'), ('M', 'oq'),
                ('L', 'qora'), ('L', 'oq'),
            },
        )

        barcodes = {variant.barcode for variant in variants}
        skus = {variant.sku for variant in variants}

        self.assertEqual(len(barcodes), 6)
        self.assertEqual(len(skus), 6)

        for variant in variants:
            self.assertTrue(is_valid_ean13(variant.barcode), variant.barcode)

    def test_product_without_sizes_gets_one_hidden_variant(self):
        product = create_product(name='Sharf')

        self.assertEqual(product.variants.count(), 1)

        variant = product.variants.first()
        self.assertIsNone(variant.size)
        self.assertIsNone(variant.color)

    def test_adding_a_size_creates_only_missing_variants(self):
        """Mavjud variantlar saqlanadi — ularda qoldiq va tarix bo'lishi mumkin."""
        product = create_product(sizes=('S', 'M'), colors=('qora',))
        existing = {variant.pk for variant in product.variants.all()}

        client = api_client(create_admin())
        sizes = list(product.variants.values_list('size_id', flat=True))
        from apps.catalog.models import Size

        large = Size.objects.create(name='L', position=3)

        response = client.patch(
            f'/api/products/{product.pk}/',
            {'size_ids': [*sizes, large.pk], 'color_ids': [product.variants.first().color_id]},
            format='json',
        )

        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(product.variants.count(), 3)
        self.assertTrue(existing.issubset(set(product.variants.values_list('pk', flat=True))))


class VariantApiTests(TestCase):

    def setUp(self):
        self.product = create_product(sizes=('M',), colors=('qora',))
        self.variant = self.product.variants.get()

    def test_lookup_by_barcode(self):
        client = api_client(create_cashier())

        response = client.get(f'/api/variants/by-barcode/?code= {self.variant.barcode} '.replace(' ', '%20'))

        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(response.json()['sku'], self.variant.sku)

    def test_unknown_barcode_returns_404(self):
        client = api_client(create_cashier())

        response = client.get('/api/variants/by-barcode/?code=2000000000000')

        self.assertEqual(response.status_code, 404)

    def test_cashier_cannot_change_price(self):
        client = api_client(create_cashier())

        response = client.patch(
            f'/api/variants/{self.variant.pk}/', {'sale_price': '1000'}, format='json'
        )

        self.assertEqual(response.status_code, 403)
        self.variant.refresh_from_db()
        self.assertIsNone(self.variant.sale_price)

    def test_admin_can_change_price(self):
        client = api_client(create_admin())

        response = client.patch(
            f'/api/variants/{self.variant.pk}/', {'sale_price': '300000'}, format='json'
        )

        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(Variant.objects.get(pk=self.variant.pk).sale_price, 300000)


class MediaTestCase(TestCase):
    """Rasm testlari uchun asos: MEDIA_ROOT vaqtinchalik papkaga olinadi."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.media = tempfile.mkdtemp()
        cls.override = override_settings(MEDIA_ROOT=cls.media)
        cls.override.enable()

    @classmethod
    def tearDownClass(cls):
        cls.override.disable()
        shutil.rmtree(cls.media, ignore_errors=True)
        super().tearDownClass()

    def upload(self, client, product, image=None, color=None):
        data = {'product': product.pk, 'image': image or image_upload()}

        if color is not None:
            data['color'] = color.pk

        return client.post('/api/product-images/', data, format='multipart')


class ProductImageTests(MediaTestCase):

    def setUp(self):
        self.product = create_product(sizes=('M',), colors=('Qora', 'Oq'))
        self.client_admin = api_client(create_admin())

    def test_upload_creates_three_sizes(self):
        response = self.upload(
            self.client_admin, self.product, image_upload(size=(2000, 1500))
        )

        self.assertEqual(response.status_code, 201, response.content)

        image = ProductImage.objects.get()

        for field, longest in (('thumb', 200), ('medium', 800), ('large', 1600)):
            with Image.open(getattr(image, field).path) as rendered:
                self.assertEqual(rendered.format, 'WEBP', field)
                self.assertEqual(max(rendered.size), longest, field)

    def test_small_image_is_not_enlarged(self):
        self.upload(self.client_admin, self.product, image_upload(size=(300, 300)))

        image = ProductImage.objects.get()

        with Image.open(image.large.path) as rendered:
            self.assertEqual(rendered.size, (300, 300))

    def test_exif_rotation_is_applied(self):
        """Telefonda yotgan holatda olingan rasm to'g'ri buriladi."""
        response = self.upload(
            self.client_admin, self.product, image_upload(size=(1200, 900), orientation=6)
        )

        self.assertEqual(response.status_code, 201, response.content)

        with Image.open(ProductImage.objects.get().thumb.path) as rendered:
            width, height = rendered.size

            self.assertGreater(height, width, 'rasm burilmagan')
            # EXIF saqlanmaydi: u bilan birga suratga olingan joy ham ketardi
            self.assertFalse(rendered.getexif())

    def test_oversized_file_is_rejected(self):
        big = SimpleUploadedFile(
            'katta.jpg', b'\0' * (MAX_UPLOAD_BYTES + 1), content_type='image/jpeg'
        )

        response = self.upload(self.client_admin, self.product, big)

        self.assertEqual(response.status_code, 400)
        self.assertIn('15 MB', str(response.json()))
        self.assertEqual(ProductImage.objects.count(), 0)

    def test_non_image_is_rejected(self):
        text = SimpleUploadedFile('hujjat.txt', b'salom', content_type='text/plain')

        response = self.upload(self.client_admin, self.product, text)

        self.assertEqual(response.status_code, 400)
        self.assertIn('rasm emas', str(response.json()))

    def test_image_belongs_to_a_color_or_to_the_product(self):
        black = Color.objects.get(name='Qora')

        self.upload(self.client_admin, self.product, color=black)
        self.upload(self.client_admin, self.product)

        by_color = ProductImage.objects.filter(color=black).count()
        general = ProductImage.objects.filter(color__isnull=True).count()

        self.assertEqual((by_color, general), (1, 1))

    def test_first_image_becomes_primary(self):
        self.upload(self.client_admin, self.product)
        self.upload(self.client_admin, self.product)

        primary = ProductImage.objects.filter(is_primary=True)

        self.assertEqual(primary.count(), 1)
        self.assertEqual(primary.get(), ProductImage.objects.order_by('id').first())

    def test_primary_can_be_switched(self):
        self.upload(self.client_admin, self.product)
        self.upload(self.client_admin, self.product)

        second = ProductImage.objects.order_by('id').last()

        response = self.client_admin.patch(
            f'/api/product-images/{second.pk}/', {'is_primary': True}, format='json'
        )

        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(ProductImage.objects.filter(is_primary=True).count(), 1)
        self.assertTrue(ProductImage.objects.get(pk=second.pk).is_primary)

    def test_eleventh_image_is_rejected(self):
        for _ in range(ProductImage.MAX_PER_PRODUCT):
            self.assertEqual(self.upload(self.client_admin, self.product).status_code, 201)

        response = self.upload(self.client_admin, self.product)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(ProductImage.objects.count(), ProductImage.MAX_PER_PRODUCT)

    def test_deleting_primary_promotes_next_and_removes_files(self):
        self.upload(self.client_admin, self.product)
        self.upload(self.client_admin, self.product)

        first, second = ProductImage.objects.order_by('id')
        paths = [first.thumb.path, first.medium.path, first.large.path]

        # Fayllar tranzaksiya yakunlangandan keyin o'chiriladi
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client_admin.delete(f'/api/product-images/{first.pk}/')

        self.assertEqual(response.status_code, 204, response.content)
        self.assertTrue(ProductImage.objects.get(pk=second.pk).is_primary)

        for path in paths:
            self.assertFalse(os.path.exists(path), path)

    def test_cashier_cannot_upload(self):
        response = self.upload(api_client(create_cashier()), self.product)

        self.assertEqual(response.status_code, 403)


class CatalogApiTests(MediaTestCase):

    def setUp(self):
        self.product = create_product(sizes=('S', 'M'), colors=('Qora', 'Oq'))
        self.client_admin = api_client(create_admin())
        self.client_cashier = api_client(create_cashier())

        self.variant = self.product.variants.first()
        receive_stock(self.variant, 5, '100000')

    def test_list_card_has_image_price_and_stock(self):
        self.upload(self.client_admin, self.product)

        response = self.client_cashier.get('/api/catalog/')

        self.assertEqual(response.status_code, 200, response.content)

        card = response.json()['results'][0]

        self.assertEqual(card['name'], self.product.name)
        self.assertEqual(card['total_stock'], 5)
        self.assertEqual(card['sale_price'], '250000.00')
        self.assertIsNotNone(card['primary_image']['thumb'])

    def test_product_without_images_has_no_primary(self):
        response = self.client_cashier.get('/api/catalog/')

        self.assertIsNone(response.json()['results'][0]['primary_image'])

    def test_detail_groups_images_by_color(self):
        black = Color.objects.get(name='Qora')

        self.upload(self.client_admin, self.product, color=black)
        self.upload(self.client_admin, self.product, color=black)
        self.upload(self.client_admin, self.product)

        response = self.client_cashier.get(f'/api/catalog/{self.product.pk}/')

        self.assertEqual(response.status_code, 200, response.content)

        groups = {group['color']: group for group in response.json()['image_groups']}

        self.assertEqual(len(groups[None]['images']), 1)
        self.assertEqual(len(groups[black.pk]['images']), 2)
        self.assertEqual(groups[black.pk]['hex_code'], black.hex_code)

    def test_detail_lists_colors_and_sizes_in_order(self):
        body = self.client_cashier.get(f'/api/catalog/{self.product.pk}/').json()

        self.assertEqual([size['name'] for size in body['sizes']], ['S', 'M'])
        self.assertEqual([color['name'] for color in body['colors']], ['Oq', 'Qora'])
        self.assertTrue(all(color['hex_code'] for color in body['colors']))

    def test_detail_has_stock_per_variant(self):
        body = self.client_cashier.get(f'/api/catalog/{self.product.pk}/').json()

        stock = {variant['id']: variant['stock_quantity'] for variant in body['variants']}

        self.assertEqual(stock[self.variant.pk], 5)
        self.assertEqual(len(stock), 4)

    def test_cashier_does_not_see_cost(self):
        body = self.client_cashier.get(f'/api/catalog/{self.product.pk}/').json()

        for variant in body['variants']:
            self.assertNotIn('average_cost', variant)

    def test_admin_sees_cost(self):
        body = self.client_admin.get(f'/api/catalog/{self.product.pk}/').json()

        self.assertIn('average_cost', body['variants'][0])

    def test_search_by_barcode(self):
        response = self.client_cashier.get(f'/api/catalog/?search={self.variant.barcode}')

        self.assertEqual(response.json()['count'], 1)

    def test_in_stock_filter_hides_empty_products(self):
        create_product(name='Qoldiqsiz')

        with_stock = self.client_cashier.get('/api/catalog/?in_stock=true').json()

        self.assertEqual([item['name'] for item in with_stock['results']], [self.product.name])


class CatalogListTests(TestCase):
    """Katalog ro'yxati: o'lcham bo'yicha qoldiq, tartib va filtrlar."""

    def setUp(self):
        self.client_cashier = api_client(create_cashier())

    def cards(self, query=''):
        response = self.client_cashier.get(f'/api/catalog/{query}')

        self.assertEqual(response.status_code, 200, response.content)

        return response.json()['results']

    def names(self, query=''):
        return [card['name'] for card in self.cards(query)]

    def test_size_stock_sums_colors_in_size_order(self):
        product = create_product(sizes=('S', 'M', 'L'), colors=('Qora', 'Oq'))

        for (size, color), quantity in {
            ('S', 'Qora'): 2,
            ('S', 'Oq'): 1,
            ('L', 'Qora'): 5,
        }.items():
            variant = product.variants.get(size__name=size, color__name=color)
            receive_stock(variant, quantity, '100000')

        card = self.cards()[0]

        # Qoldig'i yo'q o'lcham ham ro'yxatda: "M tugagan" ham javob
        self.assertEqual(
            [(entry['size_name'], entry['quantity']) for entry in card['size_stock']],
            [('S', 3), ('M', 0), ('L', 5)],
        )
        self.assertEqual(card['total_stock'], 8)

    def test_product_without_sizes_has_empty_size_stock(self):
        create_product(name='Sharf')

        self.assertEqual(self.cards()[0]['size_stock'], [])

    def test_color_count_for_the_receiving_strip(self):
        """Kirim ekranidagi karta «S–L · 2 rang» deb yozadi."""
        create_product(sizes=('S', 'M', 'L'), colors=('Qora', 'Oq'))

        self.assertEqual(self.cards()[0]['color_count'], 2)

    def test_color_count_is_zero_without_colors(self):
        create_product(name='Sharf')

        self.assertEqual(self.cards()[0]['color_count'], 0)

    def test_search_by_name_does_not_multiply_stock(self):
        """Ilgari qidiruv variantlarga ikkinchi JOIN qo'shib, yig'indini ko'paytirardi."""
        product = create_product(name='Yozgi ko‘ylak', sizes=('S', 'M'), colors=('Qora', 'Oq'))
        receive_stock(product.variants.first(), 3, '100000')

        card = self.cards('?search=yozgi')[0]

        self.assertEqual(card['total_stock'], 3)
        self.assertEqual(sum(entry['quantity'] for entry in card['size_stock']), 3)

    def test_newest_first_by_default(self):
        for name in ('Birinchi', 'Ikkinchi', 'Uchinchi'):
            create_product(name=name)

        self.assertEqual(self.names(), ['Uchinchi', 'Ikkinchi', 'Birinchi'])

    def test_order_by_name(self):
        for name in ('Uchinchi', 'Birinchi', 'Ikkinchi'):
            create_product(name=name)

        self.assertEqual(self.names('?ordering=name'), ['Birinchi', 'Ikkinchi', 'Uchinchi'])

    def test_order_by_stock_both_directions(self):
        few = create_product(name='Oz')
        many = create_product(name='Kop')
        create_product(name='Yoq')

        receive_stock(few.variants.get(), 1, '100000')
        receive_stock(many.variants.get(), 9, '100000')

        self.assertEqual(self.names('?ordering=stock'), ['Yoq', 'Oz', 'Kop'])
        self.assertEqual(self.names('?ordering=-stock'), ['Kop', 'Oz', 'Yoq'])

    def test_unknown_ordering_falls_back_to_newest(self):
        for name in ('Birinchi', 'Ikkinchi'):
            create_product(name=name)

        self.assertEqual(self.names('?ordering=price'), ['Ikkinchi', 'Birinchi'])

    def test_low_stock_shows_only_running_out(self):
        for name, quantity, minimum in (
            ('Tugayapti', 2, 3),
            ('Yetarli', 10, 3),
            # Minimal qoldiq belgilanmagan — kuzatilmaydi, qoldig'i nol bo'lsa ham
            ('Kuzatilmaydi', 0, 0),
        ):
            variant = create_product(name=name).variants.get()

            if quantity:
                receive_stock(variant, quantity, '100000')

            variant.min_stock = minimum
            variant.save(update_fields=['min_stock'])

        self.assertEqual(self.names('?low_stock=true'), ['Tugayapti'])

    def test_low_stock_looks_at_the_shop_not_the_warehouse(self):
        """Omborda to'la bo'lsa ham, javon bo'sh bo'lsa — ogohlantirish."""
        variant = create_product(name='Zalda tugadi').variants.get()

        receive_stock(variant, 20, '100000', location=Location.warehouse())

        variant.min_stock = 3
        variant.save(update_fields=['min_stock'])

        self.assertEqual(self.names('?low_stock=true'), ['Zalda tugadi'])

        # Zalga chiqarilgandan keyin ogohlantirish yo'qoladi
        create_transfer(
            source=Location.warehouse(),
            target=Location.shop(),
            lines=[{'variant': variant, 'quantity': 10}],
        )

        self.assertEqual(self.names('?low_stock=true'), [])


class SlugTests(TestCase):

    def test_slug_is_generated_from_name(self):
        product = create_product(name='Yozgi ko‘ylak')

        self.assertEqual(product.slug, 'yozgi-koylak')

    def test_same_name_gets_a_different_slug(self):
        first = create_product(name='Ko‘ylak')
        second = create_product(name='Ko‘ylak')

        self.assertNotEqual(first.slug, second.slug)
        self.assertEqual(Product.objects.filter(slug=first.slug).count(), 1)

    def test_name_without_latin_letters_still_gets_a_slug(self):
        product = create_product(name='Кўйлак')

        self.assertTrue(product.slug)

    def test_admin_can_set_slug(self):
        product = create_product()

        response = api_client(create_admin()).patch(
            f'/api/products/{product.pk}/', {'slug': 'maxsus-manzil'}, format='json'
        )

        self.assertEqual(response.status_code, 200, response.content)
        self.assertEqual(Product.objects.get(pk=product.pk).slug, 'maxsus-manzil')

    def test_unique_slug_helper_skips_taken_values(self):
        create_product(name='Sharf')

        self.assertEqual(unique_slug('Sharf'), 'sharf-2')


class CatalogSearchTests(TestCase):
    """Birlashtirilgan mahsulotlar sahifasi: qoldiq sahifasidagi qidiruvlar ham ishlaydi."""

    def setUp(self):
        self.product = create_product(name='Yozgi ko‘ylak', sizes=('M',))
        self.product.brand = 'Zara'
        self.product.save(update_fields=['brand'])
        create_product(name='Sharf')

    def names(self, query, user=None):
        client = api_client(user or create_cashier())
        response = client.get(f'/api/catalog/?search={query}')

        self.assertEqual(response.status_code, 200, response.content)

        return [item['name'] for item in response.json()['results']]

    def test_search_by_sku(self):
        sku = self.product.variants.get().sku

        self.assertEqual(self.names(sku), [self.product.name])

    def test_search_by_brand(self):
        self.assertEqual(self.names('zara'), [self.product.name])

class AddVariantTests(TestCase):
    """Kirimda kelgan yangi o'lcham × rang juftligi.

    Do'konda ko'k M va L bo'lgan kurtka qizil XL bo'lib kelsa, faqat
    qizil XL qo'shilishi kerak. Matritsa (mahsulot formasi) bu yerda
    yaramaydi: u qizil M, qizil L va ko'k XL ni ham yaratib yuboradi —
    do'konda bunday tovar yo'q, lekin ular qoldiqda va yorliqlarda
    paydo bo'lardi.
    """

    def setUp(self):
        self.admin = create_admin()
        self.client_admin = api_client(self.admin)

        self.product = create_product(sizes=('M', 'L'), colors=('Ko‘k',))
        self.blue = Color.objects.get(name='Ko‘k')
        self.large = Size.objects.get(name='L')

        self.xl = Size.objects.create(name='XL', position=9)
        self.red = Color.objects.create(name='Qizil', hex_code='#c02626')

    def pairs(self):
        return {
            (variant.size_id, variant.color_id) for variant in self.product.variants.all()
        }

    def test_creates_only_the_asked_pair(self):
        before = self.pairs()

        variant = add_variant(self.product, size=self.xl, color=self.red)

        self.assertEqual(self.pairs() - before, {(self.xl.pk, self.red.pk)})
        self.assertEqual(self.product.variants.count(), 3)

        # Qizil M, qizil L va ko'k XL yaratilmadi
        self.assertFalse(
            self.product.variants.filter(size=self.large, color=self.red).exists()
        )
        self.assertFalse(
            self.product.variants.filter(size=self.xl, color=self.blue).exists()
        )

        self.assertTrue(is_valid_ean13(variant.barcode), variant.barcode)
        self.assertEqual(Variant.objects.filter(barcode=variant.barcode).count(), 1)
        self.assertTrue(variant.sku)

    def test_is_idempotent(self):
        first = add_variant(self.product, size=self.xl, color=self.red)
        second = add_variant(self.product, size=self.xl, color=self.red)

        self.assertEqual(first.pk, second.pk)
        self.assertEqual(self.product.variants.count(), 3)

    def test_api_creates_once(self):
        response = self.client_admin.post(
            f'/api/products/{self.product.pk}/variants/',
            {'size': self.xl.pk, 'color': self.red.pk},
            format='json',
        )

        self.assertEqual(response.status_code, 201, response.content)

        body = response.json()

        self.assertEqual(body['size_name'], 'XL')
        self.assertEqual(body['color_name'], 'Qizil')
        self.assertEqual(body['stock_quantity'], 0)
        self.assertTrue(is_valid_ean13(body['barcode']), body['barcode'])

        # Ikkinchi marta bosilsa — o'sha variant, yangisi emas
        again = self.client_admin.post(
            f'/api/products/{self.product.pk}/variants/',
            {'size': self.xl.pk, 'color': self.red.pk},
            format='json',
        )

        self.assertEqual(again.status_code, 200, again.content)
        self.assertEqual(again.json()['id'], body['id'])
        self.assertEqual(self.product.variants.count(), 3)

    def test_api_needs_size_or_color(self):
        response = self.client_admin.post(
            f'/api/products/{self.product.pk}/variants/', {}, format='json'
        )

        self.assertEqual(response.status_code, 400, response.content)

    def test_api_rejects_unknown_size(self):
        response = self.client_admin.post(
            f'/api/products/{self.product.pk}/variants/',
            {'size': 9999, 'color': self.red.pk},
            format='json',
        )

        self.assertEqual(response.status_code, 404, response.content)

    def test_cashier_cannot_add_variants(self):
        response = api_client(create_cashier()).post(
            f'/api/products/{self.product.pk}/variants/',
            {'size': self.xl.pk, 'color': self.red.pk},
            format='json',
        )

        self.assertEqual(response.status_code, 403, response.content)
        self.assertEqual(self.product.variants.count(), 2)
