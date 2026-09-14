"""Hujjatlarni tasdiqlash, bekor qilish va raqamlash.

Hujjat va jurnal o'rtasidagi shartnoma:

- **Qoralama** qoldiqqa umuman ta'sir qilmaydi;
- **Tasdiqlash** har qator uchun jurnalga bitta yozuv qo'shadi;
- **Bekor qilish** yozuvlarni o'chirmaydi — teskari yozuvlar qo'shadi.

Uchinchi band 3-arxitektura qarorining bevosita oqibati: jurnal
append-only, ya'ni "bo'lmagan qilib ko'rsatish" imkoni yo'q. Bu
qulaysizlik emas, balki maqsad: bekor qilingan kirim ham tarixda
qolishi kerak, aks holda "tovar qayerdan paydo bo'ldi?" savoliga javob
yo'qoladi.
"""

from __future__ import annotations

from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.db.models import Max
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.documents.models import Document, DocumentLine
from apps.pricing import services as pricing
from apps.stock import services as stock
from apps.stock.enums import MovementReason

ZERO = Decimal('0')

#: Hujjat turiga mos harakat sababi
REASON_BY_KIND = {
    Document.Kind.PURCHASE: MovementReason.PURCHASE,
    Document.Kind.SALE: MovementReason.SALE,
    Document.Kind.RETURN_IN: MovementReason.RETURN_FROM_CUSTOMER,
    Document.Kind.RETURN_OUT: MovementReason.RETURN_TO_SUPPLIER,
}

#: Bekor qilishda ishlatiladigan teskari sabab
REVERSAL_REASON = {
    Document.Kind.PURCHASE: MovementReason.RETURN_TO_SUPPLIER,
    Document.Kind.SALE: MovementReason.RETURN_FROM_CUSTOMER,
    Document.Kind.RETURN_IN: MovementReason.SALE,
    Document.Kind.RETURN_OUT: MovementReason.PURCHASE,
}

DOCUMENT_TYPE = 'document'


@transaction.atomic
def next_number(tenant, kind: str, on_date=None) -> str:
    """Keyingi hujjat raqamini beradi: `KIR-2026-000042`.

    Raqam yil bo'yicha qayta boshlanadi. Mavjud raqamlardan eng kattasi
    olinadi — bu ketma-ketlikda bo'shliq qoldirmaydi va parallel
    so'rovlarda ham dublikat bermaydi, chunki `number` ustunida unikal
    cheklov bor va konflikt bo'lsa chaqiruvchi qayta uradi.

    Alohida hisoblagich jadvali qilinmadi: hujjatlar soni kuniga
    o'nlab, ya'ni `MAX()` so'rovi arzon va bitta jadvalni kam qiladi.
    """
    on_date = on_date or timezone.localdate()
    prefix = f'{_prefix_for(tenant, kind)}-{on_date.year}-'

    last = (
        Document.objects.filter(kind=kind, number__startswith=prefix)
        .aggregate(last=Max('number'))['last']
    )

    counter = int(last.rsplit('-', 1)[1]) + 1 if last else 1

    return f'{prefix}{counter:06d}'


def _prefix_for(tenant, kind: str) -> str:
    """Hujjat prefiksi — tashkilot sozlamasidan.

    Sozlama o'zgarsa **eski hujjatlar o'z raqamini saqlaydi**: raqam
    yaratilishda bir marta yoziladi va keyin tegilmaydi. Ya'ni prefiksni
    almashtirish tarixni buzmaydi.

    `tenant` `UUID` yoki `Tenant` bo'lishi mumkin — chaqiruvchilar
    ikkalasini ham beradi.
    """
    from apps.tenants.models import Tenant

    fields = {
        Document.Kind.PURCHASE: 'purchase_prefix',
        Document.Kind.SALE: 'sale_prefix',
    }

    field = fields.get(kind)

    if field is None:
        return Document.PREFIXES[kind]

    if not isinstance(tenant, Tenant):
        tenant = Tenant.objects.filter(pk=tenant).first()

    value = getattr(tenant, field, '') if tenant else ''

    return value or Document.PREFIXES[kind]


