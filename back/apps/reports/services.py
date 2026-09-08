"""Hisobot hisob-kitoblari.

Modelsiz ilova: barcha ma'lumot jurnal, hujjatlar va tannarx
qatlamlarida. Hisobot ularni **o'qiydi**, o'z jadvaliga nusxalamaydi —
aks holda ikkita haqiqat manbai paydo bo'lardi.

Ikkita tamoyil:

1. **Yo'qotish sotuvdan ajratiladi.** Buzilgan, muddati o'tgan va
   inventarizatsiyada kam chiqqan tovar foyda hisobotida savdo bilan
   aralashib ketmasligi kerak. `MovementReason.is_loss()` shu chegarani
   belgilaydi.

2. **Foyda faqat tasdiqlangan hujjatlardan.** Qoralama hujjat qoldiqqa
   ham, hisobotga ham ta'sir qilmaydi.
"""

from __future__ import annotations

from collections import defaultdict
from decimal import Decimal

from django.db.models import Count, DecimalField, F, Sum
from django.db.models.functions import Coalesce

from apps.catalog.models import Category
from apps.documents.models import Document, DocumentLine
from apps.pricing.models import CostConsumption, CostLayer
from apps.stock.enums import MovementReason
from apps.stock.models import StockBalance, StockMovement

ZERO = Decimal('0')
MONEY = DecimalField(max_digits=18, decimal_places=2)


def _money_sum(expression):
    """Nol bilan to'ldirilgan pul yig'indisi."""
    return Coalesce(Sum(expression, output_field=MONEY), ZERO, output_field=MONEY)


def _apply_period(queryset, date_from=None, date_to=None, field='date'):
    if date_from:
        queryset = queryset.filter(**{f'{field}__gte': date_from})

    if date_to:
        queryset = queryset.filter(**{f'{field}__lte': date_to})

    return queryset


def _confirmed_documents(kind, date_from=None, date_to=None, warehouse=None):
    queryset = Document.objects.filter(kind=kind, status=Document.Status.CONFIRMED)

    if warehouse:
        queryset = queryset.filter(warehouse_id=warehouse)

    return _apply_period(queryset, date_from, date_to)


# ---------------------------------------------------------------------
# Davr jamlanmasi
# ---------------------------------------------------------------------

def period_summary(date_from=None, date_to=None, warehouse=None) -> dict:
    """Davr bo'yicha asosiy ko'rsatkichlar.

    Dizayndagi hisobot sahifasining to'rtta kartasi shu yerdan
    to'ldiriladi (`reportImportTotal`, `reportRevenue`, `reportCost`,
    `reportProfit`), ustiga yo'qotishlar qo'shilgan — prototipda ular
    umuman ko'rsatilmagan.
    """
    purchases = _confirmed_documents(
        Document.Kind.PURCHASE, date_from, date_to, warehouse
    ).aggregate(count=Count('id'), amount=_money_sum('total_amount'))

    sales = _confirmed_documents(
        Document.Kind.SALE, date_from, date_to, warehouse
    ).aggregate(
        count=Count('id'),
        amount=_money_sum('total_amount'),
        cost=_money_sum('total_cost'),
    )

    revenue = sales['amount']
    cost = sales['cost']
    profit = revenue - cost
    losses = loss_summary(date_from, date_to, warehouse)

    return {
        'purchase_count': purchases['count'],
        'purchase_amount': purchases['amount'],
        'sale_count': sales['count'],
        'revenue': revenue,
        'cost': cost,
        'gross_profit': profit,
        'margin_percent': _percent(profit, revenue),
        'loss_amount': losses['total'],
        # Sof foyda: yo'qotishlar ayirilgan. Prototipda bunday
        # ko'rsatkich yo'q edi va foyda haqiqiydan katta ko'rinardi.
        'net_profit': profit - losses['total'],
    }


def _percent(part: Decimal, whole: Decimal) -> float:
    if not whole:
        return 0.0

    return round(float(part / whole * 100), 1)


# ---------------------------------------------------------------------
# Kesimlar
# ---------------------------------------------------------------------

def _root_category_map() -> dict[int, str]:
    """Har kategoriya uchun ildiz kategoriya nomi.

    Hisobotlarda "Sement va aralashmalar" emas, "Qurilish mollari"
    ko'rsatilishi kerak — aks holda diagramma o'nlab ustundan iborat
    bo'lib, o'qib bo'lmaydigan holga keladi.

    Kategoriyalar soni oz (o'nlab), shuning uchun daraxt xotiraga
    olinadi va ildiz Python da topiladi — `ltree` ning `subpath()`
    funksiyasini ORM ga tiqishtirishdan ko'ra soddaroq.
    """
    categories = {
        row['id']: row for row in Category.objects.values('id', 'name', 'path')
    }

    by_path = {row['path']: row for row in categories.values() if row['path']}
    result: dict[int, str] = {}

    for row in categories.values():
        if not row['path']:
            result[row['id']] = row['name']
            continue

        root_path = row['path'].split('.')[0]
        root = by_path.get(root_path)
        result[row['id']] = root['name'] if root else row['name']

    return result


