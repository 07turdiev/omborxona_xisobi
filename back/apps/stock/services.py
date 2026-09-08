"""Qoldiq bilan ishlash xizmatlari.

Bu modulda InvenTree loyihasidan (MIT) olingan naqsh bor.
Manba: InvenTree 1.6.0 dev — stock/models.py:3149-3178 (`lock_quantity`)
Litsenziya va to'liq atribut: repo ildizidagi NOTICE faylida.

**Barcha qoldiq o'zgarishlari shu yerdan o'tishi kerak.** Modelni
to'g'ridan-to'g'ri chaqirish jurnal bilan keshni bir-biriga mos
qoldirmaydi.
"""

from __future__ import annotations

from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Sum
from django.utils.translation import gettext_lazy as _

from apps.catalog.models import Variant
from apps.stock.enums import MovementReason
from apps.stock.models import Batch, StockBalance, StockMovement
from apps.warehouse.models import Warehouse

ZERO = Decimal('0')


def lock_balance(
    variant: Variant,
    warehouse: Warehouse,
    batch: Batch | None = None,
    *,
    create: bool = True,
) -> StockBalance | None:
    """Qoldiq qatorini qulflaydi va uni bazadagi joriy holatda qaytaradi.

    Manba: InvenTree stock/models.py:3149-3178 (MIT, NOTICE ga qarang).

    InvenTree dagi nozik detal saqlab qolindi: qator `select_for_update()`
    bilan qulflanadi, lekin **butun obyekt qayta yuklanmaydi**. Buning
    o'rniga `refresh_from_db()` ishlatilsa, boshqa tranzaksiyada
    o'zgargan maydonlar xotiradagi qiymatlarni jimgina bosib ketardi.

    Farq: InvenTree `StockItem` qatorini qulflaydi (uning qoldig'i
    mutable ustun), bizda esa qulf **kesh jadvaliga** qo'yiladi. Jurnal
    faqat `INSERT` qabul qilgani uchun u qulflashni talab qilmaydi —
    poyga holati faqat keshni yangilashda yuzaga keladi.

    Tranzaksiya ichida chaqirilishi shart.
    """
    query = (
        StockBalance.objects.select_for_update()
        .filter(variant=variant, warehouse=warehouse, batch=batch)
    )

    balance = query.first()

    if balance is not None or not create:
        return balance

    # Qator hali yo'q. `get_or_create` poyga holatiga tushishi mumkin,
    # shuning uchun unikal cheklovga tayanamiz va qayta o'qiymiz.
    try:
        with transaction.atomic():
            balance = StockBalance.objects.create(
                tenant=variant.tenant,
                variant=variant,
                warehouse=warehouse,
                batch=batch,
            )
    except Exception:
        balance = None

    if balance is None:
        balance = query.first()

    return balance


@transaction.atomic
def record_movement(
    *,
    variant: Variant,
    warehouse: Warehouse,
    quantity: Decimal,
    reason: str,
    batch: Batch | None = None,
    unit_cost: Decimal | None = None,
    currency: str = '',
    document_type: str = '',
    document_id: int | None = None,
    note: str = '',
    meta: dict | None = None,
    user=None,
    occurred_at=None,
    allow_negative: bool = False,
) -> StockMovement:
    """Jurnalga yozuv qo'shadi va keshni **shu tranzaksiyada** yangilaydi.

    Arguments:
        quantity: ishorali miqdor — musbat kirim, manfiy chiqim.
        allow_negative: manfiy qoldiqqa ruxsat berish. Standart holda
            taqiqlangan; inventarizatsiya tuzatishlari uchun ochiladi.

    Raises:
        ValidationError: miqdor nol bo'lsa, sabab yo'nalishga mos
            kelmasa, yoki qoldiq manfiyga tushib ketsa.
    """
    quantity = Decimal(quantity)

    if quantity == ZERO:
        raise ValidationError(_('Miqdor nol bo\'lishi mumkin emas'))

    _check_direction(reason, quantity)

    if batch is not None and batch.variant_id != variant.pk:
        raise ValidationError(_('Partiya boshqa mahsulotga tegishli'))

    balance = lock_balance(variant, warehouse, batch)

    if balance is None:
        raise ValidationError(_('Qoldiq qatorini yaratib bo\'lmadi'))

    new_quantity = balance.quantity + quantity

    if new_quantity < ZERO and not allow_negative:
        raise ValidationError(
            _('Omborda yetarli tovar yo\'q: %(have)s bor, %(need)s kerak')
            % {'have': balance.quantity, 'need': -quantity}
        )

    movement = StockMovement.objects.create(
        tenant=variant.tenant,
        variant=variant,
        warehouse=warehouse,
        batch=batch,
        quantity=quantity,
        reason=reason,
        unit_cost=unit_cost,
        currency=currency or (variant.currency if unit_cost else ''),
        document_type=document_type,
        document_id=document_id,
        note=note,
        # Sonlar `str(Decimal)` sifatida — JSON float aniqlikni yo'qotadi
        meta=_stringify_decimals(meta or {}),
        created_by=user,
        **({'occurred_at': occurred_at} if occurred_at else {}),
    )

    balance.quantity = new_quantity
    balance.last_movement = movement
    balance.save(update_fields=['quantity', 'last_movement', 'updated_at'])

    _apply_costing(movement)

    return movement


