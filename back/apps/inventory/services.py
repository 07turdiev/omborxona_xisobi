"""Ombor xizmati.

Qoldiqni o'zgartiradigan **yagona** joy — `record_movement`. U bitta
tranzaksiyada jurnalga yozuv qo'shadi va ikkita keshni yangilaydi:
o'sha joydagi qoldiq (`VariantStock`) va variantning umumiy qoldig'i
(`Variant.stock_quantity`). Qatorlar `select_for_update` bilan
qulflanadi, ya'ni ikki kassir oxirgi donani bir vaqtda sota olmaydi.

Har harakat **qaysi joyda** bo'lganini aytadi: tovar omborga keladi,
zalga ko'chiriladi va zaldan sotiladi.
"""

from decimal import ROUND_HALF_UP, Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.catalog.models import Variant
from apps.core.numbering import next_number
from apps.inventory.models import (
    Location,
    MovementReason,
    StockCount,
    StockMovement,
    Transfer,
    TransferLine,
    VariantStock,
    WriteOff,
)

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
def record_movement(
    *, variant, location, quantity: int, reason: str, unit_cost=None, document=None, user=None
) -> StockMovement:
    """Jurnalga yozuv qo'shadi va qoldiqni yangilaydi.

    `location` — harakat qaysi joyda bo'lgani. Yetarlilik **o'sha
    joyning** qoldig'i bo'yicha tekshiriladi: omborda yigirmata bo'lsa
    ham, zalda bo'lmagan tovarni zaldan sotib bo'lmaydi.

    Kirimda (`quantity > 0`) `unit_cost` berilsa, o'rtacha tannarx qayta
    hisoblanadi (u joyga bog'liq emas — bitta tovarning tannarxi bitta).
    Chiqimda o'rtacha tannarx o'zgarmaydi — jurnalga o'sha paytdagi
    tannarx nusxa sifatida yoziladi (hisobot uchun).
    """
    quantity = int(quantity)

    if quantity == 0:
        raise ValidationError('Miqdor nol bo‘lishi mumkin emas')

    locked = Variant.objects.select_for_update().get(pk=variant.pk)

    stock, _created = VariantStock.objects.select_for_update().get_or_create(
        variant=locked, location=location
    )

    at_location = stock.quantity + quantity

    if at_location < 0:
        raise ValidationError(
            f'{locked} — «{location.name}»da yetarli emas: '
            f'mavjud {stock.quantity}, kerak {abs(quantity)}'
        )

    new_quantity = locked.stock_quantity + quantity

    updated_fields = ['stock_quantity', 'updated_at']

    if quantity > 0 and unit_cost is not None:
        locked.average_cost = moving_average(
            locked.stock_quantity, locked.average_cost, quantity, Decimal(unit_cost)
        )
        updated_fields.append('average_cost')

    movement_cost = Decimal(unit_cost) if unit_cost is not None else locked.average_cost

    locked.stock_quantity = new_quantity
    locked.save(update_fields=updated_fields)

    stock.quantity = at_location
    stock.save(update_fields=['quantity'])

    # Chaqiruvchidagi obyekt ham yangi qiymatlarni ko'rsin
    variant.stock_quantity = locked.stock_quantity
    variant.average_cost = locked.average_cost

    document_type = document._meta.model_name if document is not None else ''

    return StockMovement.objects.create(
        variant=locked,
        location=location,
        quantity=quantity,
        reason=reason,
        unit_cost=round_money(movement_cost),
        document_type=document_type,
        document_id=document.pk if document is not None else None,
        user=user,
    )


@transaction.atomic
def confirm_stock_count(stock_count: StockCount, user=None) -> StockCount:
    """Sanoqni tasdiqlaydi: farqlar jurnalga yoziladi.

    Kutilgan miqdor aynan tasdiqlash paytidagi qoldiqdan olinadi —
    sanoq davomida savdo bo'lgan bo'lsa, farq haqiqiy bo'ladi. Solish-
    tirish **sanalgan joy** bo'yicha: zal sanalsa, ombordagi tovar
    farqqa tushmaydi.
    """
    if stock_count.status != StockCount.Status.DRAFT:
        raise ValidationError('Faqat qoralama inventarizatsiyani tasdiqlash mumkin')

    lines = list(stock_count.lines.select_related('variant'))

    if not lines:
        raise ValidationError('Inventarizatsiyada birorta qator yo‘q')

    for line in lines:
        locked = Variant.objects.select_for_update().get(pk=line.variant_id)

        stock = VariantStock.objects.filter(
            variant=locked, location=stock_count.location
        ).first()

        line.expected_quantity = stock.quantity if stock else 0
        line.save(update_fields=['expected_quantity'])

        difference = line.counted_quantity - line.expected_quantity

        if difference:
            record_movement(
                variant=locked,
                location=stock_count.location,
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
def create_write_off(*, variant, quantity: int, reason: str, location=None, user=None) -> WriteOff:
    """Hisobdan chiqarish: tovar joyni tark etadi, qiymati yo'qotish."""
    location = location or Location.shop()

    write_off = WriteOff.objects.create(
        variant=variant,
        location=location,
        quantity=quantity,
        reason=reason,
        created_by=user,
    )

    record_movement(
        variant=variant,
        location=location,
        quantity=-abs(int(quantity)),
        reason=MovementReason.WRITE_OFF,
        document=write_off,
        user=user,
    )

    return write_off


@transaction.atomic
def create_transfer(*, source, target, lines, user=None, date=None, note='') -> Transfer:
    """Tovarni bir joydan ikkinchisiga ko'chiradi.

    Odatda ombordan zalga: sotiladigan tovar javonga chiqariladi.
    Tasdiqlash bosqichi yo'q — ko'chirish bir harakatda bo'ladi.

    `lines` — `{variant, quantity}` lug'atlari.
    """
    if source.pk == target.pk:
        raise ValidationError('Bir joyning o‘ziga ko‘chirib bo‘lmaydi')

    prepared = [
        (item['variant'], int(item['quantity']))
        for item in lines
        if int(item.get('quantity') or 0) > 0
    ]

    if not prepared:
        raise ValidationError('Ko‘chiriladigan tovar yo‘q')

    transfer = Transfer.objects.create(
        number=next_number('KCH', Transfer.objects, date),
        date=date or timezone.localdate(),
        source=source,
        target=target,
        note=note,
        created_by=user,
    )

    for variant, quantity in prepared:
        TransferLine.objects.create(transfer=transfer, variant=variant, quantity=quantity)

        record_movement(
            variant=variant,
            location=source,
            quantity=-quantity,
            reason=MovementReason.TRANSFER_OUT,
            document=transfer,
            user=user,
        )

        record_movement(
            variant=variant,
            location=target,
            quantity=quantity,
            reason=MovementReason.TRANSFER_IN,
            document=transfer,
            user=user,
        )

    return transfer


def stock_from_movements(variant_id: int, location_id: int | None = None) -> int:
    """Jurnaldan hisoblangan haqiqiy qoldiq.

    `location_id` berilsa — o'sha joydagi, bo'lmasa hamma joydagi.
    """
    from django.db.models import Sum

    movements = StockMovement.objects.filter(variant_id=variant_id)

    if location_id is not None:
        movements = movements.filter(location_id=location_id)

    return movements.aggregate(total=Sum('quantity'))['total'] or 0
