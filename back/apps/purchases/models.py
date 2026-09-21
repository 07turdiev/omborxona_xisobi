"""Ta'minotchilar va kirim hujjatlari."""

from decimal import Decimal

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.fields import MoneyField
from apps.core.models import TimeStampedModel


class Supplier(TimeStampedModel):
    """Ta'minotchi."""

    name = models.CharField(_('Nomi'), max_length=150)
    phone = models.CharField(_('Telefon'), max_length=30, blank=True)
    note = models.CharField(_('Izoh'), max_length=300, blank=True)

    is_active = models.BooleanField(_('Faol'), default=True)

    class Meta:
        verbose_name = _('Ta’minotchi')
        verbose_name_plural = _('Ta’minotchilar')
        ordering = ['name']

    def __str__(self):
        return self.name


class SupplierPayment(TimeStampedModel):
    """Ta'minotchiga to'lov."""

    supplier = models.ForeignKey(
        Supplier,
        on_delete=models.PROTECT,
        related_name='payments',
        verbose_name=_('Ta’minotchi'),
    )

    date = models.DateField(_('Sanasi'))
    amount = MoneyField(_('Summa'))
    note = models.CharField(_('Izoh'), max_length=300, blank=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='supplier_payments',
        verbose_name=_('Kim kiritdi'),
    )

    class Meta:
        verbose_name = _('Ta’minotchiga to‘lov')
        verbose_name_plural = _('Ta’minotchiga to‘lovlar')
        ordering = ['-date', '-id']

    def __str__(self):
        return f'{self.supplier_id}: {self.amount}'


class Purchase(TimeStampedModel):
    """Kirim hujjati: tovar qabul qilish."""

    class Status(models.TextChoices):
        DRAFT = 'draft', _('Qoralama')
        CONFIRMED = 'confirmed', _('Tasdiqlangan')
        CANCELLED = 'cancelled', _('Bekor qilingan')

    number = models.CharField(_('Raqami'), max_length=20, unique=True)
    date = models.DateField(_('Sanasi'))

    #: Bo'sh bo'lishi mumkin: do'kon tizimga o'tganda javondagi tovar
    #: boshlang'ich qoldiq sifatida kiritiladi va hech kimning balansiga
    #: tushmaydi.
    supplier = models.ForeignKey(
        Supplier,
        on_delete=models.PROTECT,
        related_name='purchases',
        null=True,
        blank=True,
        verbose_name=_('Ta’minotchi'),
    )

    status = models.CharField(
        _('Holati'), max_length=10, choices=Status.choices, default=Status.DRAFT
    )

    note = models.CharField(_('Izoh'), max_length=300, blank=True)

    #: Qatorlardan hisoblanadi
    total = MoneyField(_('Summa'), default=0)
    amount_paid = MoneyField(_('To‘langan'), default=0)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='purchases',
        verbose_name=_('Kim kiritdi'),
    )

    confirmed_at = models.DateTimeField(_('Tasdiqlangan vaqt'), null=True, blank=True)
    cancelled_at = models.DateTimeField(_('Bekor qilingan vaqt'), null=True, blank=True)

    class Meta:
        verbose_name = _('Kirim')
        verbose_name_plural = _('Kirimlar')
        ordering = ['-date', '-id']
        indexes = [models.Index(fields=['status', '-date'])]

    def __str__(self):
        return self.number

    @property
    def is_editable(self) -> bool:
        """Faqat qoralama tahrirlanadi: tasdiqlangan hujjat qoldiqqa ta'sir qilgan."""
        return self.status == self.Status.DRAFT

    @property
    def debt(self) -> Decimal:
        """Shu hujjat bo'yicha qolgan qarz.

        Ta'minotchisiz kirim (do'kon ochilishidagi boshlang'ich qoldiq)
        va bekor qilingan kirim hech kimning balansiga tushmaydi —
        ularda qarz ham bo'lmaydi. Ta'minotchilar hisoboti allaqachon
        shunday hisoblaydi (`reports.services.supplier_balances`).
        """
        if self.supplier_id is None or self.status == self.Status.CANCELLED:
            return Decimal('0')

        return self.total - self.amount_paid


class PurchaseLine(models.Model):
    """Kirim qatori."""

    purchase = models.ForeignKey(
        Purchase,
        on_delete=models.CASCADE,
        related_name='lines',
        verbose_name=_('Kirim'),
    )

    variant = models.ForeignKey(
        'catalog.Variant',
        on_delete=models.PROTECT,
        related_name='purchase_lines',
        verbose_name=_('Variant'),
    )

    quantity = models.PositiveIntegerField(_('Miqdor'))
    unit_cost = MoneyField(_('Birlik tannarxi'))

    #: Kirimda ustama foizidan taklif qilingan (yoki qo'lda yozilgan) yangi
    #: sotuv narxi. Mahsulotga faqat kirim **tasdiqlanganda** ko'chiriladi:
    #: qoralama hali kelmagan tovar, uning narxi do'konda ko'rinmasligi kerak.
    new_sale_price = MoneyField(_('Yangi sotuv narxi'), null=True, blank=True)

    class Meta:
        verbose_name = _('Kirim qatori')
        verbose_name_plural = _('Kirim qatorlari')
        ordering = ['id']

    def __str__(self):
        return f'{self.variant_id}: {self.quantity}'

    @property
    def line_total(self) -> Decimal:
        return self.unit_cost * self.quantity
