"""Kassa xizmatlari: sotuv, bekor qilish, qaytarish va almashtirish.

Sotuv bitta tranzaksiyada yoziladi: qator, jurnal yozuvi va qoldiq
birgalikda o'zgaradi. Har qatorga o'sha paytdagi o'rtacha tannarx nusxa
sifatida tushadi — keyin tannarx o'zgarsa ham eski chek foydasi
o'zgarmaydi.

Kassa yuboradigan `request_key` (bir martalik kalit) hujjatda saqlanadi:
tugma ikki marta bosilsa yoki tarmoq uzilib so'rov qaytarilsa, ikkinchi
so'rov yangi chek yaratmaydi (`apps.sales.api` tekshiradi).
"""

from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from apps.core.models import ShopSettings
from apps.core.numbering import next_number
from apps.inventory.models import MovementReason
from apps.inventory.services import record_movement, round_money
from apps.sales import fiscal
from apps.sales.models import Sale, SaleLine, SaleReturn, SaleReturnLine

ZERO = Decimal('0')
HUNDRED = Decimal('100')


def _discount_amount(base: Decimal, amount, percent) -> Decimal:
    """Chegirma summasi: foiz berilsa foizdan, aks holda summa."""
    if percent:
        return round_money(base * Decimal(percent) / HUNDRED)

    return round_money(Decimal(amount or 0))


def _check_discount_limit(user, subtotal: Decimal, discount_total: Decimal) -> None:
    """Kassir uchun chegirma chegarasi (administratorga cheklov yo'q)."""
    if user is None or getattr(user, 'is_admin', False) or subtotal <= ZERO:
        return

    limit = ShopSettings.load().max_discount_percent
    percent = discount_total * HUNDRED / subtotal

    if percent > limit:
        raise ValidationError(
            f'Chegirma {percent.quantize(Decimal("0.01"))} % — ruxsat etilgani {limit} %'
        )


@transaction.atomic
def create_sale(
    *,
    user,
    lines,
    discount_amount=None,
    discount_percent=None,
    cash_amount=ZERO,
    card_amount=ZERO,
    request_key=None,
) -> Sale:
    """Chekni yozadi va tovarni ombordan chiqaradi.

    `lines` — `{variant, quantity, unit_price, discount_amount, discount_percent}`
    lug'atlari. Chek darajasidagi chegirma qatorlarga summasiga
    proporsional taqsimlanadi: qaytarishda har qator o'z chegirmasi bilan
    qaytarilishi kerak.
    """
    if not lines:
        raise ValidationError('Chekda birorta qator yo‘q')

    prepared = []
    subtotal = ZERO

    for line in lines:
        variant = line['variant']
        quantity = int(line['quantity'])

        if quantity <= 0:
            raise ValidationError('Miqdor noldan katta bo‘lishi kerak')

        unit_price = Decimal(
            line.get('unit_price') if line.get('unit_price') is not None else variant.price
        )
        base = round_money(unit_price * quantity)

        discount = _discount_amount(
            base, line.get('discount_amount'), line.get('discount_percent')
        )

        if discount > base:
            raise ValidationError('Qator chegirmasi qator summasidan katta')

        prepared.append({
            'variant': variant,
            'quantity': quantity,
            'unit_price': unit_price,
            'base': base,
            'discount': discount,
        })

        subtotal += base

    line_discount_total = sum((item['discount'] for item in prepared), ZERO)
    after_line_discounts = subtotal - line_discount_total

    receipt_discount = _discount_amount(
        after_line_discounts, discount_amount, discount_percent
    )

    if receipt_discount > after_line_discounts:
        raise ValidationError('Chek chegirmasi chek summasidan katta')

    # Chek chegirmasini qatorlarga taqsimlaymiz; oxirgi qatorga qoldiq
    # tushadi, shunda yig'indi tiyinigacha to'g'ri keladi.
    distributed = ZERO

    for index, item in enumerate(prepared):
        if receipt_discount <= ZERO or after_line_discounts <= ZERO:
            break

        if index == len(prepared) - 1:
            share = receipt_discount - distributed
        else:
            weight = (item['base'] - item['discount']) / after_line_discounts
            share = round_money(receipt_discount * weight)
            distributed += share

        item['discount'] += share

    discount_total = sum((item['discount'] for item in prepared), ZERO)
    total = subtotal - discount_total

    _check_discount_limit(user, subtotal, discount_total)

    cash_amount = round_money(Decimal(cash_amount or 0))
    card_amount = round_money(Decimal(card_amount or 0))

    if cash_amount + card_amount != total:
        raise ValidationError(
            f'To‘lov summasi mos emas: {cash_amount + card_amount} ≠ {total}'
        )

    sale = Sale.objects.create(
        number=next_number('SOT', Sale.objects),
        request_key=request_key,
        cashier=user,
        subtotal=subtotal,
        discount_total=discount_total,
        total=total,
        cash_amount=cash_amount,
        card_amount=card_amount,
    )

    for item in prepared:
        movement = record_movement(
            variant=item['variant'],
            quantity=-item['quantity'],
            reason=MovementReason.SALE,
            document=sale,
            user=user,
        )

        SaleLine.objects.create(
            sale=sale,
            variant=item['variant'],
            quantity=item['quantity'],
            unit_price=item['unit_price'],
            discount_amount=item['discount'],
            line_total=item['base'] - item['discount'],
            unit_cost=movement.unit_cost,
            line_cost=round_money(movement.unit_cost * item['quantity']),
        )

    transaction.on_commit(lambda: fiscal.register_sale(sale))

    return sale


