"""Import qiluvchilar: har tur uchun tekshirish va saqlash.

Oldindan ko'rish (preview) va saqlash (commit) bir xil `validate()` dan
o'tadi. Saqlash faylni qayta o'qiydi va qayta tekshiradi — server
oraliq holatni saqlamaydi, ya'ni preview bilan commit orasida baza
o'zgargan bo'lsa (kimdir o'sha tovarni sotib yuborgan), xato commit'da
aniqlanadi.

Import **hammasi yoki hech narsa**: bitta qatorda xato bo'lsa, fayl
umuman saqlanmaydi. Yarim import qilingan kirim fayli eng yomon holat —
foydalanuvchi qaysi qatorlar o'tganini bilmay, faylni qayta yuklaydi va
tovar ikki marta kirim bo'ladi.
"""

from __future__ import annotations

import re
from collections import OrderedDict
from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import Sum
from django.db.models.functions import Upper
from django.utils import timezone

from apps.audit.models import AuditEvent
from apps.audit.services import record
from apps.catalog.models import Barcode, Category, Product, ProductUnit, Variant
from apps.dataimport import specs
from apps.dataimport.parsing import clean_text, name_key, parse_date, parse_decimal
from apps.documents import services as documents
from apps.documents.models import Document
from apps.partners.models import Partner
from apps.stock.models import Batch, StockBalance, StockMovement
from apps.warehouse.models import Warehouse, WarehouseAccess

Action = AuditEvent.Action
PaymentMethod = Document.PaymentMethod

ZERO = Decimal('0')
MONEY_PLACES = Decimal('0.01')
QUANTITY_PLACES = Decimal('0.001')

#: Pul va miqdor chegaralari: `numeric(18, 2)` ga sig'adigan, lekin
#: "ustunlar almashib ketgan" (shtrix-kod narx ustunida) holatni ushlaydigan
MAX_MONEY = Decimal('1000000000000')
MAX_QUANTITY = Decimal('1000000000')


class CommitError(Exception):
    """Saqlash paytidagi xato — butun import bekor qilinadi."""

    def __init__(self, messages):
        super().__init__('; '.join(messages))
        self.messages = list(messages)


@dataclass
class RowResult:
    row: int
    values: dict
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    #: create | update | skip
    action: str = 'create'
    #: Tahlil qilingan qiymatlar — javobga chiqmaydi
    data: dict = field(default_factory=dict)

    def as_dict(self) -> dict:
        return {
            'row': self.row,
            'values': self.values,
            'errors': self.errors,
            'warnings': self.warnings,
            'action': 'error' if self.errors else self.action,
        }


def _words(*items: str) -> set[str]:
    return {name_key(item) for item in items}


ACTIVE_WORDS = _words('faol', 'active', 'активен', 'активный', 'ha', 'да', 'yes', '1', 'true')
INACTIVE_WORDS = _words(
    'nofaol', 'inactive', 'неактивен', 'неактивный', 'arxiv', 'архив',
    "yo'q", 'нет', 'no', '0', 'false',
)

PAYMENTS: dict[str, str] = {}

for _method, _names in {
    PaymentMethod.CASH: ('naqd', 'naqd pul', 'наличные', 'наличными', 'нал', 'cash'),
    PaymentMethod.CARD: ('karta', 'plastik', 'terminal', 'uzcard', 'humo', 'карта',
                         'картой', 'пластик', 'card'),
    PaymentMethod.TRANSFER: ("o'tkazma", "pul o'tkazma", "bank o'tkazmasi", 'perechisleniye',
                             'перечисление', 'банковский перевод', 'перевод',
                             'безналичный', 'безнал', 'transfer', 'bank transfer'),
    PaymentMethod.MIXED: ('aralash', 'смешанная', 'смешанный', 'mixed'),
    PaymentMethod.DEFERRED: ('keyinroq', 'kechiktirilgan', 'qarz', 'qarzga', 'nasiya',
                             'отсрочка', 'в долг', 'долг', 'deferred', 'credit'),
}.items():
    for _name in _names:
        PAYMENTS[name_key(_name)] = _method

_PATH_SPLIT = re.compile(r'\s*[>›»]\s*|\s+/\s+')


def split_path(text: str) -> list[str]:
    """ "Qurilish > Sement" → ["Qurilish", "Sement"]."""
    return [part for part in (' '.join(p.split()) for p in _PATH_SPLIT.split(text or '')) if part]


def max_length(model, field_name: str) -> int:
    return model._meta.get_field(field_name).max_length


