"""Hisobot hisob-kitoblari.

Barcha sanalar **mahalliy** (Asia/Tashkent). Soat 23:30 da sotilgan chek
o'sha kunning hisobotiga tushadi: `created_at` UTC da saqlanadi, shuning
uchun kun chegarasi mahalliy vaqtdan UTC ga o'giriladi.

Foyda zanjiri:
    sof tushum  = tushum − qaytarishlar
    tannarx     = sotuv tannarxi − qaytarish tannarxi
    yalpi foyda = sof tushum − tannarx
    sof foyda   = yalpi foyda − yo'qotishlar − xarajatlar

Diqqat: guruhlashda alias nomi model maydoni bilan bir xil bo'lmasligi
kerak (`quantity` → `units`), aks holda `F('quantity')` maydonga emas,
o'sha agregatning o'ziga ishora qiladi.
"""

from decimal import Decimal

from django.db.models import Count, DecimalField, F, Sum, Value
from django.db.models.functions import Coalesce
from django.utils import timezone

from apps.catalog.models import Product, Variant
from apps.core.dates import local_bounds
from apps.expenses.models import Expense
from apps.inventory.models import Location, MovementReason, StockMovement
from apps.inventory.queries import low_stock_variants
from apps.purchases.models import Purchase, Supplier
from apps.sales.models import Sale, SaleLine, SaleReturn, SaleReturnLine

ZERO = Decimal('0')
MONEY = DecimalField(max_digits=14, decimal_places=2)


def money_sum(expression):
    """Bo'sh natijada `None` emas, nol qaytadi."""
    return Coalesce(Sum(expression, output_field=MONEY), Value(ZERO), output_field=MONEY)


def unit_sum(field='quantity'):
    """Donalar yig'indisi."""
    return Coalesce(Sum(field), Value(0))


def _sales(date_from, date_to):
    start, end = local_bounds(date_from, date_to)

    return Sale.objects.filter(
        status=Sale.Status.COMPLETED, created_at__gte=start, created_at__lt=end
    )


def _returns(date_from, date_to):
    start, end = local_bounds(date_from, date_to)

    return SaleReturn.objects.filter(created_at__gte=start, created_at__lt=end)


def sales_report(date_from, date_to) -> dict:
    """Davr bo'yicha sotuv, tannarx, yo'qotish va sof foyda."""
    sales = _sales(date_from, date_to)
    returns = _returns(date_from, date_to)

    sale_totals = sales.aggregate(
        revenue=money_sum('total'),
        discounts=money_sum('discount_total'),
        cash=money_sum('cash_amount'),
        card=money_sum('card_amount'),
        receipts=Count('id'),
    )

    cost = SaleLine.objects.filter(sale__in=sales).aggregate(
        total=money_sum('line_cost')
    )['total']

    returned = returns.aggregate(total=money_sum('total'))['total']

    refund_cash = returns.filter(refund_method=SaleReturn.RefundMethod.CASH).aggregate(
        total=money_sum('total')
    )['total']
    refund_card = returns.filter(refund_method=SaleReturn.RefundMethod.CARD).aggregate(
        total=money_sum('total')
    )['total']

    returns_cost = SaleReturnLine.objects.filter(sale_return__in=returns).aggregate(
        total=money_sum(F('unit_cost') * F('quantity'))
    )['total']

    losses = loss_summary(date_from, date_to)
    expenses = expense_summary(date_from, date_to)

    revenue = sale_totals['revenue']
    net_revenue = revenue - returned
    net_cost = cost - returns_cost
    gross_profit = net_revenue - net_cost

    return {
        'date_from': date_from,
        'date_to': date_to,
        'revenue': revenue,
        'receipts': sale_totals['receipts'],
        'discounts': sale_totals['discounts'],
        'returns': returned,
        'net_revenue': net_revenue,
        'cost': net_cost,
        'gross_profit': gross_profit,
        'losses': losses['total'],
        'expenses': expenses['total'],
        'net_profit': gross_profit - losses['total'] - expenses['total'],
        'payments': {
            'cash': sale_totals['cash'] - refund_cash,
            'card': sale_totals['card'] - refund_card,
        },
        'by_category': by_category(date_from, date_to),
        'by_cashier': by_cashier(date_from, date_to),
        'loss_rows': losses['rows'],
        'expense_rows': expenses['rows'],
    }


