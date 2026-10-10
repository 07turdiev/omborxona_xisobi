"""Ombordagi javonlar va ularning manzillari.

Ombor — tor xona, javonlar devorlar bo'ylab ketadi. Har devorda
javonlar soni har xil: bir tomonda to'qqizta, boshqasida uchta, eshik
tepasida esa ikkita. Shuning uchun bu yerda to'g'ri to'rtburchak
jadval yo'q — har **javon qatori** (`ShelfRun`) o'z soni bilan yashaydi.

Manzil qator harfi va javon raqamidan yig'iladi:

    D3  ->  «o'ng devor, tepadan uchinchi javon»

Raqam tepadan boshlanadi: javon oldida turgan odam uni yuqoridan
pastga sanaydi.

Manzil **faqat joyni ko'rsatadi**: qoldiq avvalgidek butun ombor
bo'yicha yuritiladi. Ombor kichik va unda tovar ko'p saqlanmaydi, har
javonda alohida hisob yuritilsa esa zalga chiqarishda, hisobdan
chiqarishda va sanoqda har safar javon tanlash kerak bo'lardi. Manzil
bitta savolga javob beradi: «tovarni qayerdan olaman?»
"""

from django.core.exceptions import ValidationError

#: Qator harflari
LETTERS = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'

#: Bitta qatordagi javonlarning eng ko'p soni
MAX_SHELVES = 30


def parse_cell(cell: str) -> tuple[str, int] | None:
    """`'D3'` -> `('D', 3)`. Shakli noto'g'ri bo'lsa `None`."""
    cell = (cell or '').strip().upper()

    if len(cell) < 2:
        return None

    code, digits = cell[0], cell[1:]

    if code not in LETTERS or not digits.isdigit():
        return None

    level = int(digits)

    if level < 1:
        return None

    return code, level


def runs():
    """Faol javon qatorlari, eshikdan boshlab tartib bilan."""
    from apps.inventory.models import ShelfRun

    return ShelfRun.objects.filter(is_active=True)


def cell_names() -> list[str]:
    """Ombordagi hamma manzil: `A1`, `A2`, ... `E2`."""
    return [cell for run in runs() for cell in run.cells]


def normalize_cell(cell: str, known=None) -> str:
    """Manzilni tekshiradi va bir xil ko'rinishga keltiradi.

    Bo'sh qiymat ruxsat etiladi — tovarning joyi belgilanmagan degani.
    Mavjud bo'lmagan javon rad etiladi: `D12` deb yozilgan tovarni
    to'qqiz javonli devordan hech kim topa olmaydi.

    `known` — qatorlar ro'yxati; berilmasa bazadan o'qiladi. Ko'p
    qatorni ketma-ket tekshirganda (kirim hujjati) uni bir marta olib
    uzatgan ma'qul.
    """
    cell = (cell or '').strip().upper()

    if not cell:
        return ''

    known = list(runs()) if known is None else list(known)

    if not known:
        raise ValidationError(
            'Ombor javonlari hali kiritilmagan. «Ombor» sahifasida javon qatorlarini qo‘shing.'
        )

    parsed = parse_cell(cell)

    if parsed is None:
        raise ValidationError(f'«{cell}» manzil noto‘g‘ri yozilgan. Masalan: A1, D3')

    code, level = parsed
    run = next((item for item in known if item.code == code), None)

    if run is None:
        letters = ', '.join(item.code for item in known)

        raise ValidationError(f'«{code}» degan javon qatori yo‘q. Bor qatorlar: {letters}')

    if level > run.shelves:
        raise ValidationError(
            f'«{run.name}»da {run.shelves} ta javon bor, {level}-javon yo‘q.'
        )

    return f'{code}{level}'


def warehouse():
    """Ombor joyi. Bitta do'konda u bitta."""
    from apps.inventory.models import Location

    return Location.objects.filter(kind=Location.Kind.WAREHOUSE, is_active=True).first()


def place(variant, cell: str) -> str:
    """Tovarga ombordagi javon manzilini beradi.

    Bo'sh qiymat manzilni o'chiradi. Qoldiq qatori yo'q bo'lsa
    yaratiladi: tovar hali kelmagan bo'lsa ham joyini oldindan
    belgilab qo'yish mumkin.
    """
    from apps.inventory.models import VariantStock

    cell = normalize_cell(cell)
    store = warehouse()

    if store is None:
        raise ValidationError('Ombor topilmadi')

    stock, _created = VariantStock.objects.get_or_create(variant=variant, location=store)

    if stock.cell != cell:
        stock.cell = cell
        stock.save(update_fields=['cell'])

    return cell


def cabinet() -> dict:
    """Ombor xaritasi: har javonda nima turibdi.

    Bo'sh javonlar ham qaytadi — ro'yxat to'liq ko'rinishi kerak.
    Joyi belgilanmagan tovarlar alohida ro'yxatda: xodim ularni ko'rib,
    joyini belgilab chiqadi. Qatorlardan tashqarida qolganlar ham
    alohida: javon qatori o'chirilgan bo'lsa, tovar o'sha yerda
    turganini jimgina yo'qotib bo'lmaydi.
    """
    from apps.inventory.models import VariantStock

    known = list(runs())
    store = warehouse()

    shelves = {cell: [] for run in known for cell in run.cells}
    loose = []
    outside = {}

    if store is not None:
        rows = (
            VariantStock.objects.filter(location=store, quantity__gt=0)
            .select_related('variant__product', 'variant__size', 'variant__color')
            .order_by('variant__product__name', 'variant__size__name', 'variant__color__name')
        )

        for stock in rows:
            item = {
                'variant': stock.variant_id,
                'name': stock.variant.product.name,
                'label': stock.variant.label,
                'quantity': stock.quantity,
            }

            if not stock.cell:
                loose.append(item)
            elif stock.cell in shelves:
                shelves[stock.cell].append(item)
            else:
                outside.setdefault(stock.cell, []).append(item)

    return {
        'runs': [
            {
                'code': run.code,
                'name': run.name,
                'shelves': [
                    {'cell': cell, 'items': shelves[cell]} for cell in run.cells
                ],
            }
            for run in known
        ],
        'unplaced': loose,
        'outside': outside,
    }
