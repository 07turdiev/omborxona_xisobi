"""Namuna ma'lumotlari — faqat ishlab chiqish kompyuteri uchun.

Buyruq `DEBUG=False` bo'lganda ishlamaydi: namuna xodimlarning paroli
hammaga ma'lum, ular ishlab chiqarish bazasiga tushmasligi kerak.
"""

from decimal import Decimal
from pathlib import Path

from django.conf import settings
from django.core.files import File
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from apps.accounts.models import User
from apps.catalog.models import Category, Color, Product, Size, Variant
from apps.catalog.services import add_product_image, sync_variant_matrix
from apps.core.models import ShopSettings
from apps.core.numbering import next_number
from apps.inventory import services as inventory_services
from apps.inventory.models import Location
from apps.purchases import services as purchase_services
from apps.purchases.models import Purchase, PurchaseLine, Supplier
from apps.sales import services as sale_services

#: Namuna xodimlar uchun parol — faqat lokal sinov uchun
PASSWORD = 'demo12345'

#: Rasmlar shu papkada: har tovarga bittadan (manba: `demo_photos/SOURCES.md`)
PHOTO_DIR = Path(__file__).resolve().parents[2] / 'demo_photos'

#: kategoriya, nom, brend, narx, o'lchamlar, ranglar, rasm
PRODUCTS = [
    ('Ko‘ylak', 'Gulli yozgi ko‘ylak', 'Zara', '390000',
     ['S', 'M', 'L'], ['Oq', 'Bej'], 'dress-floral'),
    ('Ko‘ylak', 'Oq kechki ko‘ylak', 'Mango', '620000',
     ['S', 'M', 'L'], ['Oq'], 'dress-white'),
    ('Bluzka', 'Yo‘l-yo‘l zig‘ir bluzka', 'Koton', '210000',
     ['S', 'M', 'L'], ['Oq', 'Bej'], 'blouse-striped'),
    ('Bluzka', 'Kashtali oq bluzka', 'LC Waikiki', '185000',
     ['S', 'M', 'L'], ['Oq'], 'blouse-floral'),
    ('Bluzka', 'Shifon gulli bluzka', 'Zara', '240000',
     ['S', 'M', 'L'], ['Bej', 'Ko‘k'], 'blouse-lace'),
    ('Bluzka', 'Yengsiz qora bluzka', 'Mango', '160000',
     ['S', 'M', 'L'], ['Qora'], 'top-black'),
    ('Shim', 'Yo‘l-yo‘l keng shim', 'Zara', '290000',
     ['S', 'M', 'L', 'XL'], ['Oq'], 'trousers-striped'),
    ('Shim', 'Zig‘ir shim', 'Koton', '250000',
     ['S', 'M', 'L', 'XL'], ['Sariq', 'Bej'], 'trousers-linen'),
    ('Shim', 'Naqshli keng shim', 'LC Waikiki', '270000',
     ['M', 'L', 'XL'], ['Qora'], 'trousers-wide'),
    ('Yubka', 'Fatin yubka', 'Mango', '340000',
     ['S', 'M', 'L'], ['Jigarrang'], 'skirt-brown'),
    ('Pidjak', 'Katak pidjak', 'Zara', '520000',
     ['S', 'M', 'L'], ['Kulrang'], 'blazer-gray'),
    ('Kofta', 'Trikotaj kofta', 'Koton', '330000',
     ['S', 'M', 'L'], ['Yashil'], 'knit-gray'),
]

COLORS = [
    ('Oq', '#FFFFFF'),
    ('Qora', '#1A1A1A'),
    ('Bej', '#D9C7AE'),
    ('Jigarrang', '#8A6636'),
    ('Kulrang', '#9E9E9E'),
    ('Ko‘k', '#1976D2'),
    ('Yashil', '#4E8A72'),
    ('Sariq', '#E0B23C'),
]


