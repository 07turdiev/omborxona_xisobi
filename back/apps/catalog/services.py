"""Katalog xizmatlari: shtrix-kod, variant matritsasi va rasmlar."""

from django.core.exceptions import ValidationError
from django.db import connection, transaction
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _

from apps.catalog.images import build_sizes
from apps.catalog.models import Color, Product, ProductImage, Size, Variant

#: Ichki (do'kon ichidagi) kodlar uchun EAN-13 prefiksi.
#: 200-299 oralig'i xalqaro standartda aynan shu maqsad uchun ajratilgan.
INTERNAL_PREFIX = '200'


def ean13_check_digit(twelve_digits: str) -> str:
    """EAN-13 nazorat raqami: toq o'rin ×1, juft o'rin ×3."""
    if len(twelve_digits) != 12 or not twelve_digits.isdigit():
        raise ValueError('EAN-13 uchun 12 ta raqam kerak')

    total = sum(
        int(digit) * (3 if index % 2 else 1)
        for index, digit in enumerate(twelve_digits)
    )

    return str((10 - total % 10) % 10)


def next_internal_barcode() -> str:
    """Yangi ichki shtrix-kod: `200` + 9 xonali tartib + nazorat raqami."""
    with connection.cursor() as cursor:
        cursor.execute("SELECT nextval('catalog_barcode_seq')")
        sequence_value = cursor.fetchone()[0]

    body = f'{INTERNAL_PREFIX}{sequence_value:09d}'

    return body + ean13_check_digit(body)


def next_sku(product) -> str:
    """Variant artikuli: `P0007-03`. Mahsulot ichida tartib bilan."""
    count = product.variants.count()

    while True:
        count += 1
        candidate = f'P{product.pk:04d}-{count:02d}'

        if not Variant.objects.filter(sku=candidate).exists():
            return candidate


def create_variant(product, size=None, color=None, **fields) -> Variant:
    """Variant yaratadi: artikul va shtrix-kod avtomatik beriladi."""
    fields.setdefault('sku', next_sku(product))
    fields.setdefault('barcode', next_internal_barcode())

    return Variant.objects.create(product=product, size=size, color=color, **fields)


@transaction.atomic
def sync_variant_matrix(product, size_ids=None, color_ids=None) -> list[Variant]:
    """Tanlangan o'lcham × rang kombinatsiyalaridan yetishmaganini yaratadi.

    Mavjud variantlar hech qachon o'chirilmaydi: ularda qoldiq va sotuv
    tarixi bo'lishi mumkin. Keraksizini foydalanuvchi faolsizlantiradi.

    O'lcham ham, rang ham tanlanmagan bo'lsa, mahsulotda bitta variant
    bo'ladi (foydalanuvchi uni umuman ko'rmaydi).
    """
    sizes = list(Size.objects.filter(pk__in=size_ids or [])) or [None]
    colors = list(Color.objects.filter(pk__in=color_ids or [])) or [None]

    existing = {
        (variant.size_id, variant.color_id)
        for variant in product.variants.all()
    }

    created = []

    for size in sizes:
        for color in colors:
            key = (size.pk if size else None, color.pk if color else None)

            if key in existing:
                continue

            created.append(create_variant(product, size=size, color=color))

    return created


def unique_slug(name: str, *, exclude_pk=None) -> str:
    """Nomdan takrorlanmaydigan manzil qismini yasaydi.

    `slugify` lotin bo'lmagan belgilarni tashlaydi, shuning uchun
    butunlay kirilcha nomdan bo'sh qator chiqishi mumkin — u holda
    umumiy asos olinadi va raqam qo'shiladi.
    """
    base = slugify(name)[:200] or 'mahsulot'
    candidate = base
    index = 2

    while Product.objects.filter(slug=candidate).exclude(pk=exclude_pk).exists():
        candidate = f'{base}-{index}'
        index += 1

    return candidate


@transaction.atomic
def add_product_image(product, upload, color=None) -> ProductImage:
    """Rasmni uchta o'lchamda saqlaydi va mahsulotga biriktiradi."""
    if product.images.count() >= ProductImage.MAX_PER_PRODUCT:
        raise ValidationError(
            _('Bitta mahsulotga eng ko‘pi %(count)d ta rasm qo‘shish mumkin.')
            % {'count': ProductImage.MAX_PER_PRODUCT}
        )

    files = build_sizes(upload)

    last = product.images.order_by('-sort_order').first()

    return ProductImage.objects.create(
        product=product,
        color=color,
        sort_order=(last.sort_order + 1) if last else 0,
        # Birinchi rasm o'zi asosiy bo'ladi: kartada nimadir ko'rinsin
        is_primary=not product.images.exists(),
        **files,
    )


@transaction.atomic
def set_primary_image(image: ProductImage) -> ProductImage:
    """Asosiy rasmni almashtiradi.

    Avval eskisi olib tashlanadi: bitta mahsulotda bitta asosiy rasm
    bo'lishini baza cheklovi ham talab qiladi.
    """
    ProductImage.objects.filter(product=image.product, is_primary=True).exclude(
        pk=image.pk
    ).update(is_primary=False)

    if not image.is_primary:
        image.is_primary = True
        image.save(update_fields=['is_primary'])

    return image


@transaction.atomic
def reorder_images(product, image_ids: list[int]) -> None:
    """Rasmlarni berilgan ketma-ketlikka keltiradi."""
    positions = {image_id: index for index, image_id in enumerate(image_ids)}

    for image in product.images.filter(pk__in=positions):
        image.sort_order = positions[image.pk]
        image.save(update_fields=['sort_order'])