class CategoryTree:
    """Kategoriyalar nom-yo'li bo'yicha: ("qurilish", "sement") → Category."""

    def __init__(self):
        self.by_id = {category.pk: category for category in Category.objects.all()}
        self.by_path: dict[tuple, Category] = {}

        for category in self.by_id.values():
            self.by_path.setdefault(self.key_path(category), category)

    def key_path(self, category) -> tuple:
        names, node, seen = [], category, set()

        while node is not None and node.pk not in seen:
            seen.add(node.pk)
            names.append(name_key(node.name))
            node = self.by_id.get(node.parent_id)

        return tuple(reversed(names))

    def get(self, keys: tuple):
        return self.by_path.get(keys)


class BaseImporter:
    spec: specs.ImportSpec
    #: Tarixdagi obyekt turi
    object_type = ''

    def __init__(self, request, columns, *, confirm: bool = True):
        self.request = request
        self.membership = request.membership
        self.keys = {column.key for column in columns}
        self.labels = {column.key: column.label for column in columns}
        self.confirm = confirm
        self.today = timezone.localdate()

    # -- Qiymatlar ----------------------------------------------------

    def text(self, result, raw, key, *, required=False, limit=None) -> str:
        value = clean_text(raw.get(key))
        label = self.labels.get(key, key)

        if required and not value:
            result.errors.append(f'«{label}» to‘ldirilmagan')
        elif limit and len(value) > limit:
            result.errors.append(f'«{label}» {limit} belgidan oshmasligi kerak')

        return value

    def number(
        self, result, raw, key, *, required=False, positive=False,
        maximum=MAX_MONEY, places=MONEY_PLACES,
    ) -> Decimal | None:
        label = self.labels.get(key, key)
        value = raw.get(key)

        try:
            number = parse_decimal(value)
        except ValueError:
            result.errors.append(f'«{label}»: son emas — «{clean_text(value)}»')
            return None

        if number is None:
            if required:
                result.errors.append(f'«{label}» to‘ldirilmagan')
            return None

        if number < 0 or (positive and number == 0):
            result.errors.append(
                f'«{label}» musbat bo‘lishi kerak' if positive
                else f'«{label}» manfiy bo‘lmasligi kerak'
            )
            return None

        if number > maximum:
            result.errors.append(f'«{label}»: juda katta qiymat ({clean_text(value)})')
            return None

        return number.quantize(places, rounding=ROUND_HALF_UP)

    def date(self, result, raw, key, *, required=False):
        label = self.labels.get(key, key)
        value = raw.get(key)

        try:
            parsed = parse_date(value)
        except ValueError:
            result.errors.append(f'«{label}»: sana noto‘g‘ri — «{clean_text(value)}»')
            return None

        if parsed is None and required:
            result.errors.append(f'«{label}» to‘ldirilmagan')

        return parsed

    def status(self, result, raw) -> bool | None:
        value = clean_text(raw.get('status'))

        if not value:
            return None

        key = name_key(value)

        if key in ACTIVE_WORDS:
            return True

        if key in INACTIVE_WORDS:
            return False

        result.errors.append(f'«Holati» noma’lum: «{value}». Faol yoki Nofaol')
        return None

    # -- Oqim ---------------------------------------------------------

    def validate(self, rows) -> list[RowResult]:
        self.prepare(rows)

        results = []

        for number, raw in rows:
            values = {key: clean_text(value) for key, value in raw.items() if key in self.keys}
            result = RowResult(row=number, values=values)
            self.validate_row(result, raw)
            results.append(result)

        self.finish(results)

        return results

    def prepare(self, rows) -> None:
        """Qidiruv lug'atlarini bitta so'rovlar bilan yuklaydi."""

    def validate_row(self, result: RowResult, raw: dict) -> None:
        raise NotImplementedError

    def finish(self, results: list[RowResult]) -> None:
        """Qatorlararo tekshiruvlar (qoldiq, takroriy hujjat)."""

    def document_count(self, results) -> int:
        return 0

    def commit(self, results: list[RowResult], *, meta: dict) -> dict:
        raise NotImplementedError

    def audit_summary(self, meta: dict, **counts) -> None:
        details = ', '.join(f'{label}: {value}' for label, value in counts.items())

        record(
            Action.IMPORT,
            self.object_type,
            request=self.request,
            object_repr=f'Excel: {meta["filename"]}',
            details=details,
            changes={'file_hash': meta['file_hash'], 'rows': meta['rows']},
        )


# =====================================================================
# Kategoriyalar
# =====================================================================


