"""Valyuta konversiyasi va FIFO tannarx hisobi.

Tannarx qatlamlari — qoldiq keshi kabi, **jurnaldan hosila**. Ularni
tashlab, `rebuild_layers()` bilan qayta qurish mumkin; test aynan shuni
tekshiradi. Bu loyihaning 3-arxitektura qarorining tabiiy davomi:
haqiqat manbai bitta — `stock_movements`.

FIFO tanlangani bejiz emas: append-only jurnalda har kirim allaqachon
o'z tannarxini olib yuradi, ya'ni qatlamlar shundan to'g'ridan-to'g'ri
quriladi. O'rtacha vaznli usul esa har kirimda butun qoldiq bo'yicha
qayta hisoblashni talab qilardi.
"""

from __future__ import annotations

from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import F, Sum
from django.utils.translation import gettext_lazy as _

from apps.pricing.models import CostConsumption, CostLayer, Currency, ExchangeRate
from apps.stock.enums import MovementReason
from apps.stock.models import StockMovement

ZERO = Decimal('0')
ONE = Decimal('1')


# ---------------------------------------------------------------------
# Valyuta
# ---------------------------------------------------------------------

def base_currency_code(tenant) -> str:
    """Tashkilotning asosiy valyuta kodi."""
    code = (
        Currency.objects.filter(is_base=True)
        .values_list('code', flat=True)
        .first()
    )

    return code or tenant.base_currency


def rate_on(currency_code: str, on_date, tenant) -> Decimal:
    """Berilgan sanadagi kurs.

    Kurs `valid_from` sanasidan boshlab, keyingisi paydo bo'lgunicha
    amal qiladi. Shu sababli eski hujjatni qayta hisoblaganda o'sha
    kungi kurs olinadi va summa o'zgarmaydi.

    Asosiy valyuta uchun har doim `1`.
    """
    base = base_currency_code(tenant)

    if not currency_code or currency_code == base:
        return ONE

    rate = (
        ExchangeRate.objects.filter(
            currency__code=currency_code, valid_from__lte=on_date
        )
        .order_by('-valid_from')
        .values_list('rate', flat=True)
        .first()
    )

    if rate is None:
        raise ValidationError(
            _('%(code)s uchun %(date)s sanasiga kurs topilmadi')
            % {'code': currency_code, 'date': on_date}
        )

    return rate


def to_base(amount: Decimal, currency_code: str, on_date, tenant) -> Decimal:
    """Summani asosiy valyutaga o'giradi."""
    if amount is None:
        return None

    return Decimal(amount) * rate_on(currency_code, on_date, tenant)


# ---------------------------------------------------------------------
# FIFO qatlamlari
# ---------------------------------------------------------------------

@transaction.atomic
def create_layer(movement: StockMovement) -> CostLayer | None:
    """Kirim harakatidan tannarx qatlami yaratadi.

    Tannarxi ko'rsatilmagan kirim qatlam hosil qilmaydi (masalan
    inventarizatsiyada topilgan ortiqcha tovar) — bunday tovar sotilganda
    tannarx `None` bo'ladi va hisobotda alohida ko'rinadi.
    """
    if movement.quantity <= ZERO or movement.unit_cost is None:
        return None

    existing = CostLayer.objects.filter(movement=movement).first()

    if existing is not None:
        return existing

    tenant = movement.tenant
    on_date = movement.occurred_at.date()
    currency = movement.currency or base_currency_code(tenant)
    rate = rate_on(currency, on_date, tenant)

    return CostLayer.objects.create(
        tenant=tenant,
        variant=movement.variant,
        warehouse=movement.warehouse,
        batch=movement.batch,
        movement=movement,
        quantity_initial=movement.quantity,
        quantity_remaining=movement.quantity,
        unit_cost=movement.unit_cost,
        currency=currency,
        unit_cost_base=movement.unit_cost * rate,
        exchange_rate=rate,
        acquired_at=movement.occurred_at,
    )