def by_category(date_from, date_to) -> list[dict]:
    """Kategoriya kesimida sotuv va foyda."""
    rows = (
        SaleLine.objects.filter(sale__in=_sales(date_from, date_to))
        .values(name=F('variant__product__category__name'))
        .annotate(units=unit_sum(), revenue=money_sum('line_total'), cost=money_sum('line_cost'))
        .order_by('-revenue')
    )

    return [
        {
            'name': row['name'],
            'quantity': row['units'],
            'revenue': row['revenue'],
            'cost': row['cost'],
            'profit': row['revenue'] - row['cost'],
        }
        for row in rows
    ]


def by_cashier(date_from, date_to) -> list[dict]:
    """Kassir kesimida tushum."""
    rows = (
        _sales(date_from, date_to)
        .values(name=F('cashier__username'))
        .annotate(receipts=Count('id'), revenue=money_sum('total'))
        .order_by('-revenue')
    )

    return list(rows)


def top_products(date_from, date_to, limit=10) -> list[dict]:
    """Eng ko'p sotilgan mahsulotlar, o'lcham/rang kesimi bilan."""
    lines = SaleLine.objects.filter(sale__in=_sales(date_from, date_to))

    product_rows = (
        lines.values(product=F('variant__product_id'), name=F('variant__product__name'))
        .annotate(units=unit_sum(), revenue=money_sum('line_total'), cost=money_sum('line_cost'))
        .order_by('-revenue')[:limit]
    )

    products = [
        {
            'product_id': row['product'],
            'name': row['name'],
            'quantity': row['units'],
            'revenue': row['revenue'],
            'cost': row['cost'],
            'profit': row['revenue'] - row['cost'],
        }
        for row in product_rows
    ]

    product_ids = [row['product_id'] for row in products]
    breakdown: dict[int, list] = {product_id: [] for product_id in product_ids}

    variant_rows = (
        lines.filter(variant__product_id__in=product_ids)
        .values(
            product=F('variant__product_id'),
            sku=F('variant__sku'),
            size=F('variant__size__name'),
            color=F('variant__color__name'),
        )
        .annotate(units=unit_sum(), revenue=money_sum('line_total'))
        .order_by('-units')
    )

    for row in variant_rows:
        breakdown[row['product']].append({
            'sku': row['sku'],
            'size': row['size'],
            'color': row['color'],
            'quantity': row['units'],
            'revenue': row['revenue'],
        })

    return [{**row, 'variants': breakdown.get(row['product_id'], [])} for row in products]


def loss_summary(date_from, date_to) -> dict:
    """Yo'qotishlar: inventarizatsiya kamomadi va hisobdan chiqarish."""
    start, end = local_bounds(date_from, date_to)

    rows = (
        StockMovement.objects.filter(
            created_at__gte=start,
            created_at__lt=end,
            quantity__lt=0,
            reason__in=[MovementReason.WRITE_OFF, MovementReason.COUNT_ADJUSTMENT],
        )
        .values('reason')
        .annotate(
            units=unit_sum(),
            amount=money_sum(F('unit_cost') * F('quantity') * Value(-1)),
        )
        .order_by('reason')
    )

    rows = [
        {'reason': row['reason'], 'quantity': -row['units'], 'amount': row['amount']}
        for row in rows
    ]

    return {'rows': rows, 'total': sum((row['amount'] for row in rows), ZERO)}


def expense_summary(date_from, date_to) -> dict:
    """Xarajatlar turlari bo'yicha."""
    rows = list(
        Expense.objects.filter(date__gte=date_from, date__lte=date_to)
        .values('category')
        .annotate(amount=money_sum('amount'))
        .order_by('category')
    )

    return {'rows': rows, 'total': sum((row['amount'] for row in rows), ZERO)}


