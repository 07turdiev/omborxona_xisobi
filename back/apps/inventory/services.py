"""Ombor xizmati.

Qoldiqni o'zgartiradigan **yagona** joy — `record_movement`. U bitta
tranzaksiyada jurnalga yozuv qo'shadi va variantdagi qoldiq keshini
yangilaydi; variant qatori `select_for_update` bilan qulflanadi, ya'ni
ikki kassir oxirgi donani bir vaqtda sota olmaydi.
"""

from decimal import ROUND_HALF_UP, Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.catalog.models import Variant
from apps.inventory.models import MovementReason, StockCount, StockMovement, WriteOff

CENT = Decimal('0.01')


def round_money(value: Decimal) -> Decimal:
    return Decimal(value).quantize(CENT, rounding=ROUND_HALF_UP)


def moving_average(old_quantity: int, old_average: Decimal, in_quantity: int, in_cost: Decimal) -> Decimal:
    """Yangi o'rtacha tannarx.

    Qoldiq nol yoki manfiy bo'lsa, eski o'rtachaning ma'nosi yo'q —
    yangi kirim narxi o'rtacha bo'ladi.
    """
    if old_quantity <= 0:
        return round_money(in_cost)

    total = old_quantity * old_average + in_quantity * in_cost

    return round_money(total / (old_quantity + in_quantity))


@transaction.atomic
def record_movement(*, variant, quantity: int, reason: str, unit_cost=None, document=None, user=None) -> StockMovement:
    """Jurnalga yozuv qo'shadi va qoldiqni yangilaydi.

    Kirimda (`quantity > 0`) `unit_cost` berilsa, o'rtacha tannarx qayta
    hisoblanadi. Chiqimda o'rtacha tannarx o'zgarmaydi — jurnalga o'sha
    paytdagi tannarx nusxa sifatida yoziladi (hisobot uchun).
    """
    quantity = int(quantity)

    if quantity == 0:
        raise ValidationError('Miqdor nol bo‘lishi mumkin emas')

    locked = Variant.objects.select_for_update().get(pk=variant.pk)
    new_quantity = locked.stock_quantity + quantity

    if new_quantity < 0:
        raise ValidationError(
            f'{locked} — omborda yetarli emas: mavjud {locked.stock_quantity}, '
            f'kerak {abs(quantity)}'
        )

    updated_fields = ['stock_quantity', 'updated_at']

    if quantity > 0 and unit_cost is not None:
        locked.average_cost = moving_average(
            locked.stock_quantity, locked.average_cost, quantity, Decimal(unit_cost)
        )
        updated_fields.append('average_cost')

    movement_cost = Decimal(unit_cost) if unit_cost is not None else locked.average_cost

    locked.stock_quantity = new_quantity
    locked.save(update_fields=updated_fields)

    # Chaqiruvchidagi obyekt ham yangi qiymatlarni ko'rsin
    variant.stock_quantity = locked.stock_quantity
    variant.average_cost = locked.average_cost

    document_type = document._meta.model_name if document is not None else ''

    return StockMovement.objects.create(
        variant=locked,
        quantity=quantity,
        reason=reason,
        unit_cost=round_money(movement_cost),
        document_type=document_type,
        document_id=document.pk if document is not None else None,
        user=user,
    )


@transaction.atomic
def confirm_stock_count(stock_count: StockCount, user=None) -> StockCount:
    """Inventarizatsiyani tasdiqlaydi: farqlar jurnalga yoziladi.

    Kutilgan miqdor aynan tasdiqlash paytidagi qoldiqdan olinadi —
    sanoq davomida savdo bo'lgan bo'lsa, farq haqiqiy bo'ladi.
    """
    if stock_count.status != StockCount.Status.DRAFT:
        raise ValidationError('Faqat qoralama inventarizatsiyani tasdiqlash mumkin')

    lines = list(stock_count.lines.select_related('variant'))

    if not lines:
        raise ValidationError('Inventarizatsiyada birorta qator yo‘q')

    for line in lines:
        locked = Variant.objects.select_for_update().get(pk=line.variant_id)

        line.expected_quantity = locked.stock_quantity
        line.save(update_fields=['expected_quantity'])

        difference = line.counted_quantity - line.expected_quantity

        if difference:
            record_movement(
                variant=locked,
                quantity=difference,
                reason=MovementReason.COUNT_ADJUSTMENT,
                document=stock_count,
                user=user,
            )

    stock_count.status = StockCount.Status.CONFIRMED
    stock_count.confirmed_at = timezone.now()
    stock_count.save(update_fields=['status', 'confirmed_at', 'updated_at'])

    return stock_count


@transaction.atomic
def create_write_off(*, variant, quantity: int, reason: str, user=None) -> WriteOff:
    """Hisobdan chiqarish: tovar omborni tark etadi, qiymati yo'qotish."""
    write_off = WriteOff.objects.create(
        variant=variant, quantity=quantity, reason=reason, created_by=user
    )

    record_movement(
        variant=variant,
        quantity=-abs(int(quantity)),
        reason=MovementReason.WRITE_OFF,
        document=write_off,
        user=user,
    )

    return write_off


def stock_from_movements(variant_id: int) -> int:
    """Jurnaldan hisoblangan haqiqiy qoldiq."""
    from django.db.models import Sum

    total = StockMovement.objects.filter(variant_id=variant_id).aggregate(
        total=Sum('quantity')
    )['total']

    return total or 0
