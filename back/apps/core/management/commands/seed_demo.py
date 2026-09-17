"""Namuna ma'lumotlari — faqat ishlab chiqish kompyuteri uchun.

Buyruq `DEBUG=False` bo'lganda ishlamaydi: namuna xodimlarning paroli
hammaga ma'lum, ular ishlab chiqarish bazasiga tushmasligi kerak.
"""

from decimal import Decimal

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from apps.accounts.models import User
from apps.catalog.models import Category, Color, Product, Size, Variant
from apps.catalog.services import sync_variant_matrix
from apps.core.models import ShopSettings
from apps.core.numbering import next_number
from apps.purchases import services as purchase_services
from apps.purchases.models import Purchase, PurchaseLine, Supplier
from apps.sales import services as sale_services

#: Namuna xodimlar uchun parol — faqat lokal sinov uchun
PASSWORD = 'demo12345'

PRODUCTS = [
    ('Ko‘ylak', 'Yozgi ko‘ylak', 'Zara', '250000', ['S', 'M', 'L'], ['Oq', 'Qora']),
    ('Ko‘ylak', 'Shifon ko‘ylak', 'Mango', '320000', ['M', 'L'], ['Qizil', 'Ko‘k']),
    ('Shim', 'Klassik shim', 'LC Waikiki', '180000', ['S', 'M', 'L', 'XL'], ['Qora']),
    ('Kurtka', 'Bahorgi kurtka', 'Koton', '450000', ['M', 'L'], ['Oq', 'Qora', 'Qizil']),
]

#: DIQQAT: bu MXIK kodlari — O'YLAB TOPILGAN NAMUNA, soliq tizimida
#: mavjud emas. Haqiqiy kodlar tasnif.soliq.uz ma'lumotnomasidan olinadi
#: va Sozlamalar → Kategoriyalar bo'limida yoziladi. Namuna kodlar
#: 99999 bilan boshlanadi — shunda ular tasodifan haqiqiy deb
#: o'ylanmaydi.
CATEGORY_CODES = {
    'Ko‘ylak': '99999000000000001',
    'Shim': '99999000000000002',
    'Kurtka': '99999000000000003',
}


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
            name: Category.objects.create(name=name, mxik_code=CATEGORY_CODES.get(name, ''))
            for name in dict.fromkeys(row[0] for row in PRODUCTS)
        }
        sizes = {
            name: Size.objects.create(name=name, position=index)
            for index, name in enumerate(['S', 'M', 'L', 'XL'], 1)
        }
        colors = {
            name: Color.objects.create(name=name)
            for name in ['Oq', 'Qora', 'Qizil', 'Ko‘k']
        }

        for category, name, brand, price, product_sizes, product_colors in PRODUCTS:
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

        supplier = Supplier.objects.create(
            name='Toshkent Tekstil', phone='+998 90 000 00 00'
        )

        # Kirim: har variantdan 8 dona, tannarx sotuv narxining 60 %
        today = timezone.localdate()

        purchase = Purchase.objects.create(
            number=next_number('KIR', Purchase.objects, today),
            date=today,
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

    def _report(self):
        sample = Variant.objects.order_by('id').first()

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('Namuna ma’lumotlari tayyor.'))
        self.stdout.write('')
        self.stdout.write(f'  Xodimlar     : admin / kassir, parol: {PASSWORD}')
        self.stdout.write(
            f'  Mahsulot     : {Product.objects.count()} ta, '
            f'variant: {Variant.objects.count()} ta'
        )
        self.stdout.write(
            f'  Qoldiq       : '
            f'{sum(Variant.objects.values_list("stock_quantity", flat=True))} dona'
        )

        if sample:
            self.stdout.write(f'  Sinov uchun shtrix-kod: {sample.barcode}')

        self.stdout.write('')
