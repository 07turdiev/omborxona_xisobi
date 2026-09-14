"""Import turlari va ularning ustunlari.

Sarlavhalar uch tilda tanitiladi: o'zbekcha (bizning shablon), ruscha
(StoreFlow shabloni va 1C'dan olingan fayllar) va inglizcha. Shu sababli
foydalanuvchi eski tizimdan eksport qilingan faylni ham ustun nomlarini
qo'lda o'zgartirmasdan yuklay oladi.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from apps.core.access import Perm
from apps.dataimport.parsing import normalize_header


@dataclass(frozen=True)
class Column:
    key: str
    #: Shablondagi sarlavha
    label: str
    aliases: tuple[str, ...] = ()
    required: bool = False
    #: Yo'riqnoma varag'idagi izoh
    hint: str = ''
    sample: object = ''
    #: Ustun faqat shu ruxsat bilan qabul qilinadi (kirim narxi)
    permission: str | None = None


@dataclass(frozen=True)
class ImportSpec:
    type: str
    title: str
    permission: Perm
    columns: tuple[Column, ...]
    filename: str
    #: Tanilsa ham e'tiborsiz qoldiriladigan sarlavhalar
    ignored: tuple[str, ...] = field(default=())

    def aliases(self, columns=None) -> dict[str, str]:
        index: dict[str, str] = {}

        for column in columns or self.columns:
            for alias in (column.label, column.key, *column.aliases):
                index.setdefault(normalize_header(alias), column.key)

        return index

    def ignored_headers(self, hidden=()) -> frozenset[str]:
        """E'tiborsiz sarlavhalar — ruxsati yo'q ustunlar ham shu yerga."""
        names = {normalize_header(name) for name in (*COMMON_IGNORED, *self.ignored)}

        for column in hidden:
            names.update(
                normalize_header(alias)
                for alias in (column.label, column.key, *column.aliases)
            )

        return frozenset(names)

    def split_columns(self, membership) -> tuple[list[Column], list[Column]]:
        """(ruxsat etilgan ustunlar, yashirilgan ustunlar)."""
        allowed, hidden = [], []

        for column in self.columns:
            if column.permission and not membership.has_perm(column.permission):
                hidden.append(column)
            else:
                allowed.append(column)

        return allowed, hidden


#: Bizda tashkilot so'rovdan aniqlanadi — fayldagi "Kompaniya" ustuni kerak emas
COMMON_IGNORED = ('Kompaniya', 'Компания', 'Код компании', 'Company', 'Company code', '№', 'N')

NOTES = Column(
    'notes', 'Izoh',
    aliases=('Примечание', 'Комментарий', 'Notes', 'Note', 'Comment'),
    hint='Ixtiyoriy',
)

STATUS = Column(
    'status', 'Holati',
    aliases=('Holat', 'Статус', 'Status'),
    hint='Faol / Nofaol. Bo‘sh bo‘lsa — faol',
    sample='Faol',
)

SKU = Column(
    'sku', 'Artikul',
    aliases=('SKU', 'Артикул', 'Код товара', 'Kod', 'Mahsulot kodi', 'Shtrix-kod', 'Barcode'),
    required=True,
    hint='Mahsulot artikuli (SKU) yoki shtrix-kodi',
    sample='CEM-400',
)

WAREHOUSE = Column(
    'warehouse', 'Ombor',
    aliases=('Склад', 'Warehouse', 'Ombor kodi'),
    required=True,
    hint='Ombor nomi yoki kodi',
    sample='Asosiy ombor',
)

DATE = Column(
    'date', 'Sana',
    aliases=('Дата', 'Date'),
    required=True,
    hint='KK.OO.YYYY. Kelajak sana qabul qilinmaydi',
    sample='14.09.2026',
)

QUANTITY = Column(
    'quantity', 'Miqdor',
    aliases=('Soni', 'Количество', 'Кол-во', 'Quantity', 'Qty'),
    required=True,
    hint='Musbat son',
    sample=10,
)

UNIT = Column(
    'unit', 'Birlik',
    aliases=('O‘lchov birligi', 'Ед. изм.', 'Единица измерения', 'Unit'),
    hint='Bo‘sh bo‘lsa — mahsulotning asosiy birligi. O‘ram (qop, quti) '
         'mahsulot kartochkasida sozlangan bo‘lishi kerak',
)

PAYMENT = Column(
    'payment_method', 'To‘lov usuli',
    aliases=("To'lov", 'Способ оплаты', 'Оплата', 'Payment method', 'Payment'),
    hint='Naqd / Karta / O‘tkazma / Aralash. Bo‘sh bo‘lsa — naqd',
    sample='Naqd',
)

MIN_STOCK = Column(
    'min_stock', 'Minimal qoldiq',
    aliases=('Мин. остаток', 'Минимальный остаток', 'Minimum stock', 'Min stock'),
    hint='Shundan kam qolganda ogohlantiriladi',
)


CATEGORIES = ImportSpec(
    type='categories',
    title='Kategoriyalar',
    permission=Perm.CATEGORIES,
    filename='import-kategoriyalar',
    columns=(
        Column(
            'name', 'Kategoriya nomi',
            aliases=('Kategoriya', 'Nomi', 'Название категории', 'Категория',
                     'Category', 'Category name', 'Name'),
            required=True,
            sample='Sement',
        ),
        Column(
            'parent', 'Yuqori kategoriya',
            aliases=('Ota kategoriya', 'Родительская категория', 'Parent', 'Parent category'),
            hint='Bo‘sh bo‘lsa — ildiz. Chuqur yo‘l: "Qurilish > Quruq aralashmalar". '
                 'Mavjud bo‘lmasa, yaratiladi',
            sample='Qurilish mollari',
        ),
        Column(
            'subcategories', 'Ostki kategoriyalar',
            aliases=('Подкатегории', 'Subcategories'),
            hint='Nuqtali vergul bilan: "M400; M500"',
            sample='M400; M500',
        ),
        Column(
            'code_prefix', 'Kod prefiksi',
            aliases=('Prefiks', 'Префикс', 'Префикс SKU', 'SKU prefix', 'Prefix'),
            hint='10 belgigacha',
            sample='CEM',
        ),
        Column(
            'default_unit', 'Standart birlik',
            aliases=('O‘lchov birligi', 'Birlik', 'Ед. изм.', 'Единица измерения',
                     'Unit', 'Default unit'),
            hint='Yangi mahsulotlar uchun: kg, dona, qop, m2',
            sample='qop',
        ),
        STATUS,
    ),
    ignored=('Izoh', 'Примечание', 'Комментарий', 'Notes'),
)

PRODUCTS = ImportSpec(
    type='products',
    title='Mahsulotlar',
    permission=Perm.PRODUCTS,
    filename='import-mahsulotlar',
    columns=(
        Column(
            'category', 'Kategoriya',
            aliases=('Категория', 'Category'),
            required=True,
            hint='Mavjud kategoriya. Chuqur yo‘l: "Qurilish > Sement"',
            sample='Qurilish mollari',
        ),
        Column(
            'subcategory', 'Ostki kategoriya',
            aliases=('Подкатегория', 'Subcategory'),
            hint='Kategoriya ichidagi mavjud ostki kategoriya',
            sample='Sement',
        ),
        Column(
            'sku', 'Artikul',
            aliases=('SKU', 'Артикул', 'Код товара', 'Kod', 'Mahsulot kodi'),
            hint='Mavjud artikul bo‘lsa — mahsulot yangilanadi. Bo‘sh bo‘lsa — '
                 'avtomatik beriladi',
            sample='CEM-400',
        ),
        Column(
            'name', 'Mahsulot nomi',
            aliases=('Nomi', 'Mahsulot', 'Название товара', 'Товар', 'Наименование',
                     'Product', 'Product name', 'Name'),
            required=True,
            sample='Sement M400, 50 kg',
        ),
        Column('brand', 'Brend', aliases=('Бренд', 'Brand'), sample='Qizilqumsement'),
        Column('model', 'Model', aliases=('Модель',)),
        Column(
            'barcode', 'Shtrix-kod',
            aliases=('Shtrixkod', 'Штрих-код', 'Штрихкод', 'Barcode', 'EAN'),
            hint='Boshqa mahsulotda bo‘lmasligi kerak',
            sample='4780000000011',
        ),
        Column(
            'unit', 'Birlik',
            aliases=('O‘lchov birligi', 'Ед. изм.', 'Единица измерения', 'Unit'),
            hint='Qoldiq shu birlikda yuritiladi. Bo‘sh bo‘lsa — kategoriyadan',
            sample='qop',
        ),
        Column(
            'purchase_price', 'Kirim narxi',
            aliases=('Закупочная цена', 'Цена закупки', 'Purchase price'),
            sample=52000,
            permission=Perm.VIEW_PURCHASE_PRICE,
        ),
        Column(
            'sale_price', 'Sotuv narxi',
            aliases=('Цена продажи', 'Продажная цена', 'Цена', 'Sale price', 'Price'),
            sample=58000,
        ),
        MIN_STOCK,
        STATUS,
        Column(
            'notes', 'Tavsif',
            aliases=('Izoh', 'Описание', 'Примечание', 'Комментарий', 'Description', 'Notes'),
        ),
    ),
)

PURCHASES = ImportSpec(
    type='purchases',
    title='Kirim',
    permission=Perm.IMPORTS,
    filename='import-kirim',
    columns=(
        WAREHOUSE,
        DATE,
        Column(
            'partner', 'Yetkazib beruvchi',
            aliases=('Kontragent', 'Поставщик', 'Контрагент', 'Supplier'),
            hint='Kontragentlar ro‘yxatida bo‘lmasa, yangi yetkazib beruvchi yaratiladi',
            sample='Qurilish Savdo MChJ',
        ),
        Column(
            'external_number', 'Yetkazib beruvchi hujjati',
            aliases=('Nakladnoy', 'Hujjat raqami', 'Документ поставщика', 'Накладная',
                     'Номер накладной', 'Supplier invoice', 'Invoice'),
            hint='Bir xil ombor, sana, yetkazib beruvchi va hujjat raqamli qatorlar '
                 'bitta kirim hujjatiga yig‘iladi',
            sample='NK-00125',
        ),
        PAYMENT,
        SKU,
        QUANTITY,
        UNIT,
        Column(
            'purchase_price', 'Kirim narxi',
            aliases=('Закупочная цена', 'Цена закупки', 'Purchase price', 'Narxi'),
            required=True,
            hint='Ko‘rsatilgan birlik uchun narx',
            sample=52000,
        ),
        Column(
            'sale_price', 'Sotuv narxi',
            aliases=('Цена продажи', 'Продажная цена', 'Sale price'),
            hint='Berilsa, mahsulotning sotuv narxi yangilanadi',
            sample=58000,
        ),
        MIN_STOCK,
        Column(
            'batch', 'Partiya',
            aliases=('Partiya kodi', 'Партия', 'Batch', 'Lot'),
            hint='Yaroqlilik muddati bor tovar uchun',
        ),
        Column(
            'expiry_date', 'Yaroqlilik muddati',
            aliases=('Срок годности', 'Expiry date', 'Expiry'),
            hint='KK.OO.YYYY. Partiya kodi bilan birga',
        ),
        Column(
            'location', 'Saqlash joyi',
            aliases=('Место хранения', 'Полка', 'Расположение', 'Location'),
            hint='Qator izohiga yoziladi',
        ),
        NOTES,
    ),
    ignored=('Наценка', 'Наценка, %', 'Markup', 'Ustama'),
)

SALES = ImportSpec(
    type='sales',
    title='Sotuv',
    permission=Perm.SALES,
    filename='import-sotuv',
    columns=(
        WAREHOUSE,
        DATE,
        Column(
            'partner', 'Xaridor',
            aliases=('Mijoz', 'Kontragent', 'Покупатель', 'Контрагент', 'Buyer', 'Customer'),
            hint='Kontragentlar ro‘yxatida bo‘lmasa, mijoz ismi sifatida yoziladi',
            sample='Chakana xaridor',
        ),
        SKU,
        QUANTITY,
        UNIT,
        Column(
            'sale_price', 'Sotuv narxi',
            aliases=('Narxi', 'Цена продажи', 'Цена', 'Sale price', 'Price'),
            hint='Bo‘sh bo‘lsa — mahsulot kartochkasidagi sotuv narxi',
            sample=58000,
        ),
        Column(
            'discount_percent', 'Chegirma, %',
            aliases=('Chegirma', 'Скидка', 'Скидка, %', 'Discount'),
            hint='0 dan 100 gacha',
            sample=0,
        ),
        PAYMENT,
        NOTES,
    ),
)

SPECS: dict[str, ImportSpec] = {
    spec.type: spec for spec in (CATEGORIES, PRODUCTS, PURCHASES, SALES)
}
