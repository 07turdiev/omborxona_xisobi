"""Kirim va sotuv hujjatlari — ko'p qatorli.

Dizayn prototipida bitta hujjat = bitta mahsulot (`store/script.js`
dagi `imports` va `sales` massivlari). Real yetkazmada 20-30 pozitsiya
bo'ladi va ular bitta yuk xati bilan keladi, shuning uchun bizda
hujjat va qatorlar alohida.

Hujjat holati:

    qoralama  →  tasdiqlangan  →  bekor qilingan
                      ↓
              jurnalga yozuvlar tushadi

Tasdiqlangunicha hujjat qoldiqqa ta'sir qilmaydi. Tasdiqlanganda
`apps.stock.services` orqali jurnalga yozuvlar qo'shiladi. Bekor
qilinganda esa yozuvlar **o'chirilmaydi** — teskari yozuvlar qo'shiladi,
chunki jurnal append-only (3-arxitektura qarori).
"""

from __future__ import annotations

from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.core.fields import FactorField, MoneyField, QuantityField
from apps.core.models import TenantOwnedModel


class Document(TenantOwnedModel):
    """Kirim yoki sotuv hujjati."""

    class Kind(models.TextChoices):
        PURCHASE = 'purchase', _('Kirim')
        SALE = 'sale', _('Sotuv')
        RETURN_IN = 'return_in', _('Mijozdan qaytish')
        RETURN_OUT = 'return_out', _('Yetkazib beruvchiga qaytarish')

    class Status(models.TextChoices):
        DRAFT = 'draft', _('Qoralama')
        CONFIRMED = 'confirmed', _('Tasdiqlangan')
        CANCELLED = 'cancelled', _('Bekor qilingan')

    class PaymentMethod(models.TextChoices):
        CASH = 'cash', _('Naqd')
        CARD = 'card', _('Karta')
        TRANSFER = 'transfer', _('O‘tkazma')
        MIXED = 'mixed', _('Aralash')
        #: Faqat kirimda: yetkazib beruvchiga keyin to'lanadi. Sotuvda
        #: kechiktirilgan to'lov — bu qarzga sotuv (`is_credit`).
        DEFERRED = 'deferred', _('Keyinroq')

    #: Hujjat raqami prefikslari (dizayndagi `importPrefix` / `salePrefix`)
    PREFIXES = {
        Kind.PURCHASE: 'KIR',
        Kind.SALE: 'SOT',
        Kind.RETURN_IN: 'QAY',
        Kind.RETURN_OUT: 'QCH',
    }

    #: Qoldiqni oshiradigan hujjatlar
    INBOUND_KINDS = frozenset({Kind.PURCHASE, Kind.RETURN_IN})

    kind = models.CharField(_('Turi'), max_length=20, choices=Kind.choices)

    number = models.CharField(_('Raqami'), max_length=40)

    date = models.DateField(_('Sanasi'), default=timezone.localdate)

    status = models.CharField(
        _('Holati'),
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
    )

    warehouse = models.ForeignKey(
        'warehouse.Warehouse',
        on_delete=models.PROTECT,
        related_name='documents',
        verbose_name=_('Ombor'),
    )

    partner = models.ForeignKey(
        'partners.Partner',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='documents',
        verbose_name=_('Kontragent'),
    )

    currency = models.CharField(_('Valyuta'), max_length=3, default='UZS')

    #: Yetkazib beruvchi hujjatining raqami (dizayndagi `supplierInvoice`)
    external_number = models.CharField(
        _('Tashqi hujjat raqami'), max_length=60, blank=True
    )

    note = models.TextField(_('Izoh'), blank=True)

    payment_method = models.CharField(
        _('To‘lov usuli'),
        max_length=20,
        choices=PaymentMethod.choices,
        default=PaymentMethod.CASH,
    )

    # -- Qarzga sotuv ----------------------------------------------------
    #
    # Tasdiqlanganda `apps.debts.Debt` yaratiladi. Mijoz ma'lumoti hujjatda
    # turadi, chunki qoralama bosqichida qarz hali yo'q.

    is_credit = models.BooleanField(_('Qarzga'), default=False)

    #: Qarz evaziga narxga qo'shiladigan ustama. Har qator summasiga kiradi,
    #: ya'ni tushum va foydada ham ko'rinadi.
    credit_markup_percent = models.DecimalField(
        _('Kredit ustamasi, %'), max_digits=6, decimal_places=2, default=0
    )

    due_date = models.DateField(_('To‘lov muddati'), null=True, blank=True)

    #: Ro'yxatdagi kontragent bo'lmagan chakana mijoz uchun
    customer_name = models.CharField(_('Mijoz ismi'), max_length=200, blank=True)
    customer_phone = models.CharField(_('Mijoz telefoni'), max_length=30, blank=True)
    customer_document = models.CharField(_('Mijoz hujjati'), max_length=60, blank=True)

    #: Tasdiqlash paytida hisoblanadi va keyin o'zgarmaydi.
    #: Jonli hisoblash noto'g'ri bo'lardi: qator narxlari keyin
    #: o'zgarsa, tasdiqlangan hujjat summasi ham o'zgarib ketardi.
    total_amount = MoneyField(_('Summa'), default=0)

    #: Sotuvda — FIFO bo'yicha tannarx. Kirimda nol.
    total_cost = MoneyField(_('Tannarx'), default=0)

    confirmed_at = models.DateTimeField(_('Tasdiqlangan vaqt'), null=True, blank=True)
    cancelled_at = models.DateTimeField(_('Bekor qilingan vaqt'), null=True, blank=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='documents',
        verbose_name=_('Kim yaratdi'),
    )

    class Meta:
        verbose_name = _('Hujjat')
        verbose_name_plural = _('Hujjatlar')
        ordering = ['-date', '-id']
        constraints = [
            models.UniqueConstraint(
                fields=['tenant', 'number'], name='unique_tenant_document_number'
            )
        ]
        indexes = [
            models.Index(fields=['tenant', 'kind', '-date']),
            models.Index(fields=['tenant', 'status']),
        ]

    def __str__(self):
        return self.number

    @property
    def is_inbound(self) -> bool:
        return self.kind in self.INBOUND_KINDS

    @property
    def is_editable(self) -> bool:
        """Faqat qoralama tahrirlanadi.

        Tasdiqlangan hujjat qoldiqqa ta'sir qilgan — uni tahrirlash
        jurnal bilan hujjatni bir-biriga mos qoldirmasdi.
        """
        return self.status == self.Status.DRAFT

    @property
    def profit(self) -> Decimal:
        """Sotuv foydasi. Kirimda va tasdiqlanmagan hujjatda nol.

        Qoralamada tannarx hali hisoblanmagan (u tasdiqlashda FIFO
        qatlamlaridan chiqadi), shuning uchun `summa - 0` ni foyda deb
        ko'rsatish chalg'ituvchi bo'lardi — go'yo butun summa foyda.
        """
        if self.kind != self.Kind.SALE:
            return Decimal('0')

        if self.status != self.Status.CONFIRMED:
            return Decimal('0')

        return self.total_amount - self.total_cost

    def clean(self):
        super().clean()

        if self.kind == self.Kind.SALE and self.warehouse_id:
            if not self.warehouse.is_sellable:
                raise ValidationError({
                    'warehouse': _('Bu ombordan sotib bo\'lmaydi: %(name)s')
                    % {'name': self.warehouse.get_purpose_display()}
                })

        if self.is_credit:
            if self.kind != self.Kind.SALE:
                raise ValidationError({'is_credit': _('Qarzga faqat sotuv qilinadi')})

            # Qarz kimga berilgani noma'lum bo'lsa, uni undirib bo'lmaydi
            if not self.partner_id and not (
                self.customer_name.strip() and self.customer_phone.strip()
            ):
                raise ValidationError({
                    'customer_name': _(
                        'Qarzga sotuvda mijozni tanlang yoki ism va telefonini kiriting'
                    )
                })