@transaction.atomic
def consume_fifo(movement: StockMovement, *, strict: bool = False) -> Decimal:
    """Chiqim harakati uchun qatlamlarni eng eskisidan yechadi.

    Arguments:
        strict: qatlamlar yetmasa xato berish. Standart holda yetmagan
            qism tannarxsiz qoladi — bu real holat: boshlang'ich qoldiq
            tannarxsiz kiritilgan bo'lishi mumkin.

    Returns:
        Yechilgan umumiy tannarx (asosiy valyutada).

    Qatlamlar `select_for_update()` bilan qulflanadi — ikki kassa bir
    vaqtda bir tovarni sotganda ikkalasi ham bir qatlamni yechib
    yubormasligi uchun.
    """
    needed = abs(movement.quantity)

    if needed <= ZERO:
        return ZERO

    layers = (
        CostLayer.objects.select_for_update()
        .filter(
            variant=movement.variant,
            warehouse=movement.warehouse,
            batch=movement.batch,
            quantity_remaining__gt=0,
        )
        .order_by('acquired_at', 'id')
    )

    total = ZERO
    consumptions = []

    for layer in layers:
        if needed <= ZERO:
            break

        taken = min(layer.quantity_remaining, needed)

        consumptions.append(
            CostConsumption(
                tenant=movement.tenant,
                movement=movement,
                layer=layer,
                quantity=taken,
                unit_cost_base=layer.unit_cost_base,
            )
        )

        layer.quantity_remaining -= taken
        total += taken * layer.unit_cost_base
        needed -= taken

    if needed > ZERO and strict:
        raise ValidationError(
            _('Tannarx qatlamlari yetarli emas: %(qty)s uchun qatlam yo\'q')
            % {'qty': needed}
        )

    if consumptions:
        CostConsumption.objects.bulk_create(consumptions)
        CostLayer.objects.bulk_update(
            [c.layer for c in consumptions], ['quantity_remaining']
        )

    return total


@transaction.atomic
def move_layers(out_movement: StockMovement, in_movement: StockMovement) -> None:
    """Ko'chirishda qatlamlarni yangi omborga o'tkazadi.

    Tannarx tovar bilan birga yuradi: ombordan omborga ko'chirish
    xarid emas, shuning uchun yangi tannarx paydo bo'lmasligi kerak.
    Chiqim qatlamlari yechiladi va o'sha tannarx bilan yangi omborda
    qayta yaratiladi.
    """
    needed = abs(out_movement.quantity)

    layers = (
        CostLayer.objects.select_for_update()
        .filter(
            variant=out_movement.variant,
            warehouse=out_movement.warehouse,
            batch=out_movement.batch,
            quantity_remaining__gt=0,
        )
        .order_by('acquired_at', 'id')
    )

    for layer in layers:
        if needed <= ZERO:
            break

        taken = min(layer.quantity_remaining, needed)

        CostConsumption.objects.create(
            tenant=out_movement.tenant,
            movement=out_movement,
            layer=layer,
            quantity=taken,
            unit_cost_base=layer.unit_cost_base,
        )

        layer.quantity_remaining -= taken
        layer.save(update_fields=['quantity_remaining'])

        # Yangi omborda o'sha tannarx bilan qatlam. `acquired_at` eski
        # qatlamdan olinadi — FIFO tartibi ko'chirishdan keyin ham
        # to'g'ri qolishi uchun.
        CostLayer.objects.create(
            tenant=in_movement.tenant,
            variant=in_movement.variant,
            warehouse=in_movement.warehouse,
            batch=in_movement.batch,
            movement=in_movement,
            quantity_initial=taken,
            quantity_remaining=taken,
            unit_cost=layer.unit_cost,
            currency=layer.currency,
            unit_cost_base=layer.unit_cost_base,
            exchange_rate=layer.exchange_rate,
            acquired_at=layer.acquired_at,
        )

        needed -= taken


def movement_cost(movement: StockMovement) -> Decimal:
    """Chiqim harakatining umumiy tannarxi (asosiy valyutada)."""
    total = movement.cost_consumptions.aggregate(
        total=Sum(F('quantity') * F('unit_cost_base'))
    )['total']

    return total or ZERO


def stock_value(variant=None, warehouse=None) -> Decimal:
    """Qolgan qatlamlarning umumiy qiymati — real tannarx bo'yicha.

    Bu `qoldiq × joriy kirim narxi` dan farq qiladi: turli narxda
    kelgan partiyalar bo'lsa, haqiqiy qiymat aniqroq chiqadi.
    """
    query = CostLayer.objects.filter(quantity_remaining__gt=0)

    if variant is not None:
        query = query.filter(variant=variant)

    if warehouse is not None:
        query = query.filter(warehouse=warehouse)

    total = query.aggregate(
        total=Sum(F('quantity_remaining') * F('unit_cost_base'))
    )['total']

    return total or ZERO