def recalculate_totals(document: Document) -> Document:
    """Hujjat summasini qatorlardan qayta hisoblaydi.

    Qatorlar **yangi so'rov bilan** olinadi, `document.lines.all()` orqali
    emas. Sabab: hujjat `prefetch_related` bilan yuklangan bo'lsa,
    `.all()` keshdagi eski nusxalarni qaytaradi — ular tasdiqlash paytida
    yangilangan `line_cost` ni bilmaydi va summa nol bo'lib chiqadi.
    """
    lines = list(DocumentLine.objects.filter(document=document))

    document.total_amount = sum((line.line_total for line in lines), ZERO)
    document.total_cost = sum((line.line_cost for line in lines), ZERO)
    document.save(update_fields=['total_amount', 'total_cost', 'updated_at'])

    return document


@transaction.atomic
def confirm(document: Document, *, user=None) -> Document:
    """Hujjatni tasdiqlaydi va jurnalga yozuvlar qo'shadi.

    Sotuvda har qatorning tannarxi FIFO bo'yicha hisoblanadi va
    `line_cost` ga yoziladi — shundan keyin hujjat foydasi aniq bo'ladi.

    Raises:
        ValidationError: hujjat qoralama bo'lmasa, qatorlari bo'lmasa,
            yoki omborda tovar yetmasa.
    """
    if document.status != Document.Status.DRAFT:
        raise ValidationError(_('Faqat qoralama hujjatni tasdiqlash mumkin'))

    lines = list(document.lines.select_related('variant', 'batch'))

    if not lines:
        raise ValidationError(_('Hujjatda birorta qator yo\'q'))

    document.clean()

    reason = REASON_BY_KIND[document.kind]
    occurred_at = _document_time(document)

    for line in lines:
        if document.is_inbound:
            stock.record_movement(
                variant=line.variant,
                warehouse=document.warehouse,
                batch=line.batch,
                quantity=line.quantity_base,
                reason=reason,
                # Tannarx bazaviy birlik uchun: qoldiq ham shunda yuritiladi
                unit_cost=line.unit_price_base,
                currency=document.currency,
                document_type=DOCUMENT_TYPE,
                document_id=document.pk,
                note=line.note,
                user=user,
                occurred_at=occurred_at,
            )
            continue

        # Chiqim: partiya ko'rsatilmagan bo'lsa, o'zi tanlanadi
        cost = ZERO

        for batch, quantity in allocate_outbound(document, line):
            movement = stock.record_movement(
                variant=line.variant,
                warehouse=document.warehouse,
                batch=batch,
                quantity=-quantity,
                reason=reason,
                document_type=DOCUMENT_TYPE,
                document_id=document.pk,
                note=line.note,
                user=user,
                occurred_at=occurred_at,
            )

            # FIFO qatlamlari `record_movement` ichida yechilgan;
            # endi ularning summasini qatorga yig'amiz
            cost += pricing.movement_cost(movement)

        line.line_cost = cost
        line.save(update_fields=['line_cost', 'updated_at'])

    document.status = Document.Status.CONFIRMED
    document.confirmed_at = timezone.now()
    document.save(update_fields=['status', 'confirmed_at', 'updated_at'])

    document = recalculate_totals(document)

    # Qarzga sotuv: qarz shu tranzaksiyada yaratiladi — u yaratilmasa, sotuv
    # ham tasdiqlanmaydi. Summa `recalculate_totals` dan keyingina aniq.
    from apps.debts.services import create_for_document

    create_for_document(document, user=user)

    return document


def _document_time(document: Document):
    """Hujjat sanasidagi vaqt. Bugungi hujjat uchun joriy vaqt.

    Orqaga sanali hujjat kiritilganda harakat o'sha sanaga tushishi
    kerak — aks holda FIFO tartibi va davr hisobotlari buziladi.
    """
    if document.date == timezone.localdate():
        return None

    return timezone.make_aware(
        timezone.datetime.combine(document.date, timezone.datetime.min.time())
    )