class CategoryImporter(BaseImporter):
    spec = specs.CATEGORIES
    object_type = 'category'

    def prepare(self, rows):
        self.tree = CategoryTree()
        #: Yaratiladigan yo'llar (fayl tartibida)
        self.planned: set[tuple] = set()
        self.seen: dict[tuple, int] = {}
        self.name_limit = max_length(Category, 'name')

    def validate_row(self, result, raw):
        name = self.text(result, raw, 'name', required=True, limit=self.name_limit)
        parent = split_path(clean_text(raw.get('parent')))
        subs = [
            ' '.join(part.split())
            for part in re.split(r'[;\n]', str(raw.get('subcategories') or ''))
            if part.strip()
        ]
        prefix = self.text(result, raw, 'code_prefix', limit=10).upper()
        unit = self.text(result, raw, 'default_unit', limit=max_length(Category, 'default_unit'))
        active = self.status(result, raw)

        if any(len(part) > self.name_limit for part in (*parent, *subs)):
            result.errors.append(f'Kategoriya nomi {self.name_limit} belgidan oshmasligi kerak')

        if result.errors:
            return

        parent_keys = tuple(name_key(part) for part in parent)
        full = (*parent_keys, name_key(name))

        if full in self.seen:
            result.action = 'skip'
            result.warnings.append(
                f'Shu kategoriya {self.seen[full]}-qatorda ham bor — bu qator o‘tkazib yuboriladi'
            )
            return

        self.seen[full] = result.row

        new_parents = []

        for depth in range(1, len(parent_keys) + 1):
            key = parent_keys[:depth]

            if self.tree.get(key) is None and key not in self.planned:
                self.planned.add(key)
                new_parents.append(parent[depth - 1])

        if new_parents:
            result.warnings.append('Yuqori kategoriya ham yaratiladi: ' + ' > '.join(new_parents))

        existing = self.tree.get(full)
        changes = False

        if existing is not None:
            changes = (
                (prefix and prefix != existing.code_prefix)
                or (unit and unit != existing.default_unit)
                or (active is not None and active != existing.is_active)
            )
            result.action = 'update' if changes else 'skip'
        elif full in self.planned:
            # Oldingi qatorda yuqori kategoriya sifatida rejalangan
            result.action = 'update' if (prefix or unit or active is not None) else 'skip'
        else:
            self.planned.add(full)
            result.action = 'create'

        new_subs = []

        for sub in subs:
            key = (*full, name_key(sub))

            if self.tree.get(key) is None and key not in self.planned:
                self.planned.add(key)
                new_subs.append(sub)

        if new_subs and result.action == 'skip':
            result.action = 'update'

        result.data = {
            'path': [*parent, name],
            'subs': subs,
            'fields': {
                key: value
                for key, value in (
                    ('code_prefix', prefix), ('default_unit', unit), ('is_active', active),
                )
                if value not in ('', None)
            },
        }

    def commit(self, results, *, meta):
        cache: dict[tuple, Category] = {}
        created = updated = 0

        def ensure(names):
            nonlocal created
            keys = tuple(name_key(part) for part in names)
            parent = None

            for depth in range(1, len(keys) + 1):
                key = keys[:depth]
                node = cache.get(key) or self.tree.get(key)

                if node is None:
                    node = Category(name=names[depth - 1], parent=parent)
                    node.save()
                    created += 1

                cache[key] = node
                parent = node

            return parent

        for result in results:
            if result.action == 'skip':
                continue

            category = ensure(result.data['path'])
            changed = [
                key for key, value in result.data['fields'].items()
                if getattr(category, key) != value
            ]

            if changed:
                for key in changed:
                    setattr(category, key, result.data['fields'][key])

                category.save(update_fields=[*changed, 'updated_at'])

                if self.tree.get(tuple(name_key(p) for p in result.data['path'])) is not None:
                    updated += 1

            for sub in result.data['subs']:
                ensure([*result.data['path'], sub])

        self.audit_summary(meta, **{'yangi': created, 'yangilandi': updated})

        return {'created': created, 'updated': updated}


# =====================================================================
# Mahsulotlar
# =====================================================================


def _barcode_type(code: str) -> str:
    if code.isdigit() and len(code) == 13:
        return Barcode.CodeType.EAN13

    if code.isdigit() and len(code) == 8:
        return Barcode.CodeType.EAN8

    return Barcode.CodeType.OTHER