@transaction.atomic
def rebuild_layers(variant) -> int:
    """Variantning tannarx qatlamlarini butun jurnaldan qayta quradi.

    **Nima uchun ombor kesimida emas, variant kesimida.** Ko'chirish
    ikki omborni bog'laydi: manba ombordan qatlam yechiladi va maqsad
    omborda o'sha tannarx bilan qayta yaratiladi. Faqat bitta omborni
    qayta qurganda bu bog'lanish uzilib qoladi va ko'chirilgan tovar
    tannarxsiz qolardi.

    Shuning uchun qayta qurish variantning **barcha omborlaridagi**
    harakatlarini vaqt tartibida qayta o'ynatadi.

    Returns:
        Yaratilgan qatlamlar soni.
    """
    movements = list(
        StockMovement.objects.filter(variant=variant).order_by('occurred_at', 'id')
    )

    CostConsumption.objects.filter(layer__variant=variant).delete()
    CostLayer.objects.filter(variant=variant).delete()

    created = 0

    for movement in movements:
        if movement.reason == MovementReason.TRANSFER_OUT:
            # Qatlamlar yechiladi, lekin tannarx yo'qolmaydi — u juftlik
            # `TRANSFER_IN` yozuvida qayta paydo bo'ladi.
            consume_fifo(movement)
            continue

        if movement.reason == MovementReason.TRANSFER_IN:
            paired = _paired_out_movement(movement)

            if paired is not None:
                created += _recreate_from_consumptions(paired, movement)

            continue

        if movement.quantity > ZERO:
            if create_layer(movement) is not None:
                created += 1
        else:
            consume_fifo(movement)

    return created


def _paired_out_movement(in_movement: StockMovement) -> StockMovement | None:
    """`TRANSFER_IN` ga juft bo'lgan `TRANSFER_OUT` yozuvini topadi.

    Juftlik `meta['pair_movement']` orqali aniq bog'langan. Jurnal
    append-only bo'lgani uchun bog'lanishni keyin qo'shib bo'lmaydi —
    shuning uchun `record_movement` chaqirilishida chiqim yozuvining ID
    si kirim yozuvining `meta` siga solinadi.
    """
    pair_id = (in_movement.meta or {}).get('pair_movement')

    if not pair_id:
        return None

    return StockMovement.objects.filter(pk=pair_id).first()


def _recreate_from_consumptions(
    out_movement: StockMovement, in_movement: StockMovement
) -> int:
    """Chiqimda yechilgan qatlamlarni maqsad omborda qayta yaratadi."""
    created = 0

    for consumption in out_movement.cost_consumptions.select_related('layer'):
        source = consumption.layer

        CostLayer.objects.create(
            tenant=in_movement.tenant,
            variant=in_movement.variant,
            warehouse=in_movement.warehouse,
            batch=in_movement.batch,
            movement=in_movement,
            quantity_initial=consumption.quantity,
            quantity_remaining=consumption.quantity,
            unit_cost=source.unit_cost,
            currency=source.currency,
            unit_cost_base=consumption.unit_cost_base,
            exchange_rate=source.exchange_rate,
            # Qatlam o'z yoshini saqlaydi — FIFO tartibi ko'chirishdan
            # keyin ham to'g'ri qolishi uchun
            acquired_at=source.acquired_at,
        )
        created += 1

    return created


# ---------------------------------------------------------------------
# Jurnal bilan bog'lanish
# ---------------------------------------------------------------------

def on_movement_recorded(movement: StockMovement) -> None:
    """`apps.stock.services.record_movement` shu funksiyani chaqiradi.

    Nima uchun signal emas: FIFO yechish xato berishi mumkin
    (`strict=True` holatida) va u **jurnal yozuvi bilan bir
    tranzaksiyada** bajarilishi shart. Signal orqali bunday
    bog'liqlikni boshqarish qiyin va xato yo'qolib ketishi mumkin.

    Ko'chirish yozuvlari bu yerda e'tiborsiz qoldiriladi — ular
    juftlik bo'lgani uchun `move_layers()` orqali alohida ishlanadi.
    """
    if movement.reason in {MovementReason.TRANSFER_IN, MovementReason.TRANSFER_OUT}:
        return

    if movement.quantity > ZERO:
        create_layer(movement)
    else:
        consume_fifo(movement)
