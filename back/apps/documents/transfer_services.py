"""Ko'chirish hujjatini jo'natish va qabul qilish.

Ikki bosqich, ikki alohida amal:

- `send()` — tovar manba ombordan chiqadi va **tranzit omborga** kiradi.
  Shu paytdan boshlab u qoldiqda ko'rinadi, lekin sotuvga chiqmaydi.
- `receive()` — tovar tranzitdan chiqib maqsad omborga kiradi. Agar
  qabul qilingan miqdor jo'natilganidan kam bo'lsa, farq `TRANSIT_LOSS`
  sifatida alohida yoziladi.

Tannarx tovar bilan birga yuradi (`apps.pricing.services.move_layers`),
ya'ni ko'chirish foyda hisobotiga ta'sir qilmaydi — u xarid emas.
"""

from __future__ import annotations

from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Max
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.documents.transfer_models import Transfer, TransferLine
from apps.stock import services as stock

ZERO = Decimal('0')
DOCUMENT_TYPE = 'transfer'


@transaction.atomic
def next_number(on_date=None, tenant=None) -> str:
    """Keyingi ko'chirish raqami: `KOCH-2026-000042`.

    Prefiks tashkilot sozlamasidan olinadi; berilmasa standart `KOCH`.
    """
    from apps.core.tenancy import get_current_tenant_id
    from apps.tenants.models import Tenant

    on_date = on_date or timezone.localdate()

    if tenant is None:
        tenant = get_current_tenant_id()

    if tenant is not None and not isinstance(tenant, Tenant):
        tenant = Tenant.objects.filter(pk=tenant).first()

    prefix_value = getattr(tenant, 'transfer_prefix', '') if tenant else ''
    prefix = f'{prefix_value or Transfer.PREFIX}-{on_date.year}-'

    last = (
        Transfer.objects.filter(number__startswith=prefix)
        .aggregate(last=Max('number'))['last']
    )

    counter = int(last.rsplit('-', 1)[1]) + 1 if last else 1

    return f'{prefix}{counter:06d}'


def build_line(
    transfer: Transfer,
    *,
    variant,
    quantity,
    unit: str = '',
    batch=None,
    note: str = '',
    position: int = 0,
) -> TransferLine:
    """Ko'chirish qatorini yaratadi, o'ram koeffitsientini aniqlab."""
    from apps.catalog.models import ProductUnit

    unit = (unit or '').strip()
    base_unit = variant.product.effective_unit
    factor = Decimal('1')

    if unit and unit != base_unit:
        pack = ProductUnit.objects.filter(variant=variant, unit=unit).first()

        if pack is None:
            raise ValidationError(
                _('"%(unit)s" birligi %(name)s uchun sozlanmagan')
                % {'unit': unit, 'name': variant.product.name}
            )

        factor = pack.factor_to_base

    quantity = Decimal(quantity)

    return TransferLine.objects.create(
        tenant=transfer.tenant,
        transfer=transfer,
        variant=variant,
        batch=batch,
        unit=unit or base_unit,
        factor=factor,
        quantity_sent=quantity,
        quantity_sent_base=quantity * factor,
        note=note,
        position=position,
    )


@transaction.atomic
def send(transfer: Transfer, *, user=None) -> Transfer:
    """Birinchi bosqich: tovar tranzit omborga o'tadi.

    Shu paytdan boshlab tovar **hech kimniki emas**: manba omborda
    yo'q, maqsad omborga hali yetib bormagan. Lekin qoldiqda ko'rinadi
    va yo'qolib qolmaydi.
    """
    if transfer.status != Transfer.Status.DRAFT:
        raise ValidationError(_('Faqat qoralama ko\'chirishni jo\'natish mumkin'))

    lines = list(transfer.lines.select_related('variant', 'batch'))

    if not lines:
        raise ValidationError(_('Ko\'chirishda birorta qator yo\'q'))

    transfer.clean()

    for line in lines:
        stock.transfer_out(
            variant=line.variant,
            warehouse=transfer.from_warehouse,
            transit_warehouse=transfer.transit_warehouse,
            quantity=line.quantity_sent_base,
            batch=line.batch,
            document_type=DOCUMENT_TYPE,
            document_id=transfer.pk,
            user=user,
            note=line.note or transfer.note,
        )

    transfer.status = Transfer.Status.SENT
    transfer.sent_at = timezone.now()
    transfer.save(update_fields=['status', 'sent_at', 'updated_at'])

    return transfer


