"""Omborlararo ko'chirish hujjati — ikki bosqichli.

Promptning 6-bandi: "jo'natildi → qabul qilindi. Oradagi farq
(yo'qolgan, kam yetib kelgan) alohida ko'rinishi kerak."

Nima uchun alohida model, `Document` emas: kirim va sotuv **bir
bosqichli** — tasdiqlandi va tugadi. Ko'chirishda esa ikkita alohida
voqea bor, ular orasida kunlar o'tishi mumkin, va har birida o'z
miqdori qayd etiladi. `Document.status` ga uchinchi holat qo'shish
kirim/sotuv mantiqini ham murakkablashtirardi.

Holat oqimi:

    qoralama  →  jo'natilgan  →  qabul qilingan
                     ↓                 ↓
              tovar tranzitda    farq bo'lsa kamomad yoziladi

`qty_sent` va `qty_received` **ikki alohida ustun** — naqsh
InvenTree'ning `PurchaseOrderLineItem.quantity` / `.received`
juftligidan (order/models.py:2354). Uning `TransferOrder` i esa buni
qilmaydi: u yerda kamomad `min()` bilan jimgina yutib yuboriladi
(order/models.py:4235).
"""

from __future__ import annotations

from decimal import Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.core.fields import FactorField, QuantityField
from apps.core.models import TenantOwnedModel


class Transfer(TenantOwnedModel):
    """Omborlararo ko'chirish."""

    class Status(models.TextChoices):
        DRAFT = 'draft', _('Qoralama')
        SENT = 'sent', _('Jo\'natilgan')
        RECEIVED = 'received', _('Qabul qilingan')
        CANCELLED = 'cancelled', _('Bekor qilingan')

    PREFIX = 'KOCH'

    number = models.CharField(_('Raqami'), max_length=40)
    date = models.DateField(_('Sanasi'), default=timezone.localdate)

    status = models.CharField(
        _('Holati'), max_length=20, choices=Status.choices, default=Status.DRAFT
    )

    from_warehouse = models.ForeignKey(
        'warehouse.Warehouse',
        on_delete=models.PROTECT,
        related_name='transfers_out',
        verbose_name=_('Qayerdan'),
    )

    to_warehouse = models.ForeignKey(
        'warehouse.Warehouse',
        on_delete=models.PROTECT,
        related_name='transfers_in',
        verbose_name=_('Qayerga'),
    )

    #: Yo'ldagi tovar shu omborda turadi. Uning vazifasi `transit`
    #: bo'lishi kerak — shunda qoldiq sotuvga chiqmaydi.
    transit_warehouse = models.ForeignKey(
        'warehouse.Warehouse',
        on_delete=models.PROTECT,
        related_name='transfers_transit',
        verbose_name=_('Tranzit ombor'),
    )

    note = models.TextField(_('Izoh'), blank=True)

    sent_at = models.DateTimeField(_('Jo\'natilgan vaqt'), null=True, blank=True)
    received_at = models.DateTimeField(_('Qabul qilingan vaqt'), null=True, blank=True)
    cancelled_at = models.DateTimeField(_('Bekor qilingan vaqt'), null=True, blank=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='transfers',
        verbose_name=_('Kim yaratdi'),
    )

    class Meta:
        verbose_name = _('Ko\'chirish')
        verbose_name_plural = _('Ko\'chirishlar')
        ordering = ['-date', '-id']
        constraints = [
            models.UniqueConstraint(
                fields=['tenant', 'number'], name='unique_tenant_transfer_number'
            )
        ]
        indexes = [models.Index(fields=['tenant', 'status', '-date'])]

    def __str__(self):
        return self.number

    @property
    def is_editable(self) -> bool:
        return self.status == self.Status.DRAFT

    @property
    def in_transit(self) -> bool:
        """Tovar hozir yo'ldami?"""
        return self.status == self.Status.SENT

    @property
    def total_shortfall(self) -> Decimal:
        """Umumiy kamomad — jo'natilgan va qabul qilingan farqi."""
        if self.status != self.Status.RECEIVED:
            return Decimal('0')

        return sum(
            (line.shortfall for line in self.lines.all()), Decimal('0')
        )

    @property
    def has_shortfall(self) -> bool:
        return self.total_shortfall > 0

    def clean(self):
        super().clean()

        if self.from_warehouse_id and self.from_warehouse_id == self.to_warehouse_id:
            raise ValidationError({
                'to_warehouse': _('Manba va maqsad ombor bir xil bo\'lishi mumkin emas')
            })

        if self.transit_warehouse_id:
            from apps.warehouse.models import Warehouse

            if self.transit_warehouse.purpose != Warehouse.Purpose.TRANSIT:
                raise ValidationError({
                    'transit_warehouse': _(
                        'Tranzit ombor sifatida faqat "Tranzit" vazifasidagi '
                        'ombor tanlanishi mumkin — aks holda yo\'ldagi tovar '
                        'sotuvga chiqib ketadi'
                    )
                })


class TransferLine(TenantOwnedModel):
    """Ko'chirish qatori: jo'natilgan va qabul qilingan miqdor."""

    transfer = models.ForeignKey(
        Transfer,
        on_delete=models.CASCADE,
        related_name='lines',
        verbose_name=_('Ko\'chirish'),
    )

    variant = models.ForeignKey(
        'catalog.Variant',
        on_delete=models.PROTECT,
        related_name='transfer_lines',
        verbose_name=_('Variant'),
    )

    batch = models.ForeignKey(
        'stock.Batch',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='transfer_lines',
        verbose_name=_('Partiya'),
    )

    unit = models.CharField(_('Birlik'), max_length=30, blank=True)
    factor = FactorField(_('Koeffitsient'), default=1)

    quantity_sent = QuantityField(_('Jo\'natildi'), positive=True)
    quantity_sent_base = QuantityField(_('Jo\'natildi (bazaviy)'), positive=True)

    #: Qabul qilinganda to'ldiriladi. `null` — hali qabul qilinmagan;
    #: `0` — umuman yetib kelmagan. Bu ikkisi turli holatlar.
    quantity_received = QuantityField(
        _('Qabul qilindi'), positive=True, null=True, blank=True
    )
    quantity_received_base = QuantityField(
        _('Qabul qilindi (bazaviy)'), positive=True, null=True, blank=True
    )

    note = models.CharField(_('Izoh'), max_length=250, blank=True)
    position = models.PositiveSmallIntegerField(_('Tartib'), default=0)

    class Meta:
        verbose_name = _('Ko\'chirish qatori')
        verbose_name_plural = _('Ko\'chirish qatorlari')
        ordering = ['position', 'id']
        indexes = [models.Index(fields=['tenant', 'transfer'])]

    def __str__(self):
        return f'{self.variant} × {self.quantity_sent} {self.unit}'

    @property
    def shortfall(self) -> Decimal:
        """Yetib kelmagan miqdor (bazaviy birlikda).

        Hali qabul qilinmagan bo'lsa nol — kamomad faqat qabuldan keyin
        ma'lum bo'ladi.
        """
        if self.quantity_received_base is None:
            return Decimal('0')

        return max(self.quantity_sent_base - self.quantity_received_base, Decimal('0'))

    @property
    def is_complete(self) -> bool:
        return self.quantity_received_base is not None and self.shortfall == 0