def _apply_costing(movement: StockMovement) -> None:
    """Tannarx qatlamlarini yangilaydi.

    Nima uchun signal emas: FIFO yechish xato berishi mumkin va u
    **jurnal yozuvi bilan bir tranzaksiyada** bajarilishi shart.
    Signal orqali bunday bog'liqlikni boshqarish qiyin — xato jimgina
    yo'qolib ketishi mumkin.

    Import funksiya ichida: `apps.pricing` `apps.stock` modellariga
    tayanadi, ya'ni modul darajasida import qilinsa halqa hosil bo'lardi.
    """
    from apps.pricing.services import on_movement_recorded

    on_movement_recorded(movement)


def _check_direction(reason: str, quantity: Decimal) -> None:
    """Sabab miqdor ishorasiga mos kelishini tekshiradi."""
    if reason in MovementReason.bidirectional():
        return

    if reason in MovementReason.inbound() and quantity < ZERO:
        raise ValidationError(
            _('"%(reason)s" kirim sababi, miqdor musbat bo\'lishi kerak')
            % {'reason': MovementReason(reason).label}
        )

    if reason in MovementReason.outbound() and quantity > ZERO:
        raise ValidationError(
            _('"%(reason)s" chiqim sababi, miqdor manfiy bo\'lishi kerak')
            % {'reason': MovementReason(reason).label}
        )


def _stringify_decimals(data: dict) -> dict:
    """`Decimal` qiymatlarni satrga o'giradi (JSON aniqligi uchun)."""
    return {
        key: str(value) if isinstance(value, Decimal) else value
        for key, value in data.items()
    }


@transaction.atomic
def transfer_out(
    *, variant, warehouse, transit_warehouse, quantity, batch=None,
    document_type='', document_id=None, user=None, note='',
) -> tuple[StockMovement, StockMovement]:
    """Ko'chirishning birinchi bosqichi: tovar tranzit omborga o'tadi.

    Ikki yozuv qoldiradi — manba ombordan chiqim va tranzitga kirim.
    Shunday qilib tovar **qoldiqdan yo'qolmaydi**, lekin sotuvga ham
    chiqmaydi (tranzit ombor `is_sellable = False`).

    InvenTree ning `TransferOrder` i buni qilmaydi: u yerda tovar
    yakunlangunicha manba omborda turadi va bir qadamda ko'chadi
    (order/models.py:4205). "Yo'lda" holati umuman yo'q.
    """
    quantity = abs(Decimal(quantity))

    out = record_movement(
        variant=variant, warehouse=warehouse, batch=batch,
        quantity=-quantity, reason=MovementReason.TRANSFER_OUT,
        document_type=document_type, document_id=document_id,
        user=user, note=note,
        meta={'to_warehouse': transit_warehouse.pk},
    )

    into = record_movement(
        variant=variant, warehouse=transit_warehouse, batch=batch,
        quantity=quantity, reason=MovementReason.TRANSFER_IN,
        document_type=document_type, document_id=document_id,
        user=user, note=note,
        # `pair_movement` — juftlikning aniq bog'lanishi. Jurnal
        # append-only bo'lgani uchun bog'lanishni keyin qo'shib
        # bo'lmaydi; tannarxni qayta qurishda esa u zarur.
        meta={'from_warehouse': warehouse.pk, 'pair_movement': out.pk},
    )

    _move_layers(out, into)

    return out, into


def _move_layers(out_movement, in_movement) -> None:
    """Ko'chirishda tannarxni tovar bilan birga olib o'tadi."""
    from apps.pricing.services import move_layers

    move_layers(out_movement, in_movement)