def allocate_outbound(document: Document, line) -> list[tuple]:
    """Chiqim uchun partiyalarni tanlaydi: (partiya, miqdor) ro'yxati.

    Qator partiyasi ko'rsatilgan bo'lsa — o'sha. Ko'rsatilmagan bo'lsa
    **FEFO**: muddati eng yaqin partiya birinchi sotiladi.

    Nima uchun FEFO, FIFO emas: tannarx hisobi FIFO bo'lsa ham, fizik
    sotuvda muddati yaqin tovarni birinchi chiqarish kerak, aks holda
    u omborda qolib yaroqsiz bo'ladi. Muddati yo'q partiyalar oxirida
    turadi.

    Bitta qator bir necha partiyani qamrashi mumkin — shuning uchun
    ro'yxat qaytadi va har biri uchun alohida jurnal yozuvi bo'ladi.
    """
    from apps.stock.models import StockBalance

    needed = line.quantity_base

    if line.batch_id:
        return [(line.batch, needed)]

    balances = (
        StockBalance.objects.filter(
            variant=line.variant, warehouse=document.warehouse, quantity__gt=0
        )
        .select_related('batch')
        # Muddati borlar oldinda, ular ichida eng yaqini birinchi
        .order_by(
            models.F('batch__expiry_date').asc(nulls_last=True),
            'batch_id',
        )
    )

    allocation: list[tuple] = []
    available = ZERO

    for balance in balances:
        if needed <= ZERO:
            break

        take = min(balance.quantity, needed)
        allocation.append((balance.batch, take))

        available += balance.quantity
        needed -= take

    if needed > ZERO:
        raise ValidationError(
            _('%(name)s: omborda yetarli emas. Kerak %(need)s, mavjud %(have)s')
            % {
                'name': line.variant.product.name,
                'need': line.quantity_base,
                'have': available,
            }
        )

    return allocation


@transaction.atomic
def cancel(document: Document, *, user=None, note: str = '') -> Document:
    """Tasdiqlangan hujjatni bekor qiladi — teskari yozuvlar bilan.

    Yozuvlar o'chirilmaydi. Bu ataylab: bekor qilingan kirim ham
    tarixda qolishi kerak, aks holda "tovar qayerdan paydo bo'ldi va
    qayoqqa ketdi?" savoliga javob yo'qoladi.

    Qoralama hujjat esa shunchaki qoralama bo'lib qoladi — u jurnalga
    umuman tegmagan.
    """
    if document.status == Document.Status.CANCELLED:
        raise ValidationError(_('Hujjat allaqachon bekor qilingan'))

    if document.status == Document.Status.DRAFT:
        document.status = Document.Status.CANCELLED
        document.cancelled_at = timezone.now()
        document.save(update_fields=['status', 'cancelled_at', 'updated_at'])

        return document

    # To'lov qabul qilingan qarzli sotuvni bekor qilib bo'lmaydi. Tekshiruv
    # teskari yozuvlardan oldin: aks holda yarim bekor qilingan holat qolardi.
    if document.kind == Document.Kind.SALE:
        from apps.debts.services import cancel_for_document

        cancel_for_document(document)

    reason = REVERSAL_REASON[document.kind]
    sign = Decimal('-1') if document.is_inbound else Decimal('1')

    for line in document.lines.select_related('variant', 'batch'):
        stock.record_movement(
            variant=line.variant,
            warehouse=document.warehouse,
            batch=line.batch,
            quantity=sign * line.quantity_base,
            reason=reason,
            unit_cost=line.unit_price_base if not document.is_inbound else None,
            currency=document.currency if not document.is_inbound else '',
            document_type=DOCUMENT_TYPE,
            document_id=document.pk,
            note=note or str(_('Hujjat bekor qilindi')),
            meta={'reversal_of': document.number},
            user=user,
        )

    document.status = Document.Status.CANCELLED
    document.cancelled_at = timezone.now()
    document.save(update_fields=['status', 'cancelled_at', 'updated_at'])

    return document


def build_line(
    document: Document,
    *,
    variant,
    quantity: Decimal,
    unit_price: Decimal,
    unit: str = '',
    batch=None,
    discount_percent: Decimal = ZERO,
    note: str = '',
    position: int = 0,
) -> DocumentLine:
    """Hujjat qatorini yaratadi, o'ram koeffitsientini aniqlab.

    Foydalanuvchi "3 qop" deb kiritsa, koeffitsient `ProductUnit` dan
    olinadi va qatorga **nusxa sifatida** yoziladi. Keyin koeffitsient
    o'zgarsa ham eski hujjat qayta hisoblanmaydi.
    """
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

    line = DocumentLine(
        tenant=document.tenant,
        document=document,
        variant=variant,
        batch=batch,
        unit=unit or base_unit,
        factor=factor,
        quantity=Decimal(quantity),
        unit_price=Decimal(unit_price),
        discount_percent=Decimal(discount_percent),
        note=note,
        position=position,
    )
    line.recalculate()
    line.save()

    return line
