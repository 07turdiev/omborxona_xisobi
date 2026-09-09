"""Ma'lumotni Excel faylga chiqarish.

Buxgalteriya odatda `.xlsx` talab qiladi: raqamlarni qo'shish, filtrlash
va boshqa jadvallar bilan solishtirish uchun.

**Sonlar matn emas, son sifatida yoziladi.** Aks holda Excel ularni
qo'sha olmaydi va foydalanuvchi har safar qo'lda formatlashi kerak
bo'lardi. Bu `Decimal` → `float` o'girishni talab qiladi; pul summalari
uchun bu xavfsiz, chunki `float64` 2^53 gacha butun sonni aniq saqlaydi
— so'mda bu 90 trillion tiyin, ya'ni amalda cheklov emas.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from django.http import HttpResponse
from django.utils import timezone
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

#: Sarlavha qatori uslubi
HEADER_FILL = PatternFill('solid', fgColor='F1EDFF')
HEADER_FONT = Font(bold=True, size=10)

#: Ustun turlari — format va kenglikni belgilaydi
MONEY = 'money'
QUANTITY = 'quantity'
DATE = 'date'
DATETIME = 'datetime'
TEXT = 'text'
NUMBER = 'number'

FORMATS = {
    MONEY: '#,##0.00',
    QUANTITY: '#,##0.000',
    NUMBER: '#,##0',
    DATE: 'DD.MM.YYYY',
    DATETIME: 'DD.MM.YYYY HH:MM',
}

#: Ruxsat etilgan ustun turlari
KINDS = frozenset({MONEY, QUANTITY, NUMBER, DATE, DATETIME, TEXT})

WIDTHS = {
    MONEY: 16,
    QUANTITY: 14,
    NUMBER: 10,
    DATE: 12,
    DATETIME: 18,
    TEXT: 22,
}


class Column:
    """Chiqariladigan ustun ta'rifi.

    `key` — qator lug'atidagi kalit yoki obyekt atributi.
    `kind` — format (yuqoridagi doimiylardan).
    """

    __slots__ = ('key', 'title', 'kind', 'width')

    def __init__(self, key: str, title: str, kind: str = TEXT, width: int | None = None):
        # Noto'g'ri tur jimgina o'tib ketsa, son matn bo'lib qolardi va
        # buni faqat Excel'da fayl ochilganda sezgan bo'lardik.
        if kind not in KINDS:
            raise ValueError(f"Noma'lum ustun turi: {kind!r}")

        self.key = key
        self.title = title
        self.kind = kind
        self.width = width or WIDTHS.get(kind, 20)


def _value_of(row: Any, key: str) -> Any:
    """Qatordan qiymatni oladi — lug'at ham, obyekt ham bo'lishi mumkin."""
    if isinstance(row, dict):
        value = row

        # Ichma-ich kalit: "variant.product.name"
        for part in key.split('.'):
            if value is None:
                return None

            value = value.get(part) if isinstance(value, dict) else getattr(value, part, None)

        return value

    value = row

    for part in key.split('.'):
        if value is None:
            return None

        value = getattr(value, part, None)

    return value


#: Son sifatida yozilishi kerak bo'lgan ustunlar
NUMERIC_KINDS = frozenset({MONEY, QUANTITY, NUMBER})


def _cell_value(value: Any, kind: str) -> Any:
    """Qiymatni Excel tushunadigan tipga o'giradi."""
    if value is None:
        return None

    # DRF `Decimal`ni matn sifatida qaytaradi ("1500.00"). Uni shundayligicha
    # yozsak Excel matn deb qabul qiladi va qo'sha olmaydi — shuning uchun
    # ustun turiga qarab qaytadan songa o'giramiz.
    if isinstance(value, str):
        if kind in NUMERIC_KINDS:
            try:
                return float(Decimal(value))
            except (InvalidOperation, ValueError):
                return value

        if kind in (DATE, DATETIME):
            return _parse_date(value)

        return value

    if isinstance(value, Decimal):
        # Son sifatida yoziladi — Excel'da qo'shish uchun
        return float(value)

    if isinstance(value, (datetime, date)):
        # Vaqt zonasi Excel'da yo'q, mahalliy vaqtga o'giramiz
        if isinstance(value, datetime) and timezone.is_aware(value):
            value = timezone.localtime(value)

        return value.replace(tzinfo=None) if isinstance(value, datetime) else value

    if isinstance(value, bool):
        return 'ha' if value else 'yo\'q'

    return value


def _parse_date(value: str) -> Any:
    """ISO satrni sana/vaqtga o'giradi, aks holda matnni qaytaradi."""
    text = value.strip()

    if not text:
        return None

    # `Z` qo'shimchasini `fromisoformat` 3.11 gacha tushunmaydi
    normalized = text[:-1] + '+00:00' if text.endswith('Z') else text

    for parser in (datetime.fromisoformat, date.fromisoformat):
        try:
            parsed = parser(normalized)
        except ValueError:
            continue

        if isinstance(parsed, datetime) and timezone.is_aware(parsed):
            parsed = timezone.localtime(parsed)

        return parsed.replace(tzinfo=None) if isinstance(parsed, datetime) else parsed

    return value