@transaction.atomic
def receive(transfer: Transfer, *, received: dict[int, Decimal] | None = None, user=None) -> Transfer:
    """Ikkinchi bosqich: qabul qilish.

    Arguments:
        received: `{qator_id: qabul_qilingan_miqdor}` — kiritilgan
            birlikda. Ko'rsatilmagan qator to'liq qabul qilingan deb
            hisoblanadi.

    Kamomad **jimgina yutilmaydi**: farq `TRANSIT_LOSS` sababi bilan
    alohida jurnal yozuvi bo'lib tushadi va hisobotda yo'qotish sifatida
    ko'rinadi.
    """
    if transfer.status != Transfer.Status.SENT:
        raise ValidationError(_('Faqat jo\'natilgan ko\'chirishni qabul qilish mumkin'))

    received = received or {}

    for line in transfer.lines.select_related('variant', 'batch'):
        entered = received.get(line.pk)

        quantity = (
            line.quantity_sent if entered is None else Decimal(entered)
        )

        if quantity < ZERO:
            raise ValidationError(_('Qabul qilingan miqdor manfiy bo\'lishi mumkin emas'))

        quantity_base = quantity * line.factor

        if quantity_base > line.quantity_sent_base:
            raise ValidationError(
                _('%(name)s: jo\'natilganidan ko\'p qabul qilib bo\'lmaydi')
                % {'name': line.variant.product.name}
            )

        if quantity_base > ZERO:
            stock.transfer_in(
                variant=line.variant,
                transit_warehouse=transfer.transit_warehouse,
                warehouse=transfer.to_warehouse,
                quantity=quantity_base,
                batch=line.batch,
                document_type=DOCUMENT_TYPE,
                document_id=transfer.pk,
                user=user,
                note=line.note or transfer.note,
            )
        else:
            # Umuman yetib kelmagan: butun miqdor yo'qotish
            _write_off_transit(transfer, line, line.quantity_sent_base, user)

        line.quantity_received = quantity
        line.quantity_received_base = quantity_base
        line.save(
            update_fields=['quantity_received', 'quantity_received_base', 'updated_at']
        )

    transfer.status = Transfer.Status.RECEIVED
    transfer.received_at = timezone.now()
    transfer.save(update_fields=['status', 'received_at', 'updated_at'])

    return transfer


def _write_off_transit(transfer: Transfer, line: TransferLine, quantity, user) -> None:
    """Tranzitda qolgan tovarni yo'qotish sifatida hisobdan chiqaradi."""
    from apps.stock.enums import MovementReason

    stock.record_movement(
        variant=line.variant,
        warehouse=transfer.transit_warehouse,
        batch=line.batch,
        quantity=-quantity,
        reason=MovementReason.TRANSIT_LOSS,
        document_type=DOCUMENT_TYPE,
        document_id=transfer.pk,
        user=user,
        note=str(_('Ko\'chirishda yetib kelmadi')),
        meta={'expected': str(line.quantity_sent_base), 'received': '0'},
    )


@transaction.atomic
def cancel(transfer: Transfer, *, user=None) -> Transfer:
    """Ko'chirishni bekor qiladi.

    Qoralama shunchaki bekor bo'ladi. Jo'natilgan ko'chirishda esa
    tovar tranzitda turibdi — u manba omborga **qaytariladi**, ya'ni
    teskari yo'nalishda yana ikki yozuv qo'shiladi.
    """
    if transfer.status in {Transfer.Status.RECEIVED, Transfer.Status.CANCELLED}:
        raise ValidationError(
            _('Qabul qilingan yoki bekor qilingan ko\'chirishni bekor qilib bo\'lmaydi')
        )

    if transfer.status == Transfer.Status.SENT:
        for line in transfer.lines.select_related('variant', 'batch'):
            stock.transfer_in(
                variant=line.variant,
                transit_warehouse=transfer.transit_warehouse,
                warehouse=transfer.from_warehouse,
                quantity=line.quantity_sent_base,
                batch=line.batch,
                document_type=DOCUMENT_TYPE,
                document_id=transfer.pk,
                user=user,
                note=str(_('Ko\'chirish bekor qilindi')),
            )

    transfer.status = Transfer.Status.CANCELLED
    transfer.cancelled_at = timezone.now()
    transfer.save(update_fields=['status', 'cancelled_at', 'updated_at'])

    return transfer