class DocumentLine(TenantOwnedModel):
    """Hujjat qatori.

    **Miqdor ikki birlikda saqlanadi.** Foydalanuvchi "3 qop" deb
    kiritadi, qoldiq esa kilogrammda yuritiladi. Shuning uchun:

    - `unit` va `quantity` — foydalanuvchi kiritgani;
    - `factor` — o'sha paytdagi konversiya koeffitsienti;
    - `quantity_base` — bazaviy birlikdagi miqdor.

    `factor` **nusxa sifatida** saqlanadi, `ProductUnit` ga havola
    orqali emas. Sabab valyuta kursi bilan bir xil: agar keyin "1 qop =
    50 kg" o'rniga "1 qop = 40 kg" deb o'zgartirilsa, eski hujjatlar
    o'z-o'zidan qayta hisoblanib ketmasligi kerak.
    """

    document = models.ForeignKey(
        Document,
        on_delete=models.CASCADE,
        related_name='lines',
        verbose_name=_('Hujjat'),
    )

    variant = models.ForeignKey(
        'catalog.Variant',
        on_delete=models.PROTECT,
        related_name='document_lines',
        verbose_name=_('Variant'),
    )

    batch = models.ForeignKey(
        'stock.Batch',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='document_lines',
        verbose_name=_('Partiya'),
    )

    unit = models.CharField(
        _('Birlik'),
        max_length=30,
        blank=True,
        help_text=_('Bo\'sh bo\'lsa mahsulotning bazaviy birligi'),
    )

    factor = FactorField(
        _('Koeffitsient'),
        default=1,
        help_text=_('1 birlik necha bazaviy birlikka teng'),
    )

    quantity = QuantityField(_('Miqdor'), positive=True)
    quantity_base = QuantityField(_('Bazaviy miqdor'), positive=True)

    unit_price = MoneyField(_('Birlik narxi'))

    discount_percent = models.DecimalField(
        _('Chegirma, %'),
        max_digits=5,
        decimal_places=2,
        default=0,
    )

    line_total = MoneyField(_('Qator summasi'), default=0)

    #: Sotuvda FIFO bo'yicha hisoblangan tannarx (asosiy valyutada).
    #: Tasdiqlash paytida to'ldiriladi.
    line_cost = MoneyField(_('Qator tannarxi'), default=0)

    note = models.CharField(_('Izoh'), max_length=250, blank=True)

    position = models.PositiveSmallIntegerField(_('Tartib'), default=0)

    class Meta:
        verbose_name = _('Hujjat qatori')
        verbose_name_plural = _('Hujjat qatorlari')
        ordering = ['position', 'id']
        indexes = [models.Index(fields=['tenant', 'document'])]

    def __str__(self):
        return f'{self.variant} × {self.quantity} {self.unit}'

    def recalculate(self) -> None:
        """Bazaviy miqdor va qator summasini qayta hisoblaydi."""
        self.factor = self.factor or Decimal('1')
        self.quantity_base = self.quantity * self.factor

        discount = (Decimal('100') - (self.discount_percent or Decimal('0'))) / Decimal('100')

        # Qarzga sotuvda ustama narxga qo'shiladi. Chegirma bilan ko'paytma
        # tartibi ahamiyatsiz: `narx × (1 + ustama) × (1 − chegirma)`.
        markup = Decimal('0')

        if self.document.is_credit:
            markup = self.document.credit_markup_percent or Decimal('0')

        multiplier = (Decimal('100') + markup) / Decimal('100')

        self.line_total = (self.quantity * self.unit_price * multiplier * discount).quantize(
            Decimal('0.01')
        )

    @property
    def unit_price_base(self) -> Decimal:
        """Bazaviy birlik uchun narx — tannarx solishtirish uchun."""
        if not self.factor:
            return self.unit_price

        return (self.unit_price / self.factor).quantize(Decimal('0.01'))


# Ko'chirish hujjati alohida faylda — u ikki bosqichli va o'z holat
# oqimiga ega, shuning uchun kirim/sotuv mantig'i bilan aralashmasin.
from apps.documents.transfer_models import Transfer, TransferLine  # noqa: E402,F401