def add_sheet(
    workbook: Workbook,
    columns: Sequence[Column],
    rows: Iterable[Any],
    *,
    sheet_name: str = 'Hisobot',
    title: str = '',
    meta: Sequence[tuple[str, str]] = (),
    sheet: Any = None,
) -> Any:
    """Kitobga bitta varaq qo'shadi.

    Arguments:
        title: varaq boshidagi sarlavha (masalan "Qoldiqlar").
        meta: sarlavha ostidagi qatorlar — davr, ombor, tashkilot.
            Hisobot qaysi shartlarda olinganini bilmasdan uni keyin
            tushunib bo'lmaydi.
        sheet: tayyor varaq (yangi kitobning birinchisi uchun).
    """
    if sheet is None:
        sheet = workbook.create_sheet()

    # Excel varaq nomida ba'zi belgilarni qabul qilmaydi
    sheet.title = sheet_name[:31].replace('/', '-').replace('\\', '-')

    offset = 0

    if title:
        sheet.cell(row=1, column=1, value=title).font = Font(bold=True, size=13)
        offset += 1

    for key, value in meta:
        offset += 1
        sheet.cell(row=offset, column=1, value=f'{key}:').font = Font(bold=True, size=9)
        sheet.cell(row=offset, column=2, value=value).font = Font(size=9)

    if offset:
        offset += 1  # bo'sh qator

    header_row = offset + 1

    for index, column in enumerate(columns, start=1):
        cell = sheet.cell(row=header_row, column=index, value=column.title)
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
        cell.alignment = Alignment(vertical='center', wrap_text=True)

        sheet.column_dimensions[get_column_letter(index)].width = column.width

    for row_index, row in enumerate(rows, start=header_row + 1):
        for column_index, column in enumerate(columns, start=1):
            value = _cell_value(_value_of(row, column.key), column.kind)
            cell = sheet.cell(row=row_index, column=column_index, value=value)

            if column.kind in FORMATS:
                cell.number_format = FORMATS[column.kind]

    # Sarlavha qatori doim ko'rinib tursin va filtr ishlasin
    sheet.freeze_panes = sheet.cell(row=header_row + 1, column=1)
    sheet.auto_filter.ref = (
        f'A{header_row}:{get_column_letter(len(columns))}{sheet.max_row}'
    )

    return sheet


def build_workbook(
    columns: Sequence[Column],
    rows: Iterable[Any],
    *,
    sheet_name: str = 'Hisobot',
    title: str = '',
    meta: Sequence[tuple[str, str]] = (),
) -> Workbook:
    """Bitta jadvalni Excel kitobiga aylantiradi."""
    workbook = Workbook()

    add_sheet(
        workbook,
        columns,
        rows,
        sheet_name=sheet_name,
        title=title,
        meta=meta,
        sheet=workbook.active,
    )

    return workbook


def context_meta(
    request,
    *,
    warehouse_id=None,
    extra: Sequence[tuple[str, str]] = (),
) -> list[tuple[str, str]]:
    """Fayl qaysi shartlarda olinganini tavsiflovchi qatorlar.

    Tashkilot, ombor va yaratilgan vaqt har bir eksportda kerak:
    faylni bir hafta keyin ochgan odam uning qaysi do'kon va qaysi
    omborga tegishli ekanini boshqa yo'l bilan bilolmaydi.
    """
    from apps.tenants.models import Tenant
    from apps.warehouse.models import Warehouse

    tenant = Tenant.objects.filter(pk=getattr(request, 'tenant_id', None)).first()

    if warehouse_id:
        warehouse = Warehouse.objects.filter(pk=warehouse_id).first()
        warehouse_name = warehouse.name if warehouse else str(warehouse_id)
    else:
        warehouse_name = 'barchasi'

    return [
        ('Tashkilot', tenant.name if tenant else '—'),
        ('Ombor', warehouse_name),
        *extra,
        ('Yaratilgan', timezone.localtime().strftime('%d.%m.%Y %H:%M')),
    ]


def excel_response(workbook: Workbook, filename: str) -> HttpResponse:
    """Kitobni yuklab olinadigan javobga o'raydi."""
    stamp = timezone.localdate().strftime('%Y-%m-%d')
    full_name = f'{filename}-{stamp}.xlsx'

    response = HttpResponse(
        content_type=(
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
    )
    # Fayl nomida o'zbekcha harflar bo'lishi mumkin — RFC 5987
    response['Content-Disposition'] = f"attachment; filename*=UTF-8''{full_name}"

    workbook.save(response)

    return response
