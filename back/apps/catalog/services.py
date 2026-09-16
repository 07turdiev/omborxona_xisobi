"""Katalog xizmatlari: shtrix-kod va variant matritsasi."""

from django.db import connection, transaction

from apps.catalog.models import Color, Size, Variant

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