@transaction.atomic
def transfer_in(
    *, variant, transit_warehouse, warehouse, quantity, batch=None,
    document_type='', document_id=None, user=None, note='',
) -> dict:
    """Ko'chirishning ikkinchi bosqichi: qabul qilish.

    `quantity` — **haqiqatan qabul qilingan** miqdor. Agar u tranzitdagi
    miqdordan kam bo'lsa, farq `TRANSIT_LOSS` sifatida alohida yoziladi.

    InvenTree bu farqni jimgina yutib yuboradi:
    `transfer_quantity = min(self.quantity, self.item.quantity)`
    (order/models.py:4235) — kamomad hech qayerda qayd etilmaydi.
    """
    received = abs(Decimal(quantity))

    balance = lock_balance(variant, transit_warehouse, batch, create=False)
    in_transit = balance.quantity if balance else ZERO

    if received > in_transit:
        raise ValidationError(
            _('Tranzitda %(have)s bor, %(need)s qabul qilib bo\'lmaydi')
            % {'have': in_transit, 'need': received}
        )

    result: dict = {}

    result['out'] = record_movement(
        variant=variant, warehouse=transit_warehouse, batch=batch,
        quantity=-received, reason=MovementReason.TRANSFER_OUT,
        document_type=document_type, document_id=document_id,
        user=user, note=note,
        meta={'to_warehouse': warehouse.pk},
    )

    result['in'] = record_movement(
        variant=variant, warehouse=warehouse, batch=batch,
        quantity=received, reason=MovementReason.TRANSFER_IN,
        document_type=document_type, document_id=document_id,
        user=user, note=note,
        meta={
            'from_warehouse': transit_warehouse.pk,
            'pair_movement': result['out'].pk,
        },
    )

    _move_layers(result['out'], result['in'])

    shortfall = in_transit - received

    if shortfall > ZERO:
        result['loss'] = record_movement(
            variant=variant, warehouse=transit_warehouse, batch=batch,
            quantity=-shortfall, reason=MovementReason.TRANSIT_LOSS,
            document_type=document_type, document_id=document_id,
            user=user,
            note=note or str(_('Ko\'chirishda kamomad')),
            meta={'expected': str(in_transit), 'received': str(received)},
        )

    return result


@transaction.atomic
def reserve(variant, warehouse, quantity, batch=None) -> StockBalance:
    """Miqdorni buyurtmaga band qiladi."""
    quantity = abs(Decimal(quantity))
    balance = lock_balance(variant, warehouse, batch, create=False)

    if balance is None or balance.available_quantity < quantity:
        available = balance.available_quantity if balance else ZERO
        raise ValidationError(
            _('Band qilish uchun yetarli tovar yo\'q: %(have)s mavjud')
            % {'have': available}
        )

    balance.reserved_quantity += quantity
    balance.save(update_fields=['reserved_quantity', 'updated_at'])

    return balance


@transaction.atomic
def release(variant, warehouse, quantity, batch=None) -> StockBalance:
    """Band qilingan miqdorni bo'shatadi."""
    quantity = abs(Decimal(quantity))
    balance = lock_balance(variant, warehouse, batch, create=False)

    if balance is None:
        raise ValidationError(_('Qoldiq topilmadi'))

    balance.reserved_quantity = max(balance.reserved_quantity - quantity, ZERO)
    balance.save(update_fields=['reserved_quantity', 'updated_at'])

    return balance


@transaction.atomic
def rebuild_balance(variant, warehouse, batch=None) -> StockBalance:
    """Keshni jurnaldan qayta hisoblaydi.

    Kesh haqiqat manbai emasligini isbotlaydigan amal: uni istalgan
    paytda tashlab, jurnaldan tiklash mumkin. Testlar shu funksiya
    natijasini kesh bilan solishtiradi.
    """
    total = (
        StockMovement.objects.filter(
            variant=variant, warehouse=warehouse, batch=batch
        ).aggregate(total=Sum('quantity'))['total']
        or ZERO
    )

    balance = lock_balance(variant, warehouse, batch)
    balance.quantity = total
    balance.save(update_fields=['quantity', 'updated_at'])

    return balance


@transaction.atomic
def stocktake(
    *, variant, warehouse, counted_quantity, batch=None, user=None, note='',
) -> StockMovement | None:
    """Inventarizatsiya: sanalgan miqdor bilan hisoblangan qoldiq farqi.

    Farq bo'lsa `STOCKTAKE_CORRECTION` sababi bilan tuzatuvchi yozuv
    qo'shiladi. Farq bo'lmasa hech narsa yozilmaydi va `None` qaytadi.

    **Nima uchun kerak.** Append-only jurnal nazariy jihatdan har doim
    to'g'ri qoldiq beradi. Amalda esa o'g'irlik, sinish, namlikdan
    buzilish va inson xatosi bo'ladi. Farqni qayd etmasak, jurnalning
    "haqiqat manbai" degan da'vosi buziladi va foydalanuvchi tizimga
    ishonishni to'xtatadi.

    Farq **yo'qotish** sifatida belgilanadi (`MovementReason.is_loss`),
    ya'ni foyda hisobotida sotuvdan alohida chiqadi.
    """
    counted = Decimal(counted_quantity)
    balance = lock_balance(variant, warehouse, batch)
    difference = counted - balance.quantity

    if difference == ZERO:
        return None

    return record_movement(
        variant=variant, warehouse=warehouse, batch=batch,
        quantity=difference,
        reason=MovementReason.STOCKTAKE_CORRECTION,
        user=user,
        note=note or str(_('Inventarizatsiya')),
        meta={'expected': str(balance.quantity), 'counted': str(counted)},
        allow_negative=True,
    )