@transaction.atomic
def void_sale(sale: Sale, user=None) -> Sale:
    """Chekni bekor qiladi: tovar omborga qaytadi.

    Faqat o'sha kuni — mahalliy sana bo'yicha. Eski chek uchun qaytarish
    ishlatiladi, chunki kunlik kassa allaqachon yopilgan bo'ladi.
    """
    if sale.status != Sale.Status.COMPLETED:
        raise ValidationError('Chek allaqachon bekor qilingan')

    if sale.returns.exists():
        raise ValidationError('Qaytarish qilingan chekni bekor qilib bo‘lmaydi')

    if timezone.localdate(sale.created_at) != timezone.localdate():
        raise ValidationError('Chekni faqat sotilgan kuni bekor qilish mumkin')

    for line in sale.lines.select_related('variant'):
        record_movement(
            variant=line.variant,
            quantity=line.quantity,
            reason=MovementReason.SALE_VOID,
            unit_cost=line.unit_cost,
            document=sale,
            user=user,
        )

    sale.status = Sale.Status.VOIDED
    sale.voided_at = timezone.now()
    sale.voided_by = user
    sale.save(update_fields=['status', 'voided_at', 'voided_by', 'updated_at'])

    return sale


def returned_quantity(sale_line: SaleLine) -> int:
    """Shu qator bo'yicha allaqachon qaytarilgan miqdor."""
    total = sale_line.return_lines.aggregate(total=Sum('quantity'))['total']

    return total or 0


@transaction.atomic
def create_return(*, sale: Sale, items, refund_method, user=None, request_key=None) -> SaleReturn:
    """Qaytarish: tovar asl tannarxi bilan omborga qaytadi.

    Qaytariladigan summa qator summasidan olinadi, ya'ni chegirma
    hisobga olinadi. Qator to'liq qaytarilganda qoldiq tiyinlar ham
    qaytadi (yaxlitlash yo'qolmaydi).
    """
    if sale.status != Sale.Status.COMPLETED:
        raise ValidationError('Bekor qilingan chekdan qaytarib bo‘lmaydi')

    if not items:
        raise ValidationError('Qaytariladigan qator ko‘rsatilmagan')

    sale_return = SaleReturn.objects.create(
        number=next_number('QAY', SaleReturn.objects),
        request_key=request_key,
        sale=sale,
        refund_method=refund_method,
        created_by=user,
    )

    total = ZERO

    for item in items:
        line = item['sale_line']
        quantity = int(item['quantity'])

        if line.sale_id != sale.pk:
            raise ValidationError('Qator boshqa chekka tegishli')

        if quantity <= 0:
            raise ValidationError('Miqdor noldan katta bo‘lishi kerak')

        already = returned_quantity(line)
        remaining = line.quantity - already

        if quantity > remaining:
            raise ValidationError(
                f'{line.variant} — sotilgani {line.quantity}, qaytarilgani {already}, '
                f'qaytarish mumkin {remaining}'
            )

        if quantity == remaining:
            # Oxirgi donalar: qator summasidan qolgan hamma narsa qaytadi
            refunded = line.return_lines.aggregate(total=Sum('refund_amount'))['total'] or ZERO
            refund = line.line_total - refunded
        else:
            refund = round_money(line.line_total / line.quantity * quantity)

        SaleReturnLine.objects.create(
            sale_return=sale_return,
            sale_line=line,
            quantity=quantity,
            unit_cost=line.unit_cost,
            refund_amount=refund,
        )

        record_movement(
            variant=line.variant,
            quantity=quantity,
            reason=MovementReason.RETURN,
            unit_cost=line.unit_cost,
            document=sale_return,
            user=user,
        )

        total += refund

    sale_return.total = total
    sale_return.save(update_fields=['total', 'updated_at'])

    transaction.on_commit(lambda: fiscal.register_return(sale_return))

    return sale_return


@transaction.atomic
def exchange(
    *,
    user,
    sale: Sale,
    return_items,
    lines,
    refund_method,
    cash_amount=ZERO,
    card_amount=ZERO,
    discount_amount=None,
    discount_percent=None,
    request_key=None,
) -> dict:
    """Almashtirish: qaytarish va yangi sotuv bitta amalda.

    Buxgalteriyada ikki hujjat qoladi (qaytarish — kassadan chiqim, sotuv
    — kirim), kassirga esa bitta son ko'rsatiladi: `difference` musbat
    bo'lsa mijoz qo'shimcha to'laydi, manfiy bo'lsa qaytarib olinadi.
    """
    sale_return = create_return(
        sale=sale,
        items=return_items,
        refund_method=refund_method,
        user=user,
        request_key=request_key,
    )

    new_sale = create_sale(
        user=user,
        lines=lines,
        discount_amount=discount_amount,
        discount_percent=discount_percent,
        cash_amount=cash_amount,
        card_amount=card_amount,
        request_key=request_key,
    )

    return {
        'sale_return': sale_return,
        'sale': new_sale,
        'difference': new_sale.total - sale_return.total,
    }
