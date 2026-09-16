"""Katalog testlari: variant matritsasi va shtrix-kod."""

from django.test import TestCase

from apps.catalog.models import Variant
from apps.catalog.services import ean13_check_digit, next_internal_barcode
from apps.core.factories import api_client, create_admin, create_cashier, create_product


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