def stock_report(category=None, low_stock=False) -> dict:
    """Joriy qoldiq: qaysi joyda nechta, tannarx va chakana qiymati bilan."""
    queryset = Variant.objects.select_related(
        'product', 'product__category', 'size', 'color'
    ).prefetch_related('stocks__location')

    if category:
        queryset = queryset.filter(product__category_id=category)

    if low_stock:
        queryset = low_stock_variants(queryset)

    rows = []
    cost_value = ZERO
    retail_value = ZERO
    units = 0

    for variant in queryset:
        price = variant.price or ZERO
        row_cost = variant.average_cost * variant.stock_quantity
        row_retail = price * variant.stock_quantity

        cost_value += row_cost
        retail_value += row_retail
        units += variant.stock_quantity

        shop = sum(
            stock.quantity
            for stock in variant.stocks.all()
            if stock.location.kind == Location.Kind.SHOP
        )

        rows.append({
            'variant_id': variant.pk,
            'sku': variant.sku,
            'barcode': variant.barcode,
            'product': variant.product.name,
            'category': variant.product.category.name,
            'label': variant.label,
            'quantity': variant.stock_quantity,
            # Qayerda turibdi: javondagisi sotiladi, qolgani zaxira
            'shop_quantity': shop,
            'warehouse_quantity': variant.stock_quantity - shop,
            'min_stock': variant.min_stock,
            'average_cost': variant.average_cost,
            'price': price,
            'cost_value': row_cost,
            'retail_value': row_retail,
        })

    return {
        'rows': rows,
        'positions': len(rows),
        'units': units,
        'cost_value': cost_value,
        'retail_value': retail_value,
        'potential_profit': retail_value - cost_value,
    }


def supplier_balances() -> list[dict]:
    """Ta'minotchilar bo'yicha qarz."""
    rows = []

    for supplier in Supplier.objects.all():
        purchases = supplier.purchases.filter(status=Purchase.Status.CONFIRMED).aggregate(
            total=money_sum('total'), paid=money_sum('amount_paid')
        )
        payments = supplier.payments.aggregate(total=money_sum('amount'))['total']

        rows.append({
            'supplier_id': supplier.pk,
            'name': supplier.name,
            'phone': supplier.phone,
            'purchases': purchases['total'],
            'paid': purchases['paid'] + payments,
            'balance': purchases['total'] - purchases['paid'] - payments,
        })

    return rows


def dashboard() -> dict:
    """Bugun va shu oy: asosiy ko'rsatkichlar."""
    today = timezone.localdate()
    month_start = today.replace(day=1)

    def period(date_from, date_to):
        sales = _sales(date_from, date_to)
        returns = _returns(date_from, date_to)

        totals = sales.aggregate(revenue=money_sum('total'), receipts=Count('id'))
        cost = SaleLine.objects.filter(sale__in=sales).aggregate(
            total=money_sum('line_cost')
        )['total']

        returned = returns.aggregate(total=money_sum('total'))['total']
        returns_cost = SaleReturnLine.objects.filter(sale_return__in=returns).aggregate(
            total=money_sum(F('unit_cost') * F('quantity'))
        )['total']

        net_revenue = totals['revenue'] - returned
        receipts = totals['receipts']

        return {
            'revenue': net_revenue,
            'receipts': receipts,
            'average_receipt': (net_revenue / receipts) if receipts else ZERO,
            'gross_profit': net_revenue - (cost - returns_cost),
        }

    # Panelda mahsulot sanaladi: bosilganda ochiladigan ro'yxat ham
    # mahsulotlar ro'yxati (bitta ko'ylakning uch o'lchami — bitta karta)
    low_stock = (
        Product.objects.filter(
            is_active=True,
            id__in=low_stock_variants(
                Variant.objects.filter(is_active=True)
            ).values('product'),
        ).count()
    )

    return {
        'today': period(today, today),
        'month': period(month_start, today),
        'low_stock_count': low_stock,
    }