class ProductImporter(BaseImporter):
    spec = specs.PRODUCTS
    object_type = 'product'

    def prepare(self, rows):
        self.tree = CategoryTree()

        skus = {clean_text(raw.get('sku')).upper() for _, raw in rows if clean_text(raw.get('sku'))}
        self.variants: dict[str, Variant] = {}

        for variant in (
            Variant.objects.select_related('product')
            .annotate(sku_upper=Upper('sku'))
            .filter(sku_upper__in=skus)
        ):
            self.variants.setdefault(variant.sku.upper(), variant)

        codes = {
            Barcode.normalize(clean_text(raw.get('barcode')))
            for _, raw in rows if clean_text(raw.get('barcode'))
        }
        self.barcodes = dict(
            Barcode.objects.filter(code_normalized__in=codes)
            .values_list('code_normalized', 'variant_id')
        )

        # Artikulsiz qatorlar mavjud mahsulotga nomi bo'yicha bog'lanadi
        names = {
            clean_text(raw.get('name')).lower()
            for _, raw in rows if not clean_text(raw.get('sku'))
        }
        self.products: dict[tuple, Product] = {}

        if names:
            from django.db.models.functions import Lower

            for product in (
                Product.objects.annotate(name_lower=Lower('name'))
                .filter(name_lower__in=names)
                .prefetch_related('variants')
            ):
                self.products.setdefault((product.category_id, name_key(product.name)), product)

        self.seen_skus: dict[str, int] = {}
        self.seen_codes: dict[str, int] = {}
        self.seen_names: dict[tuple, int] = {}

    def validate_row(self, result, raw):
        name = self.text(result, raw, 'name', required=True, limit=max_length(Product, 'name'))
        category_text = self.text(result, raw, 'category', required=True)
        subcategory = self.text(result, raw, 'subcategory')
        sku = self.text(result, raw, 'sku', limit=max_length(Variant, 'sku'))
        brand = self.text(result, raw, 'brand', limit=max_length(Product, 'brand'))
        model = self.text(result, raw, 'model', limit=max_length(Product, 'model'))
        barcode = self.text(result, raw, 'barcode', limit=max_length(Barcode, 'code'))
        unit = self.text(result, raw, 'unit', limit=max_length(Product, 'base_unit'))
        notes = str(raw.get('notes') or '').strip()
        active = self.status(result, raw)

        prices = {}

        for key in ('purchase_price', 'sale_price'):
            if key in self.keys:
                prices[key] = self.number(result, raw, key)

        min_stock = self.number(
            result, raw, 'min_stock', maximum=MAX_QUANTITY, places=QUANTITY_PLACES
        )

        path = split_path(category_text)

        if subcategory:
            path.append(subcategory)

        category = self.tree.get(tuple(name_key(part) for part in path)) if path else None

        if path and category is None:
            result.errors.append(
                f'Kategoriya topilmadi: {" > ".join(path)}. Avval kategoriyani yarating '
                'yoki kategoriyalar faylini import qiling'
            )

        variant = None

        if sku:
            first = self.seen_skus.setdefault(sku.upper(), result.row)

            if first != result.row:
                result.errors.append(f'Artikul {sku} {first}-qatorda ham bor')

            variant = self.variants.get(sku.upper())
        elif category is not None and name:
            key = (category.pk, name_key(name))
            first = self.seen_names.setdefault(key, result.row)

            if first != result.row:
                result.errors.append(f'Shu kategoriyada «{name}» {first}-qatorda ham bor')

            product = self.products.get(key)

            if product is not None:
                product_variants = list(product.variants.all())

                if len(product_variants) == 1:
                    variant = product_variants[0]
                else:
                    result.errors.append(
                        f'«{name}» mahsulotining {len(product_variants)} ta varianti bor — '
                        'qaysi biri yangilanishini artikul bilan ko‘rsating'
                    )

        normalized = Barcode.normalize(barcode)

        if normalized:
            first = self.seen_codes.setdefault(normalized, result.row)

            if first != result.row:
                result.errors.append(f'Shtrix-kod {barcode} {first}-qatorda ham bor')

            owner = self.barcodes.get(normalized)

            if owner is not None and (variant is None or owner != variant.pk):
                result.errors.append(f'Shtrix-kod {barcode} boshqa mahsulotga biriktirilgan')

        if result.errors:
            return

        result.action = 'update' if variant else 'create'

        if variant is not None and category is not None and variant.product.category_id != category.pk:
            result.warnings.append('Mahsulot kategoriyasi o‘zgaradi')

        result.data = {
            'variant': variant,
            'category': category,
            'sku': sku,
            'barcode': barcode,
            'product': {
                'name': name, 'brand': brand, 'model': model,
                'description': notes, 'base_unit': unit,
            },
            'variant_fields': {**prices, 'min_stock': min_stock},
            'active': active,
        }

    def finish(self, results):
        """Harakati bor mahsulotning asosiy birligini o'zgartirishni taqiqlaydi.

        Qoldiq va jurnal eski birlikda yozilgan: "100 kg" birlik "qop" ga
        almashsa, o'sha yozuvlar jimgina "100 qop" bo'lib qoladi.
        """
        changing = {
            result.data['variant'].product_id: result
            for result in results
            if not result.errors and result.data.get('variant') is not None
            and result.data['product']['base_unit']
            and result.data['product']['base_unit'] != result.data['variant'].product.base_unit
        }

        if not changing:
            return

        moved = set(
            StockMovement.objects.filter(variant__product_id__in=changing)
            .values_list('variant__product_id', flat=True)
            .distinct()
        )

        for product_id in moved:
            result = changing[product_id]
            result.errors.append(
                'Harakati bor mahsulotning asosiy birligini o‘zgartirib bo‘lmaydi '
                f'(hozir: «{result.data["variant"].product.base_unit or "—"}»)'
            )

    def commit(self, results, *, meta):
        created = updated = 0

        for result in results:
            data = result.data
            product_fields = {key: value for key, value in data['product'].items() if value}
            variant_fields = {
                key: value for key, value in data['variant_fields'].items() if value is not None
            }

            if data['variant'] is None:
                product = Product.objects.create(
                    category=data['category'],
                    is_active=data['active'] is not False,
                    **product_fields,
                )
                variant = Variant.objects.create(
                    product=product,
                    sku=data['sku'] or self._free_sku(product),
                    is_active=data['active'] is not False,
                    **variant_fields,
                )
                created += 1
            else:
                variant = Variant.objects.select_related('product').get(pk=data['variant'].pk)
                product = variant.product

                if data['category'] is not None:
                    product_fields['category'] = data['category']

                if data['active'] is not None:
                    product_fields['is_active'] = data['active']
                    variant_fields['is_active'] = data['active']

                if self._apply(product, product_fields) | self._apply(variant, variant_fields):
                    updated += 1

            normalized = Barcode.normalize(data['barcode'])

            if normalized and not Barcode.objects.filter(code_normalized=normalized).exists():
                Barcode.objects.create(
                    variant=variant, code=data['barcode'], code_type=_barcode_type(normalized)
                )

        self.audit_summary(meta, **{'yangi': created, 'yangilandi': updated})

        return {'created': created, 'updated': updated}

    @staticmethod
    def _apply(instance, fields: dict) -> bool:
        changed = [key for key, value in fields.items() if getattr(instance, key) != value]

        for key in changed:
            setattr(instance, key, fields[key])

        if changed:
            instance.save(update_fields=[*changed, 'updated_at'])

        return bool(changed)

    @staticmethod
    def _free_sku(product) -> str:
        """Artikulsiz mahsulotga kod: kategoriya prefiksi bo'lsa `CEM-0042`."""
        prefix = ''

        for category in product.category.ancestors().order_by('-path'):
            if category.code_prefix:
                prefix = category.code_prefix
                break

        base = f'{prefix}-{product.pk:04d}' if prefix else f'P{product.pk}'
        candidate, counter = base, 1

        while Variant.objects.filter(sku=candidate).exists():
            counter += 1
            candidate = f'{base}-{counter}'

        return candidate


