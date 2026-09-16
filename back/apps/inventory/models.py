"""Ombor: harakatlar jurnali, inventarizatsiya va hisobdan chiqarish.

`StockMovement` — qoldiqning yagona haqiqat manbai. Jurnal yozuvi hech
qachon o'zgartirilmaydi va o'chirilmaydi: xato bo'lsa teskari yozuv
qo'shiladi. `Variant.stock_quantity` esa shu jurnaldan hisoblangan kesh.
"""

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.fields import MoneyField
from apps.core.models import TimeStampedModel


class MovementReason(models.TextChoices):
    PURCHASE = 'purchase', _('Kirim')
    PURCHASE_CANCEL = 'purchase_cancel', _('Kirim bekor qilindi')
    SALE = 'sale', _('Sotuv')
    SALE_VOID = 'sale_void', _('Sotuv bekor qilindi')
    RETURN = 'return', _('Qaytarish')
    COUNT_ADJUSTMENT = 'count_adjustment', _('Inventarizatsiya tuzatishi')
    WRITE_OFF = 'write_off', _('Hisobdan chiqarish')


class StockMovement(models.Model):
    """Qoldiqning bitta o'zgarishi. Kirim musbat, chiqim manfiy."""

    variant = models.ForeignKey(
        'catalog.Variant',
        on_delete=models.PROTECT,
        related_name='movements',
        verbose_name=_('Variant'),
    )

    quantity = models.IntegerField(_('Miqdor'))

    reason = models.CharField(_('Sabab'), max_length=20, choices=MovementReason.choices)

    #: Manba hujjat: 'purchase', 'sale', 'sale_return', 'stock_count', 'write_off'
    document_type = models.CharField(_('Hujjat turi'), max_length=20, blank=True)
    document_id = models.PositiveIntegerField(_('Hujjat raqami'), null=True, blank=True)

    unit_cost = MoneyField(_('Birlik tannarxi'), default=0)

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='movements',
        verbose_name=_('Xodim'),
    )

    created_at = models.DateTimeField(_('Vaqti'), auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = _('Ombor harakati')
        verbose_name_plural = _('Ombor harakatlari')
        ordering = ['-created_at', '-id']
        indexes = [models.Index(fields=['variant', '-created_at'])]

    def __str__(self):
        return f'{self.variant_id}: {self.quantity:+d} ({self.get_reason_display()})'

    def save(self, *args, **kwargs):
        """Yozuv faqat bir marta yoziladi."""
        if self.pk is not None:
            raise ValueError('Ombor harakatini o‘zgartirib bo‘lmaydi')

        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValueError('Ombor harakatini o‘chirib bo‘lmaydi')


class StockCount(TimeStampedModel):
    """Inventarizatsiya (sanoq)."""

    class Status(models.TextChoices):
        DRAFT = 'draft', _('Qoralama')
        CONFIRMED = 'confirmed', _('Tasdiqlangan')

    number = models.CharField(_('Raqami'), max_length=20, unique=True)
    date = models.DateField(_('Sanasi'))

    status = models.CharField(
        _('Holati'), max_length=10, choices=Status.choices, default=Status.DRAFT
    )

    #: Bo'sh bo'lsa — butun do'kon bo'yicha
    category = models.ForeignKey(
        'catalog.Category',
        on_delete=models.PROTECT,
        related_name='stock_counts',
        null=True,
        blank=True,
        verbose_name=_('Kategoriya'),
    )

    note = models.CharField(_('Izoh'), max_length=300, blank=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='stock_counts',
        verbose_name=_('Kim boshladi'),
    )

    confirmed_at = models.DateTimeField(_('Tasdiqlangan vaqt'), null=True, blank=True)

    class Meta:
        verbose_name = _('Inventarizatsiya')
        verbose_name_plural = _('Inventarizatsiyalar')
        ordering = ['-date', '-id']

    def __str__(self):
        return self.number


class StockCountLine(models.Model):
    """Sanoq qatori: kutilgan va sanab chiqilgan miqdor."""

    stock_count = models.ForeignKey(
        StockCount,
        on_delete=models.CASCADE,
        related_name='lines',
        verbose_name=_('Inventarizatsiya'),
    )

    variant = models.ForeignKey(
        'catalog.Variant',
        on_delete=models.PROTECT,
        related_name='count_lines',
        verbose_name=_('Variant'),
    )

    #: Tasdiqlashda jurnaldagi qoldiq shu yerga yoziladi
    expected_quantity = models.IntegerField(_('Kutilgan'), default=0)
    counted_quantity = models.IntegerField(_('Sanaldi'), default=0)

    class Meta:
        verbose_name = _('Sanoq qatori')
        verbose_name_plural = _('Sanoq qatorlari')
        ordering = ['id']
        constraints = [
            models.UniqueConstraint(
                fields=['stock_count', 'variant'], name='unique_variant_in_stock_count'
            ),
        ]

    def __str__(self):
        return f'{self.variant_id}: {self.counted_quantity}'

    @property
    def difference(self) -> int:
        return self.counted_quantity - self.expected_quantity


class WriteOff(TimeStampedModel):
    """Hisobdan chiqarish: buzilgan yoki yo'qolgan tovar."""

    variant = models.ForeignKey(
        'catalog.Variant',
        on_delete=models.PROTECT,
        related_name='write_offs',
        verbose_name=_('Variant'),
    )

    quantity = models.PositiveIntegerField(_('Miqdor'))
    reason = models.CharField(_('Sababi'), max_length=300)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='write_offs',
        verbose_name=_('Kim yozdi'),
    )

    class Meta:
        verbose_name = _('Hisobdan chiqarish')
        verbose_name_plural = _('Hisobdan chiqarishlar')
        ordering = ['-created_at', '-id']

    def __str__(self):
        return f'{self.variant_id}: {self.quantity}'
