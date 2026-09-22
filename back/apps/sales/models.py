"""Sotuv (kassa) va qaytarish.

Har sotuv qatorida o'sha paytdagi tannarx nusxa sifatida saqlanadi
(`unit_cost`): keyin tannarx o'zgarsa ham eski chekning foydasi
o'zgarmaydi. Qaytarishda tovar aynan shu tannarx bilan qaytadi.
"""

from decimal import Decimal

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.fields import MoneyField
from apps.core.models import TimeStampedModel

REQUEST_KEY_HELP = _(
    'Kassa yuboradigan bir martalik kalit: tugma ikki marta bosilsa ham '
    'ikkinchi so\'rov yangi hujjat yaratmaydi'
)


class Sale(TimeStampedModel):
    """Chek."""

    class Status(models.TextChoices):
        COMPLETED = 'completed', _('Yakunlangan')
        VOIDED = 'voided', _('Bekor qilingan')

    number = models.CharField(_('Raqami'), max_length=20, unique=True)

    #: Qayerda sotildi. Tovar shu joyning qoldig'idan yechiladi.
    location = models.ForeignKey(
        'inventory.Location',
        on_delete=models.PROTECT,
        related_name='sales',
        verbose_name=_('Joy'),
    )

    #: Takroriy so'rovni ajratish uchun (idempotentlik)
    request_key = models.UUIDField(
        _('So‘rov kaliti'), null=True, blank=True, unique=True, help_text=REQUEST_KEY_HELP
    )

    cashier = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sales',
        verbose_name=_('Kassir'),
    )

    subtotal = MoneyField(_('Chegirmasiz summa'), default=0)
    discount_total = MoneyField(_('Chegirma'), default=0)
    total = MoneyField(_('Jami'), default=0)

    cash_amount = MoneyField(_('Naqd'), default=0)
    card_amount = MoneyField(_('Karta'), default=0)

    status = models.CharField(
        _('Holati'), max_length=10, choices=Status.choices, default=Status.COMPLETED
    )

    voided_at = models.DateTimeField(_('Bekor qilingan vaqt'), null=True, blank=True)
    voided_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='voided_sales',
        verbose_name=_('Kim bekor qildi'),
    )

    #: Fiskal provayder javobi (hozircha bo'sh — `NullFiscalProvider`)
    fiscal_receipt_id = models.CharField(_('Fiskal chek raqami'), max_length=64, blank=True)
    fiscal_qr_url = models.URLField(_('Fiskal QR havolasi'), blank=True)

    class Meta:
        verbose_name = _('Sotuv')
        verbose_name_plural = _('Sotuvlar')
        ordering = ['-created_at', '-id']
        indexes = [
            models.Index(fields=['status', '-created_at']),
            models.Index(fields=['cashier', '-created_at']),
        ]

    def __str__(self):
        return self.number


class SaleLine(models.Model):
    """Chek qatori."""

    sale = models.ForeignKey(
        Sale,
        on_delete=models.CASCADE,
        related_name='lines',
        verbose_name=_('Sotuv'),
    )

    variant = models.ForeignKey(
        'catalog.Variant',
        on_delete=models.PROTECT,
        related_name='sale_lines',
        verbose_name=_('Variant'),
    )

    quantity = models.PositiveIntegerField(_('Miqdor'))

    unit_price = MoneyField(_('Narxi'))
    discount_amount = MoneyField(_('Chegirma'), default=0)
    line_total = MoneyField(_('Qator summasi'), default=0)

    #: Sotuv paytidagi o'rtacha tannarx nusxasi
    unit_cost = MoneyField(_('Birlik tannarxi'), default=0)
    line_cost = MoneyField(_('Qator tannarxi'), default=0)

    class Meta:
        verbose_name = _('Sotuv qatori')
        verbose_name_plural = _('Sotuv qatorlari')
        ordering = ['id']

    def __str__(self):
        return f'{self.variant_id}: {self.quantity}'

    @property
    def profit(self) -> Decimal:
        return self.line_total - self.line_cost


class SaleReturn(TimeStampedModel):
    """Qaytarish — mavjud chekka bog'lanadi."""

    class RefundMethod(models.TextChoices):
        CASH = 'cash', _('Naqd')
        CARD = 'card', _('Karta')

    number = models.CharField(_('Raqami'), max_length=20, unique=True)

    request_key = models.UUIDField(
        _('So‘rov kaliti'), null=True, blank=True, unique=True, help_text=REQUEST_KEY_HELP
    )

    sale = models.ForeignKey(
        Sale,
        on_delete=models.PROTECT,
        related_name='returns',
        verbose_name=_('Sotuv'),
    )

    total = MoneyField(_('Qaytarilgan summa'), default=0)

    refund_method = models.CharField(
        _('Qaytarish usuli'),
        max_length=10,
        choices=RefundMethod.choices,
        default=RefundMethod.CASH,
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='sale_returns',
        verbose_name=_('Kim qabul qildi'),
    )

    fiscal_receipt_id = models.CharField(_('Fiskal chek raqami'), max_length=64, blank=True)
    fiscal_qr_url = models.URLField(_('Fiskal QR havolasi'), blank=True)

    class Meta:
        verbose_name = _('Qaytarish')
        verbose_name_plural = _('Qaytarishlar')
        ordering = ['-created_at', '-id']

    def __str__(self):
        return self.number


class SaleReturnLine(models.Model):
    """Qaytarish qatori — asl chek qatoriga bog'lanadi."""

    sale_return = models.ForeignKey(
        SaleReturn,
        on_delete=models.CASCADE,
        related_name='lines',
        verbose_name=_('Qaytarish'),
    )

    sale_line = models.ForeignKey(
        SaleLine,
        on_delete=models.PROTECT,
        related_name='return_lines',
        verbose_name=_('Sotuv qatori'),
    )

    quantity = models.PositiveIntegerField(_('Miqdor'))

    #: Asl qatordagi tannarx — tovar shu qiymat bilan qoldiqqa qaytadi
    unit_cost = MoneyField(_('Birlik tannarxi'), default=0)

    #: Chegirma hisobga olingan qaytariladigan summa
    refund_amount = MoneyField(_('Qaytariladigan summa'), default=0)

    class Meta:
        verbose_name = _('Qaytarish qatori')
        verbose_name_plural = _('Qaytarish qatorlari')
        ordering = ['id']

    def __str__(self):
        return f'{self.sale_line_id}: {self.quantity}'