# =====================================================================
# Kirim va sotuv hujjatlari
# =====================================================================


class DocumentImporter(BaseImporter):
    kind = ''

    def prepare(self, rows):
        visible = WarehouseAccess.visible_to(
            self.request.user, Warehouse.objects.filter(is_active=True)
        )
        self.warehouses_by_code: dict[str, Warehouse] = {}
        self.warehouses_by_name: dict[str, Warehouse] = {}

        for warehouse in visible:
            self.warehouses_by_code[warehouse.code.upper()] = warehouse
            self.warehouses_by_name.setdefault(name_key(warehouse.name), warehouse)

        tokens = {clean_text(raw.get('sku')) for _, raw in rows} - {''}

        self.by_sku: dict[str, Variant] = {}

        for variant in (
            Variant.objects.select_related('product')
            .annotate(sku_upper=Upper('sku'))
            .filter(sku_upper__in={token.upper() for token in tokens})
        ):
            self.by_sku.setdefault(variant.sku.upper(), variant)

        self.by_barcode = {
            barcode.code_normalized: barcode.variant
            for barcode in Barcode.objects.select_related('variant__product').filter(
                code_normalized__in={Barcode.normalize(token) for token in tokens}
            )
        }

        variant_ids = {v.pk for v in self.by_sku.values()} | {v.pk for v in self.by_barcode.values()}

        self.packs = {
            (pack.variant_id, name_key(pack.unit)): pack
            for pack in ProductUnit.objects.filter(variant_id__in=variant_ids)
        }

        self.partners: dict[str, Partner] = {}

        for partner in Partner.objects.order_by('-is_active', 'id'):
            self.partners.setdefault(name_key(partner.name), partner)

        self.base_units: dict[int, str] = {}
        self.announced: set[str] = set()

    def warehouse(self, result, raw):
        value = self.text(result, raw, 'warehouse', required=True)

        if not value:
            return None

        warehouse = self.warehouses_by_code.get(value.upper()) or self.warehouses_by_name.get(
            name_key(value)
        )

        if warehouse is None:
            result.errors.append(f'Ombor topilmadi yoki unga ruxsatingiz yo‘q: «{value}»')

        return warehouse

    def payment(self, result, raw) -> str:
        value = clean_text(raw.get('payment_method'))

        if not value:
            return PaymentMethod.CASH

        method = PAYMENTS.get(name_key(value))

        if method is None:
            result.errors.append(
                f'To‘lov usuli noma’lum: «{value}». Naqd, Karta, O‘tkazma yoki Aralash'
            )
            return PaymentMethod.CASH

        return method

    def announce(self, result, key: str, message: str) -> None:
        """Bir xil ogohlantirish faqat birinchi qatorda chiqsin."""
        if key not in self.announced:
            self.announced.add(key)
            result.warnings.append(message)

    def base_unit(self, variant) -> str:
        if variant.product_id not in self.base_units:
            self.base_units[variant.product_id] = variant.product.effective_unit

        return self.base_units[variant.product_id]

    def validate_row(self, result, raw):
        warehouse = self.warehouse(result, raw)
        on_date = self.date(result, raw, 'date', required=True)

        if on_date and on_date > self.today:
            result.errors.append('Sana kelajakda bo‘lmasligi kerak')

        token = self.text(result, raw, 'sku', required=True)
        variant = None

        if token:
            variant = self.by_sku.get(token.upper()) or self.by_barcode.get(Barcode.normalize(token))

            if variant is None:
                result.errors.append(f'Mahsulot topilmadi: «{token}»')
            elif not (variant.is_active and variant.product.is_active):
                result.warnings.append('Mahsulot nofaol')

        quantity = self.number(
            result, raw, 'quantity', required=True, positive=True,
            maximum=MAX_QUANTITY, places=QUANTITY_PLACES,
        )

        unit_text = self.text(result, raw, 'unit', limit=30)
        unit, factor = '', Decimal('1')

        if variant is not None and unit_text and name_key(unit_text) != name_key(self.base_unit(variant)):
            pack = self.packs.get((variant.pk, name_key(unit_text)))

            if pack is None:
                result.errors.append(
                    f'«{unit_text}» birligi {variant.product.name} uchun sozlanmagan'
                )
            else:
                unit, factor = pack.unit, pack.factor_to_base

        payment = self.payment(result, raw)
        note = str(raw.get('notes') or '').strip()

        result.data = {
            'warehouse': warehouse,
            'date': on_date,
            'variant': variant,
            'quantity': quantity,
            'quantity_base': (quantity or ZERO) * factor,
            'unit': unit,
            'unit_label': unit or (self.base_unit(variant) if variant else ''),
            'payment': payment,
            'note': note,
        }

        self.validate_details(result, raw)

        if result.errors:
            return

        result.data['group'] = self.group_key(result.data)

    def validate_details(self, result, raw) -> None:
        raise NotImplementedError

    def group_key(self, data) -> tuple:
        raise NotImplementedError

    def document_count(self, results) -> int:
        return len({result.data['group'] for result in results if 'group' in result.data})

    # -- Saqlash ------------------------------------------------------

    def commit(self, results, *, meta):
        groups: OrderedDict[tuple, list[RowResult]] = OrderedDict()

        for result in results:
            groups.setdefault(result.data['group'], []).append(result)

        self.new_partners: dict[str, Partner] = {}
        self.batches: dict[tuple, Batch] = {}
        created = []

        for rows in groups.values():
            first = rows[0].data

            document = Document.objects.create(
                kind=self.kind,
                number=documents.next_number(self.request.tenant_id, self.kind, first['date']),
                date=first['date'],
                warehouse=first['warehouse'],
                partner=self.commit_partner(first),
                payment_method=first['payment'],
                external_number=first.get('external_number', ''),
                customer_name=first.get('customer_name', ''),
                note=f'Excel importi: {meta["filename"]}',
                created_by=self.request.user,
            )

            for position, result in enumerate(rows):
                data = result.data

                try:
                    documents.build_line(
                        document,
                        variant=data['variant'],
                        quantity=data['quantity'],
                        unit_price=data['price'],
                        unit=data['unit'],
                        batch=self.commit_batch(data),
                        discount_percent=data.get('discount') or ZERO,
                        note=data['line_note'][:250],
                        position=position,
                    )
                except DjangoValidationError as exc:
                    raise CommitError([f'{result.row}-qator: {m}' for m in exc.messages]) from exc

                self.after_line(data)

            documents.recalculate_totals(document)

            if self.confirm:
                try:
                    documents.confirm(document, user=self.request.user)
                except DjangoValidationError as exc:
                    rows_text = ', '.join(str(result.row) for result in rows)
                    raise CommitError(
                        [f'{rows_text}-qatorlar: {m}' for m in exc.messages]
                    ) from exc

            record(
                Action.IMPORT,
                self.kind,
                request=self.request,
                obj=document,
                warehouse=document.warehouse,
                details=f'Excel: {meta["filename"]} — {len(rows)} qator',
                changes={'file_hash': meta['file_hash'], 'rows': len(rows)},
            )

            created.append({
                'id': document.pk,
                'number': document.number,
                'status': Document.objects.values_list('status', flat=True).get(pk=document.pk),
                'lines': len(rows),
            })

        return {'created': len(created), 'updated': 0, 'documents': created}

    def commit_partner(self, data):
        return data.get('partner')

    def commit_batch(self, data):
        return None

    def after_line(self, data) -> None:
        pass


