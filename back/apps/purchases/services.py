"""Kirim xizmatlari: tasdiqlash, bekor qilish va ta'minotchi balansi."""

from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from apps.catalog.models import Product
from apps.core import telegram
from apps.inventory.models import Location, MovementReason, VariantStock
from apps.inventory.services import create_transfer, record_movement
from apps.purchases.models import Purchase

ZERO = Decimal('0')


def recalculate_total(purchase: Purchase) -> Purchase:
    """Hujjat summasini qatorlardan qayta hisoblaydi."""
    total = sum((line.unit_cost * line.quantity for line in purchase.lines.all()), ZERO)

    purchase.total = total
    purchase.save(update_fields=['total', 'updated_at'])

    return purchase


def move_to_shop(purchase: Purchase, lines, user=None) -> None:
    """Qabul qilingan tovarning bir qismini darhol javonga chiqaradi.

    Qabul paytida xodim «shundan nechtasi zalga» sonini yozadi. Alohida
    ko'chirish hujjati yoziladi: qoldiq tarixida kirim ham, javonga
    chiqish ham alohida ko'rinib turadi.

    Zalga qabul qilingan tovarda bu son ma'nosiz — u allaqachon
    javonda.
    """
    if purchase.location.kind != Location.Kind.WAREHOUSE:
        return

    moving = [
        {'variant': line.variant, 'quantity': line.to_shop}
        for line in lines
        if line.to_shop > 0
    ]

    if not moving:
        return

    create_transfer(
        source=purchase.location,
        target=Location.shop(),
        lines=moving,
        user=user,
        date=purchase.date,
        note=f'{purchase.number} qabulidan',
    )


def apply_cells(purchase: Purchase, lines) -> None:
    """Qatorlarda yozilgan shkaf katagini qoldiqqa ko'chiradi.

    Faqat omborga qabul qilinganda: savdo zalida shkaf yo'q.
    Qatorda katak yozilmagan bo'lsa, tovarning oldingi joyi
    o'zgarmaydi — odatda u o'sha yerga qaytariladi.
    """
    if purchase.location.kind != Location.Kind.WAREHOUSE:
        return

    for line in lines:
        if not line.cell:
            continue

        stock = VariantStock.objects.filter(
            variant=line.variant, location=purchase.location
        ).first()

        if stock is not None and stock.cell != line.cell:
            stock.cell = line.cell
            stock.save(update_fields=['cell'])


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

    Tovar hujjatda ko'rsatilgan joyga tushadi — odatda omborga.
    Ombordan zalga chiqarish alohida amal (`create_transfer`).

    Shu yerda yangi sotuv narxi ham kuchga kiradi: qoralamada u faqat
    yozib qo'yilgan bo'ladi, do'konda esa eski narx ishlaydi.
    """
    if purchase.status != Purchase.Status.DRAFT:
        raise ValidationError('Faqat qoralama kirimni tasdiqlash mumkin')

    lines = list(purchase.lines.select_related('variant'))

    if not lines:
        raise ValidationError('Kirimda birorta qator yo‘q')

    for line in lines:
        record_movement(
            variant=line.variant,
            location=purchase.location,
            quantity=line.quantity,
            reason=MovementReason.PURCHASE,
            unit_cost=line.unit_cost,
            document=purchase,
            user=user,
        )

    apply_cells(purchase, lines)
    move_to_shop(purchase, lines, user)
    apply_new_sale_prices(lines)

    purchase.status = Purchase.Status.CONFIRMED
    purchase.confirmed_at = timezone.now()
    purchase.save(update_fields=['status', 'confirmed_at', 'updated_at'])

    purchase = recalculate_total(purchase)

    notify_confirmed(purchase, lines)

    return purchase


def notify_confirmed(purchase: Purchase, lines) -> None:
    """Boshliqqa qabul haqida xabar."""
    units = sum(line.quantity for line in lines)
    to_shop = sum(line.to_shop for line in lines)
    prices = sum(1 for line in lines if line.new_sale_price)

    text = [
        f'<b>Tovar qabul qilindi: {purchase.number}</b>',
        f'{units} dona — {telegram.money(purchase.total)} so‘m',
        f'Joyi: {purchase.location.name}',
    ]

    if purchase.supplier_id:
        text.append(f'Ta’minotchi: {purchase.supplier.name}')

    if to_shop:
        text.append(f'Zalga chiqarildi: {to_shop} dona')

    if prices:
        text.append(f'Yangi sotuv narxi: {prices} ta tovarda')

    text.append(f'Kim: {telegram.who(purchase.created_by)}')

    telegram.notify('\n'.join(text))


@transaction.atomic
def cancel(purchase: Purchase, user=None) -> Purchase:
    """Tasdiqlangan kirimni bekor qiladi — teskari yozuvlar bilan.

    Tovar allaqachon sotilgan bo'lsa, qoldiq yetmaydi va bekor qilish
    to'xtatiladi: aks holda qoldiq manfiyga tushardi.

    O'rtacha tannarx qayta hisoblanmaydi: chiqimda u o'zgarmaydi.
    """
    if purchase.status != Purchase.Status.CONFIRMED:
        raise ValidationError('Faqat tasdiqlangan kirimni bekor qilish mumkin')

    for line in purchase.lines.select_related('variant'):
        record_movement(
            variant=line.variant,
            location=purchase.location,
            quantity=-line.quantity,
            reason=MovementReason.PURCHASE_CANCEL,
            unit_cost=line.unit_cost,
            document=purchase,
            user=user,
        )

    purchase.status = Purchase.Status.CANCELLED
    purchase.cancelled_at = timezone.now()
    purchase.save(update_fields=['status', 'cancelled_at', 'updated_at'])

    telegram.notify(
        f'<b>Kirim bekor qilindi: {purchase.number}</b>\n'
        f'{telegram.money(purchase.total)} so‘m — tovar qoldiqdan chiqarildi\n'
        f'Kim: {telegram.who(user)}'
    )

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