def _sale_lines(date_from=None, date_to=None, warehouse=None):
    queryset = DocumentLine.objects.filter(
        document__kind=Document.Kind.SALE,
        document__status=Document.Status.CONFIRMED,
    ).select_related('variant__product')

    if warehouse:
        queryset = queryset.filter(document__warehouse_id=warehouse)

    return _apply_period(queryset, date_from, date_to, field='document__date')


def by_category(date_from=None, date_to=None, warehouse=None) -> list[dict]:
    """Sotuvni ildiz kategoriyalar bo'yicha guruhlaydi."""
    roots = _root_category_map()

    rows = (
        _sale_lines(date_from, date_to, warehouse)
        .values(category_id=F('variant__product__category_id'))
        .annotate(
            revenue=_money_sum('line_total'),
            cost=_money_sum('line_cost'),
            quantity=Coalesce(Sum('quantity_base'), ZERO),
        )
    )

    grouped: dict[str, dict] = defaultdict(
        lambda: {'revenue': ZERO, 'cost': ZERO, 'quantity': ZERO}
    )

    for row in rows:
        name = roots.get(row['category_id'], '—')
        bucket = grouped[name]
        bucket['revenue'] += row['revenue']
        bucket['cost'] += row['cost']
        bucket['quantity'] += row['quantity']

    result = [
        {
            'name': name,
            'revenue': values['revenue'],
            'cost': values['cost'],
            'profit': values['revenue'] - values['cost'],
            'quantity': values['quantity'],
            'margin_percent': _percent(
                values['revenue'] - values['cost'], values['revenue']
            ),
        }
        for name, values in grouped.items()
    ]

    return sorted(result, key=lambda item: item['revenue'], reverse=True)


def by_warehouse(date_from=None, date_to=None) -> list[dict]:
    """Sotuvni omborlar bo'yicha guruhlaydi."""
    rows = (
        _confirmed_documents(Document.Kind.SALE, date_from, date_to)
        .values('warehouse_id', name=F('warehouse__name'))
        .annotate(
            count=Count('id'),
            revenue=_money_sum('total_amount'),
            cost=_money_sum('total_cost'),
        )
        .order_by('-revenue')
    )

    return [
        {
            'warehouse_id': row['warehouse_id'],
            'name': row['name'],
            'count': row['count'],
            'revenue': row['revenue'],
            'cost': row['cost'],
            'profit': row['revenue'] - row['cost'],
        }
        for row in rows
    ]


def top_products(date_from=None, date_to=None, warehouse=None, limit=10) -> list[dict]:
    """Eng ko'p tushum keltirgan mahsulotlar."""
    rows = (
        _sale_lines(date_from, date_to, warehouse)
        .values('variant_id', name=F('variant__product__name'), sku=F('variant__sku'))
        .annotate(
            revenue=_money_sum('line_total'),
            cost=_money_sum('line_cost'),
            quantity=Coalesce(Sum('quantity_base'), ZERO),
        )
        .order_by('-revenue')[:limit]
    )

    return [
        {**row, 'profit': row['revenue'] - row['cost']}
        for row in rows
    ]


def daily_sales(date_from=None, date_to=None, warehouse=None) -> list[dict]:
    """Kunlik tushum — dizayndagi diagramma uchun."""
    rows = (
        _confirmed_documents(Document.Kind.SALE, date_from, date_to, warehouse)
        .values('date')
        .annotate(
            revenue=_money_sum('total_amount'),
            cost=_money_sum('total_cost'),
            count=Count('id'),
        )
        .order_by('date')
    )

    return [
        {
            'date': row['date'],
            'revenue': row['revenue'],
            'profit': row['revenue'] - row['cost'],
            'count': row['count'],
        }
        for row in rows
    ]


# ---------------------------------------------------------------------
# Yo'qotishlar
# ---------------------------------------------------------------------

