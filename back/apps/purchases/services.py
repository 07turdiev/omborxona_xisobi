"""Kirim xizmatlari: tasdiqlash, bekor qilish va ta'minotchi balansi."""

from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from apps.catalog.models import Product
from apps.inventory.models import Location, MovementReason
from apps.inventory.services import record_movement
from apps.purchases.models import Purchase

ZERO = Decimal('0')


def recalculate_total(purchase: Purchase) -> Purchase:
    """Hujjat summasini qatorlardan qayta hisoblaydi."""
    total = sum((line.unit_cost * line.quantity for line in purchase.lines.all()), ZERO)

    purchase.total = total
    purchase.save(update_fields=['total', 'updated_at'])

    return purchase


def apply_new_sale_prices(lines) -> int:
    """Kirimda yozilgan yangi sotuv narxlarini mahsulotlarga ko'chiradi.

    Narx modelga tegishli: bitta modelning hamma qatorida bir xil qiymat
    turadi, shuning uchun mahsulot bo'yicha guruhlanadi. Nechta mahsulot
    yangilangani qaytariladi.
    """
    prices = {
        line.variant.product_id: line.new_sale_price
        for line in lines
        if line.new_sale_price is not None
    }

    if not prices:
        return 0

    for product in Product.objects.filter(pk__in=prices):
        product.sale_price = prices[product.pk]
        product.save(update_fields=['sale_price', 'updated_at'])

    return len(prices)


@transaction.atomic
def confirm(purchase: Purchase, user=None) -> Purchase:
    """Tovarni **omborga** kiritadi va o'rtacha tannarxni qayta hisoblaydi.

    Kelgan tovar doim omborga tushadi; zalga chiqarish alohida amal
    (`create_transfer`).

    Shu yerda yangi sotuv narxi ham kuchga kiradi: qoralamada u faqat
    yozib qo'yilgan bo'ladi, do'konda esa eski narx ishlaydi.
    """
    if purchase.status != Purchase.Status.DRAFT:
        raise ValidationError('Faqat qoralama kirimni tasdiqlash mumkin')

    lines = list(purchase.lines.select_related('variant'))

    if not lines:
        raise ValidationError('Kirimda birorta qator yo‘q')

    warehouse = Location.warehouse()

    for line in lines:
        record_movement(
            variant=line.variant,
            location=warehouse,
            quantity=line.quantity,
            reason=MovementReason.PURCHASE,
            unit_cost=line.unit_cost,
            document=purchase,
            user=user,
        )

    apply_new_sale_prices(lines)

    purchase.status = Purchase.Status.CONFIRMED
    purchase.confirmed_at = timezone.now()
    purchase.save(update_fields=['status', 'confirmed_at', 'updated_at'])

    return recalculate_total(purchase)


@transaction.atomic
def cancel(purchase: Purchase, user=None) -> Purchase:
    """Tasdiqlangan kirimni bekor qiladi — teskari yozuvlar bilan.

    Tovar allaqachon sotilgan bo'lsa, qoldiq yetmaydi va bekor qilish
    to'xtatiladi: aks holda qoldiq manfiyga tushardi.

    O'rtacha tannarx qayta hisoblanmaydi: chiqimda u o'zgarmaydi.
    """
    if purchase.status != Purchase.Status.CONFIRMED:
        raise ValidationError('Faqat tasdiqlangan kirimni bekor qilish mumkin')

    warehouse = Location.warehouse()

    for line in purchase.lines.select_related('variant'):
        record_movement(
            variant=line.variant,
            location=warehouse,
            quantity=-line.quantity,
            reason=MovementReason.PURCHASE_CANCEL,
            unit_cost=line.unit_cost,
            document=purchase,
            user=user,
        )

    purchase.status = Purchase.Status.CANCELLED
    purchase.cancelled_at = timezone.now()
    purchase.save(update_fields=['status', 'cancelled_at', 'updated_at'])

    return purchase


def supplier_balance(supplier) -> Decimal:
    """Ta'minotchiga qolgan qarz.

    Tasdiqlangan kirimlar summasi − o'sha kirimlarda to'langani − alohida
    to'lovlar. Ta'minotchisiz kirimlar (do'kon ochilishidagi boshlang'ich
    qoldiq) hech kimning balansiga tushmaydi.
    """
    purchases = supplier.purchases.filter(status=Purchase.Status.CONFIRMED).aggregate(
        total=Sum('total'), paid=Sum('amount_paid')
    )
    payments = supplier.payments.aggregate(total=Sum('amount'))

    return (
        (purchases['total'] or ZERO)
        - (purchases['paid'] or ZERO)
        - (payments['total'] or ZERO)
    )
