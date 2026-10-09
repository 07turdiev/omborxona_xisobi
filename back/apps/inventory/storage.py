"""Ombordagi shkaf: ustun va qatorlarga bo'lingan kataklar.

Omborda bitta shkaf bor va u Excel jadvaliga o'xshaydi: ustunlar harf
(A, B, C...), qatorlar raqam (1, 2, 3...). Katak nomi shu ikkisidan
yig'iladi — `B2`.

Katak **faqat joyni ko'rsatadi**: qoldiq avvalgidek butun ombor
bo'yicha yuritiladi. Ombor kichik va unda tovar ko'p saqlanmaydi,
shuning uchun har katakda alohida hisob yuritish xodimning ishini
og'irlashtirardi — zalga chiqarishda, hisobdan chiqarishda va sanoqda
har safar katak tanlash kerak bo'lardi. Bu yerda esa katak bitta
savolga javob beradi: «tovarni qayerdan olaman?»

Shkaf o'lchami do'kon sozlamalarida (`ShopSettings`).
"""

from django.core.exceptions import ValidationError

#: Ustun harflari. Bitta shkaf uchun 12 tadan ortig'i kerak emas.
LETTERS = 'ABCDEFGHIJKL'

MAX_COLUMNS = len(LETTERS)
MAX_ROWS = 20


def column_letter(index: int) -> str:
    """0 -> 'A', 1 -> 'B'."""
    return LETTERS[index]


def cell_names(columns: int, rows: int) -> list[str]:
    """Shkafdagi hamma katak nomi, chapdan o'ngga va yuqoridan pastga."""
    return [f'{LETTERS[column]}{row + 1}' for row in range(rows) for column in range(columns)]


def parse_cell(cell: str) -> tuple[int, int] | None:
    """`'B2'` -> `(1, 1)`. Shakli noto'g'ri bo'lsa `None`.

    Qaytadigan juftlik — noldan boshlanadigan (ustun, qator) indeksi.
    """
    cell = (cell or '').strip().upper()

    if len(cell) < 2:
        return None

    letter, digits = cell[0], cell[1:]

    if letter not in LETTERS or not digits.isdigit():
        return None

    row = int(digits)

    if row < 1:
        return None

    return LETTERS.index(letter), row - 1


def normalize_cell(cell: str, columns: int, rows: int) -> str:
    """Katak nomini tekshiradi va bir xil ko'rinishga keltiradi.

    Bo'sh qiymat ruxsat etiladi — tovarning joyi belgilanmagan degani.
    Shkafdan tashqaridagi katak rad etiladi: `F1` deb yozilgan tovarni
    besh ustunli shkafdan hech kim topa olmaydi.
    """
    cell = (cell or '').strip().upper()

    if not cell:
        return ''

    parsed = parse_cell(cell)

    if parsed is None:
        raise ValidationError(f'«{cell}» katak nomi noto‘g‘ri. Masalan: A1, B2')

    column, row = parsed

    if column >= columns or row >= rows:
        last = f'{LETTERS[columns - 1]}{rows}'

        raise ValidationError(f'«{cell}» shkafda yo‘q. Oxirgi katak: {last}')

    return f'{LETTERS[column]}{row + 1}'


def warehouse() -> 'Location':  # noqa: F821
    """Ombor joyi. Bitta do'konda u bitta."""
    from apps.inventory.models import Location

    return Location.objects.filter(kind=Location.Kind.WAREHOUSE, is_active=True).first()


def place(variant, cell: str) -> str:
    """Tovarga shkafdagi joy belgilaydi.

    Bo'sh qiymat joyni o'chiradi. Qoldiq qatori yo'q bo'lsa yaratiladi:
    tovar hali kelmagan bo'lsa ham, uning joyini oldindan belgilab
    qo'yish mumkin.
    """
    from apps.core.models import ShopSettings
    from apps.inventory.models import VariantStock

    settings = ShopSettings.load()
    cell = normalize_cell(cell, settings.cabinet_columns, settings.cabinet_rows)

    store = warehouse()

    if store is None:
        raise ValidationError('Ombor topilmadi')

    stock, _created = VariantStock.objects.get_or_create(variant=variant, location=store)

    if stock.cell != cell:
        stock.cell = cell
        stock.save(update_fields=['cell'])

    return cell


def cabinet() -> dict:
    """Shkaf xaritasi: har katakda nima turibdi.

    Bo'sh kataklar ham qaytadi — jadval to'liq chizilishi kerak.
    Joyi belgilanmagan, lekin omborda turgan tovarlar alohida
    ro'yxatda: ularni xodim ko'rib, joyini belgilab chiqadi.
    """
    from apps.core.models import ShopSettings
    from apps.inventory.models import VariantStock

    settings = ShopSettings.load()
    store = warehouse()

    cells = {name: [] for name in cell_names(settings.cabinet_columns, settings.cabinet_rows)}
    loose = []

    if store is None:
        return {
            'columns': settings.cabinet_columns,
            'rows': settings.cabinet_rows,
            'cells': cells,
            'unplaced': loose,
            'outside': {},
        }

    rows = (
        VariantStock.objects.filter(location=store, quantity__gt=0)
        .select_related('variant__product', 'variant__size', 'variant__color')
        .order_by('variant__product__name', 'variant__size__name', 'variant__color__name')
    )

    # Shkaf kichraytirilgan bo'lsa, eski kataklar ro'yxatdan tashqarida
    # qoladi. Ularni jimgina yo'qotib bo'lmaydi: tovar o'sha yerda
    # turibdi va xodim uni ko'chirishi kerak.
    outside = {}

    for stock in rows:
        item = {
            'variant': stock.variant_id,
            'name': stock.variant.product.name,
            'label': stock.variant.label,
            'quantity': stock.quantity,
        }

        if not stock.cell:
            loose.append(item)
        elif stock.cell in cells:
            cells[stock.cell].append(item)
        else:
            outside.setdefault(stock.cell, []).append(item)

    return {
        'columns': settings.cabinet_columns,
        'rows': settings.cabinet_rows,
        'cells': cells,
        'unplaced': loose,
        'outside': outside,
    }