class PurchaseImporter(DocumentImporter):
    spec = specs.PURCHASES
    kind = Document.Kind.PURCHASE
    object_type = 'purchase'

    def validate_details(self, result, raw):
        data = result.data

        data['price'] = self.number(result, raw, 'purchase_price', required=True)
        data['sale_price'] = self.number(result, raw, 'sale_price')
        data['min_stock'] = self.number(
            result, raw, 'min_stock', maximum=MAX_QUANTITY, places=QUANTITY_PLACES
        )

        name = self.text(result, raw, 'partner', limit=max_length(Partner, 'name'))
        data['partner'] = self.partners.get(name_key(name)) if name else None
        data['partner_name'] = name

        if name and data['partner'] is None:
            self.announce(
                result, f'partner:{name_key(name)}', f'Yangi yetkazib beruvchi yaratiladi: {name}'
            )

        data['external_number'] = self.text(
            result, raw, 'external_number', limit=max_length(Document, 'external_number')
        )

        data['batch'] = self.text(result, raw, 'batch', limit=max_length(Batch, 'code'))
        data['expiry_date'] = self.date(result, raw, 'expiry_date')

        if data['expiry_date'] and not data['batch']:
            result.errors.append('Yaroqlilik muddati uchun partiya kodi ham kerak')

        location = self.text(result, raw, 'location')
        data['line_note'] = '; '.join(
            part for part in (f'Joyi: {location}' if location else '', data['note']) if part
        )

    def group_key(self, data):
        return (
            data['warehouse'].pk, data['date'], name_key(data['partner_name']),
            name_key(data['external_number']), data['payment'],
        )

    def finish(self, results):
        """Shu yetkazib beruvchining shu nakladnoyi avval kiritilganmi?"""
        numbers = {
            result.data['external_number']
            for result in results
            if not result.errors and result.data.get('external_number')
        }

        if not numbers:
            return

        existing = {}

        for number, external, partner_id in (
            Document.objects.filter(kind=self.kind, external_number__in=numbers)
            .exclude(status=Document.Status.CANCELLED)
            .values_list('number', 'external_number', 'partner_id')
        ):
            existing.setdefault((name_key(external), partner_id), number)

        for result in results:
            data = result.data

            if result.errors or not data.get('external_number'):
                continue

            partner_id = data['partner'].pk if data['partner'] else None
            found = existing.get((name_key(data['external_number']), partner_id))

            if found:
                self.announce(
                    result,
                    f'invoice:{found}',
                    f'Nakladnoy {data["external_number"]} avval kiritilgan: {found}. '
                    'Tovar ikki marta kirim bo‘lmasligini tekshiring',
                )

    def commit_partner(self, data):
        if data['partner'] is not None or not data['partner_name']:
            return data['partner']

        key = name_key(data['partner_name'])

        if key not in self.new_partners:
            self.new_partners[key] = Partner.objects.create(
                name=data['partner_name'], is_supplier=True
            )

        return self.new_partners[key]

    def commit_batch(self, data):
        if not data['batch']:
            return None

        key = (data['variant'].pk, data['batch'])

        if key not in self.batches:
            self.batches[key], _ = Batch.objects.get_or_create(
                variant=data['variant'],
                code=data['batch'],
                defaults={'expiry_date': data['expiry_date']},
            )

        return self.batches[key]

    def after_line(self, data):
        """Fayldagi sotuv narxi va minimal qoldiq mahsulot kartochkasiga yoziladi."""
        variant = data['variant']
        changed = []

        for key in ('sale_price', 'min_stock'):
            if data[key] is not None and getattr(variant, key) != data[key]:
                setattr(variant, key, data[key])
                changed.append(key)

        if changed:
            variant.save(update_fields=[*changed, 'updated_at'])