class Command(BaseCommand):
    help = 'Namuna ma’lumotlarini yaratadi (faqat DEBUG=True bo‘lganda)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Bazadagi hamma narsani o‘chirib, qaytadan yaratadi',
        )

    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError(
                'seed_demo faqat DEBUG=True bo‘lganda ishlaydi.\n'
                'Ishlab chiqarish bazasida namuna xodim yaratilmaydi: '
                'ularning paroli hujjatlarda ochiq yozilgan.'
            )

        self.stdout.write(
            self.style.WARNING(
                'DIQQAT: bu buyruq faqat lokal sinov uchun. Yaratiladigan '
                'xodimlar (admin, kassir) va ularning paroli hammaga ma’lum — '
                'serverda hech qachon ishlatmang.'
            )
        )

        if Product.objects.exists() and not options['force']:
            raise CommandError(
                'Bazada allaqachon ma’lumot bor. Hammasini o‘chirib qayta '
                'yaratish uchun: manage.py seed_demo --force'
            )

        if options['force']:
            self.stdout.write('Baza tozalanmoqda...')
            call_command('flush', interactive=False, verbosity=0)

        # `flush` joylarni ham o'chiradi (ular migratsiyada yaratilgan)
        Location.objects.get_or_create(
            kind=Location.Kind.WAREHOUSE, defaults={'name': 'Ombor'}
        )
        Location.objects.get_or_create(kind=Location.Kind.SHOP, defaults={'name': 'Savdo zali'})

        self._create()

    def _create(self):
        shop = ShopSettings.load()
        shop.shop_name = 'Madlen sen'
        shop.max_discount_percent = Decimal('15')
        shop.save()

        admin = User.objects.create_user(
            username='admin',
            password=PASSWORD,
            role=User.Role.ADMIN,
            first_name='Gulnora',
            last_name='Karimova',
            is_staff=True,
            is_superuser=True,
        )
        cashier = User.objects.create_user(
            username='kassir',
            password=PASSWORD,
            role=User.Role.CASHIER,
            first_name='Dilnoza',
            last_name='Rahimova',
        )

        categories = {
            name: Category.objects.create(name=name)
            for name in dict.fromkeys(row[0] for row in PRODUCTS)
        }
        sizes = {
            name: Size.objects.create(name=name, position=index)
            for index, name in enumerate(['S', 'M', 'L', 'XL'], 1)
        }
        colors = {
            name: Color.objects.create(name=name, hex_code=hex_code)
            for name, hex_code in COLORS
        }

        for category, name, brand, price, product_sizes, product_colors, photo in PRODUCTS:
            product = Product.objects.create(
                category=categories[category],
                name=name,
                brand=brand,
                sale_price=Decimal(price),
            )
            sync_variant_matrix(
                product,
                [sizes[item].id for item in product_sizes],
                [colors[item].id for item in product_colors],
            )
            self._add_photo(product, photo)

        supplier = Supplier.objects.create(
            name='Toshkent Tekstil', phone='+998 90 000 00 00'
        )

        # Kirim: har variantdan 8 dona, tannarx sotuv narxining 60 %
        today = timezone.localdate()

        purchase = Purchase.objects.create(
            number=next_number('KIR', Purchase.objects, today),
            date=today,
            location=Location.warehouse(),
            supplier=supplier,
            note='Namuna partiya',
        )

        for product in Product.objects.all():
            cost = (product.sale_price * Decimal('0.6')).quantize(Decimal('0.01'))

            for variant in product.variants.all():
                PurchaseLine.objects.create(
                    purchase=purchase, variant=variant, quantity=8, unit_cost=cost
                )

        purchase_services.recalculate_total(purchase)
        purchase_services.confirm(purchase, user=admin)

        # Kelgan tovarning bir qismi savdo zaliga chiqariladi: qolgani
        # omborda turadi, xuddi haqiqiy do'kondagidek
        inventory_services.create_transfer(
            source=Location.warehouse(),
            target=Location.shop(),
            lines=[
                {'variant': variant, 'quantity': 3}
                for variant in Variant.objects.order_by('id')
            ],
            user=admin,
            note='Javonga chiqarildi',
        )

        # Ikkita sotuv: biri naqd (chegirma bilan), biri karta
        first, second = list(Variant.objects.order_by('id')[:2])

        sale_services.create_sale(
            user=cashier,
            lines=[
                {'variant': first, 'quantity': 2, 'discount_percent': Decimal('10')},
                {'variant': second, 'quantity': 1},
            ],
            cash_amount=(first.price * 2 * Decimal('0.9')).quantize(Decimal('0.01'))
            + second.price,
        )

        last = Variant.objects.order_by('-id').first()
        sale_services.create_sale(
            user=cashier,
            lines=[{'variant': last, 'quantity': 1}],
            card_amount=last.price,
        )

        self._report()

    def _add_photo(self, product, name: str) -> None:
        """Tovarga bitta rasm biriktiradi — rasmsiz tovar bo'lmaydi."""
        path = PHOTO_DIR / f'{name}.webp'

        if not path.exists():
            raise CommandError(f'Namuna rasmi topilmadi: {path}')

        with path.open('rb') as handle:
            add_product_image(product, File(handle, name=path.name))

    def _report(self):
        sample = Variant.objects.order_by('id').first()

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('Namuna ma’lumotlari tayyor.'))
        self.stdout.write('')
        self.stdout.write(f'  Xodimlar     : admin / kassir, parol: {PASSWORD}')
        self.stdout.write(
            f'  Mahsulot     : {Product.objects.count()} ta '
            f'(hammasi rasmli), variant: {Variant.objects.count()} ta'
        )
        self.stdout.write(
            f'  Qoldiq       : '
            f'{sum(Variant.objects.values_list("stock_quantity", flat=True))} dona'
        )

        if sample:
            self.stdout.write(f'  Sinov uchun shtrix-kod: {sample.barcode}')

        self.stdout.write('')