def loss_summary(date_from=None, date_to=None, warehouse=None) -> dict:
    """Yo'qotishlar: buzilgan, muddati o'tgan, kamomad, sanash farqi.

    Har yo'qotish **tannarx bo'yicha** baholanadi: qaysi qatlamdan
    yechilgan bo'lsa, o'sha narx. `qoldiq × joriy narx` noto'g'ri
    javob berardi.

    Prototipda bunday hisobot umuman yo'q — yo'qotishlar hech qayerda
    ko'rinmaydi va foyda haqiqiydan katta bo'lib chiqadi.
    """
    reasons = [
        reason for reason in MovementReason.values
        if MovementReason.is_loss(reason)
    ]

    movements = StockMovement.objects.filter(reason__in=reasons, quantity__lt=0)

    if warehouse:
        movements = movements.filter(warehouse_id=warehouse)

    movements = _apply_period(movements, date_from, date_to, field='occurred_at__date')

    consumption = CostConsumption.objects.filter(movement__in=movements)

    by_reason_rows = (
        movements.values('reason')
        .annotate(quantity=Coalesce(Sum('quantity'), ZERO), count=Count('id'))
        .order_by()
    )

    costs = dict(
        consumption.values_list('movement__reason')
        .annotate(total=_money_sum(F('quantity') * F('unit_cost_base')))
        .values_list('movement__reason', 'total')
    )

    labels = dict(MovementReason.choices)

    rows = [
        {
            'reason': row['reason'],
            'label': str(labels.get(row['reason'], row['reason'])),
            'count': row['count'],
            # Miqdor manfiy yozilgan — hisobotda musbat ko'rsatamiz
            'quantity': -row['quantity'],
            'amount': costs.get(row['reason'], ZERO),
        }
        for row in by_reason_rows
    ]

    return {
        'total': sum((row['amount'] for row in rows), ZERO),
        'by_reason': sorted(rows, key=lambda item: item['amount'], reverse=True),
    }


# ---------------------------------------------------------------------
# Qoldiq qiymati
# ---------------------------------------------------------------------

def stock_valuation(warehouse=None) -> dict:
    """Ombordagi tovarning tannarxi va kutilayotgan tushumi.

    `cost_value` FIFO qatlamlaridan — turli narxdagi partiyalar
    hisobga olinadi. `retail_value` esa joriy sotuv narxidan, ya'ni
    "hammasi sotilsa qancha tushum bo'ladi".
    """
    balances = StockBalance.objects.exclude(quantity=0)
    layers = CostLayer.objects.filter(quantity_remaining__gt=0)

    if warehouse:
        balances = balances.filter(warehouse_id=warehouse)
        layers = layers.filter(warehouse_id=warehouse)

    totals = balances.aggregate(
        positions=Count('id'),
        units=Coalesce(Sum('quantity'), ZERO),
        reserved=Coalesce(Sum('reserved_quantity'), ZERO),
        retail=_money_sum(F('quantity') * F('variant__sale_price')),
    )

    cost_value = layers.aggregate(
        total=_money_sum(F('quantity_remaining') * F('unit_cost_base'))
    )['total']

    retail = totals['retail']

    return {
        'positions': totals['positions'],
        'units': totals['units'],
        'reserved': totals['reserved'],
        'cost_value': cost_value,
        'retail_value': retail,
        'potential_profit': retail - cost_value,
        'margin_percent': _percent(retail - cost_value, retail),
    }


def recent_movements(limit=10) -> list[dict]:
    """Oxirgi harakatlar — boshqaruv panelidagi ro'yxat uchun."""
    rows = (
        StockMovement.objects.select_related('variant__product', 'warehouse')
        .order_by('-occurred_at', '-id')[:limit]
    )

    return [
        {
            'id': row.id,
            'occurred_at': row.occurred_at,
            'product_name': row.variant.product.name,
            'warehouse_name': row.warehouse.name,
            'quantity': row.quantity,
            'reason': row.reason,
            'reason_display': row.get_reason_display(),
            'is_loss': MovementReason.is_loss(row.reason),
        }
        for row in rows
    ]


def low_stock(limit=10) -> list[dict]:
    """Minimal chegaradan pastga tushgan qoldiqlar."""
    rows = (
        StockBalance.objects.select_related('variant__product', 'warehouse')
        .filter(
            variant__min_stock__isnull=False,
            quantity__lte=F('variant__min_stock'),
        )
        .exclude(quantity=0)
        .order_by('quantity')[:limit]
    )

    return [
        {
            'variant_id': row.variant_id,
            'product_name': row.variant.product.name,
            'sku': row.variant.sku,
            'warehouse_name': row.warehouse.name,
            'quantity': row.quantity,
            'min_stock': row.variant.min_stock,
            'unit': row.variant.product.effective_unit,
        }
        for row in rows
    ]


def expiring_batches(days=30, limit=10) -> list[dict]:
    """Muddati yaqinlashgan partiyalar.

    Qurilish mollarida bu ixtiyoriy emas: sement 3-6 oy saqlanadi va
    muddati o'tgan tovarni sotib yuborish real risk.
    """
    from datetime import timedelta

    from django.utils import timezone

    threshold = timezone.localdate() + timedelta(days=days)

    rows = (
        StockBalance.objects.select_related('batch', 'variant__product', 'warehouse')
        .filter(
            batch__expiry_date__isnull=False,
            batch__expiry_date__lte=threshold,
            quantity__gt=0,
        )
        .order_by('batch__expiry_date')[:limit]
    )

    today = timezone.localdate()

    return [
        {
            'batch_code': row.batch.code,
            'product_name': row.variant.product.name,
            'warehouse_name': row.warehouse.name,
            'quantity': row.quantity,
            'expiry_date': row.batch.expiry_date,
            'days_left': (row.batch.expiry_date - today).days,
            'is_expired': row.batch.expiry_date < today,
        }
        for row in rows
    ]