class SaleImporter(DocumentImporter):
    spec = specs.SALES
    kind = Document.Kind.SALE
    object_type = 'sale'

    def validate_details(self, result, raw):
        data = result.data
        variant = data['variant']
        warehouse = data['warehouse']

        if warehouse is not None and not warehouse.is_sellable:
            result.errors.append(
                f'Bu ombordan sotib bo‘lmaydi: {warehouse.name} ({warehouse.get_purpose_display()})'
            )

        price = self.number(result, raw, 'sale_price')

        if price is None and variant is not None and not clean_text(raw.get('sale_price')):
            price = variant.sale_price

            if price is None:
                result.errors.append(
                    '«Sotuv narxi» to‘ldirilmagan va mahsulot kartochkasida ham yo‘q'
                )
            elif data['unit']:
                result.errors.append(
                    'O‘ramda sotilganda «Sotuv narxi» ustunini to‘ldiring — kartochkadagi '
                    'narx asosiy birlik uchun'
                )

        data['price'] = price
        data['discount'] = self.number(result, raw, 'discount_percent', maximum=Decimal('100'))

        if data['payment'] == PaymentMethod.DEFERRED:
            result.errors.append(
                'Qarzga sotuvni Excel orqali kiritib bo‘lmaydi — uni «Sotuv» bo‘limida '
                'mijoz ma’lumotlari bilan kiriting'
            )

        name = self.text(result, raw, 'partner', limit=max_length(Document, 'customer_name'))
        data['partner'] = self.partners.get(name_key(name)) if name else None
        data['partner_name'] = name
        data['customer_name'] = name if data['partner'] is None else ''

        if name and data['partner'] is None:
            self.announce(
                result,
                f'customer:{name_key(name)}',
                f'«{name}» kontragentlar ro‘yxatida yo‘q — mijoz ismi sifatida yoziladi',
            )

        data['line_note'] = data['note']

    def group_key(self, data):
        return (
            data['warehouse'].pk, data['date'], name_key(data['partner_name']), data['payment'],
        )

    def finish(self, results):
        """Qoldiq yetadimi — fayl tartibida, oldingi qatorlar sarfini hisobga olib.

        Tasdiqlashdagi tekshiruv bilan bir xil: `quantity` bo'yicha, band
        qilingan miqdor ayirilmaydi (`documents.services.allocate_outbound`).
        Preview'da ushlanmasa, xato commit'da butun faylni to'xtatardi va
        foydalanuvchi qaysi qator aybdor ekanini bilmasdi.
        """
        pending = [result for result in results if not result.errors]

        if not pending:
            return

        pairs = {(r.data['variant'].pk, r.data['warehouse'].pk) for r in pending}

        available = {
            (row['variant_id'], row['warehouse_id']): row['total'] or ZERO
            for row in StockBalance.objects.filter(
                variant_id__in={variant for variant, _ in pairs},
                warehouse_id__in={warehouse for _, warehouse in pairs},
            )
            .values('variant_id', 'warehouse_id')
            .annotate(total=Sum('quantity'))
        }

        for result in pending:
            data = result.data
            key = (data['variant'].pk, data['warehouse'].pk)
            have = available.get(key, ZERO)
            need = data['quantity_base']

            if need > have:
                base = self.base_unit(data['variant'])
                message = (
                    f'Omborda yetarli emas: kerak {need.normalize():f} {base}, '
                    f'mavjud {max(have, ZERO).normalize():f} {base}'
                )

                if self.confirm:
                    result.errors.append(message)
                    continue

                result.warnings.append(message + ' (qoralama sifatida saqlanadi)')

            available[key] = have - need


IMPORTERS: dict[str, type[BaseImporter]] = {
    'categories': CategoryImporter,
    'products': ProductImporter,
    'purchases': PurchaseImporter,
    'sales': SaleImporter,
}
