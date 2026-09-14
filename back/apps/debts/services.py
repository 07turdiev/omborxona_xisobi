"""Qarz yaratish, to'lov qabul qilish va bekor qilish."""

from __future__ import annotations

from datetime import timedelta
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models import Max
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.debts.models import Debt, DebtPayment

ZERO = Decimal('0')
CENT = Decimal('0.01')

DEFAULT_PREFIX = 'QRZ'


def next_number(tenant, on_date=None) -> str:
    """Keyingi qarz raqami: `QRZ-2026-000042`. Hujjat raqamlash naqshi."""
    on_date = on_date or timezone.localdate()
    prefix = f'{(getattr(tenant, "debt_prefix", "") or DEFAULT_PREFIX)}-{on_date.year}-'

    last = Debt.objects.filter(number__startswith=prefix).aggregate(last=Max('number'))['last']
    counter = int(last.rsplit('-', 1)[1]) + 1 if last else 1

    return f'{prefix}{counter:06d}'


def base_amount_for(document) -> Decimal:
    """Ustamasiz summa: har qator `miqdor × narx × (1 − chegirma)`.

    Ustama summasi shu va hujjat summasi orasidagi farq. Ular alohida
    saqlanadi, chunki hisobotda "narx" va "kredit uchun ustama" alohida
    ko'rinishi kerak: ustama — qarz evaziga olinadigan haq, tovar narxi emas.
    """
    from apps.documents.models import DocumentLine

    total = ZERO

    for line in DocumentLine.objects.filter(document=document):
        discount = (Decimal('100') - (line.discount_percent or ZERO)) / Decimal('100')
        total += (line.quantity * line.unit_price * discount).quantize(CENT, ROUND_HALF_UP)

    return total


def create_for_document(document, *, user=None) -> Debt | None:
    """Tasdiqlangan qarzga sotuvdan qarz yaratadi. Oddiy sotuvda — hech narsa.

    `documents.services.confirm()` ichidan, o'sha tranzaksiyada chaqiriladi:
    qarz yaratilmasa, sotuv ham tasdiqlanmaydi.
    """
    from apps.documents.models import Document
    from apps.tenants.models import Tenant

    if document.kind != Document.Kind.SALE or not document.is_credit:
        return None

    tenant = Tenant.objects.get(pk=document.tenant_id)
    partner = document.partner

    due_date = document.due_date or (
        document.date + timedelta(days=tenant.debt_default_days)
    )

    return Debt.objects.create(
        tenant=tenant,
        number=next_number(tenant, document.date),
        document=document,
        warehouse=document.warehouse,
        partner=partner,
        customer_name=(partner.name if partner else document.customer_name)[:200],
        customer_phone=(
            (partner.phone if partner else '') or document.customer_phone
        )[:30],
        customer_document=document.customer_document,
        issued_date=document.date,
        due_date=due_date,
        base_amount=base_amount_for(document),
        markup_percent=document.credit_markup_percent or ZERO,
        amount=document.total_amount,
        currency=document.currency,
        note=document.note,
    )


def cancel_for_document(document) -> None:
    """Sotuv bekor qilinayotganda qarzni ham bekor qiladi.

    **To'lov qabul qilingan qarzni bekor qilib bo'lmaydi.** Aks holda
    mijozdan olingan pul hech qanday hujjatga bog'lanmay qolardi: kassada
    pul bor, lekin nima uchun olingani noma'lum. Avval mijoz bilan
    hisob-kitobni hal qilish kerak.
    """
    debt = Debt.objects.select_for_update().filter(document=document).first()

    if debt is None or debt.status == Debt.Status.CANCELLED:
        return

    if debt.paid_amount > ZERO:
        raise ValidationError(
            _('%(number)s qarzi bo‘yicha %(paid)s to‘lov qabul qilingan. '
              'To‘lovli qarzga bog‘langan sotuvni bekor qilib bo‘lmaydi.')
            % {'number': debt.number, 'paid': debt.paid_amount}
        )

    debt.status = Debt.Status.CANCELLED
    debt.save(update_fields=['status', 'updated_at'])


@transaction.atomic
def pay(
    debt: Debt, *, amount, method: str, note: str = '', user=None, request_key: str = ''
) -> tuple[DebtPayment, bool]:
    """Qarz bo'yicha to'lov qabul qiladi (qisman yoki to'liq).

    Qarz qatori qulflanadi (`SELECT FOR UPDATE`): ikki kassir bir vaqtda
    oxirgi qoldiqni qabul qilsa, ikkinchisi yangilangan qoldiqni ko'radi
    va ortiqcha to'lov qabul qilinmaydi.

    Returns:
        `(to'lov, yangi_yaratildimi)`. Bir xil `request_key` bilan takroriy
        so'rov avvalgi to'lovni `False` bilan qaytaradi — chaqiruvchi uni
        tarixga ikkinchi marta yozmasligi uchun.
    """
    request_key = (request_key or '').strip()[:64]

    if request_key:
        existing = DebtPayment.objects.filter(request_key=request_key).first()

        if existing is not None:
            if existing.debt_id != debt.pk:
                raise ValidationError(_('Bu so‘rov kaliti boshqa qarz uchun ishlatilgan'))

            return existing, False

    try:
        amount = Decimal(str(amount)).quantize(CENT, ROUND_HALF_UP)
    except (InvalidOperation, ValueError):
        raise ValidationError(_('Summa noto‘g‘ri'))

    debt = Debt.objects.select_for_update().get(pk=debt.pk)

    if debt.status != Debt.Status.ACTIVE:
        raise ValidationError(
            _('%(number)s qarzi faol emas: %(status)s')
            % {'number': debt.number, 'status': debt.get_status_display()}
        )

    if amount <= ZERO:
        raise ValidationError(_('To‘lov summasi noldan katta bo‘lishi kerak'))

    if amount > debt.remaining:
        raise ValidationError(
            _('To‘lov qoldiqdan katta: qoldiq %(remaining)s, kiritilgan %(amount)s')
            % {'remaining': debt.remaining, 'amount': amount}
        )

    try:
        # Savepoint: bir xil kalit bilan parallel so'rov shu orada yozib
        # ulgurgan bo'lsa, o'sha to'lov qaytariladi — ikkinchisi yozilmaydi
        with transaction.atomic():
            payment = DebtPayment.objects.create(
                tenant_id=debt.tenant_id,
                debt=debt,
                amount=amount,
                method=method,
                note=(note or '')[:250],
                request_key=request_key,
                created_by=user,
                created_by_name=((user.get_full_name() or user.username) if user else '')[:150],
            )
    except IntegrityError:
        existing = DebtPayment.objects.filter(request_key=request_key).first()

        if existing is None:
            raise

        return existing, False

    debt.paid_amount += amount

    if debt.paid_amount >= debt.amount:
        debt.status = Debt.Status.PAID
        debt.paid_at = timezone.now()

    debt.save(update_fields=['paid_amount', 'status', 'paid_at', 'updated_at'])

    return payment, True
