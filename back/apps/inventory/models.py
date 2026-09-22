"""Ombor: joylar, harakatlar jurnali, sanoq va hisobdan chiqarish.

Do'konda tovar ikki joyda turadi: **Ombor** va **Do'kon** (savdo zali).
Tovar avval omborga keladi, sotiladigani zalga ko'chiriladi. Shuning
uchun har harakat qaysi joyda bo'lganini aytadi va qoldiq joy bo'yicha
alohida yuritiladi (`VariantStock`).

`StockMovement` — qoldiqning yagona haqiqat manbai. Jurnal yozuvi hech
qachon o'zgartirilmaydi va o'chirilmaydi: xato bo'lsa teskari yozuv
qo'shiladi. `VariantStock.quantity` (joydagi qoldiq) va
`Variant.stock_quantity` (joylarning yig'indisi) — shu jurnaldan
hisoblangan kesh.
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
    COUNT_ADJUSTMENT = 'count_adjustment', _('Sanoq tuzatishi')
    WRITE_OFF = 'write_off', _('Hisobdan chiqarish')
    TRANSFER_OUT = 'transfer_out', _('Ko‘chirildi (chiqdi)')
    TRANSFER_IN = 'transfer_in', _('Ko‘chirildi (kirdi)')


class Location(TimeStampedModel):
    """Tovar turadigan joy.

    Do'konda ikkitasi bor: tovar keladigan **Ombor** va sotiladigan
    **Do'kon** (savdo zali). Ro'yxat ochiq: ikkinchi do'kon ochilsa,
    yangi qator qo'shiladi va qolgan kod o'zgarmaydi.
    """

    class Kind(models.TextChoices):
        WAREHOUSE = 'warehouse', _('Ombor')
        SHOP = 'shop', _('Do‘kon')

    name = models.CharField(_('Nomi'), max_length=80, unique=True)
    kind = models.CharField(_('Turi'), max_length=10, choices=Kind.choices)
    is_active = models.BooleanField(_('Faol'), default=True)

    class Meta:
        verbose_name = _('Joy')
        verbose_name_plural = _('Joylar')
        ordering = ['kind', 'name']

    def __str__(self):
        return self.name

    @classmethod
    def of_kind(cls, kind: str) -> 'Location':
        """Shu turdagi birinchi faol joy.

        Yo'q bo'lsa — yaratiladi. Ombor va zal do'konning tuzilishi:
        ular hech qachon yo'q bo'lmasligi kerak, aks holda tovar
        qabul qilish ham, sotish ham to'xtab qolardi.
        """
        location = cls.objects.filter(kind=kind, is_active=True).order_by('pk').first()

        if location is None:
            location = cls.objects.create(kind=kind, name=cls.Kind(kind).label)

        return location

    @classmethod
    def warehouse(cls) -> 'Location':
        return cls.of_kind(cls.Kind.WAREHOUSE)

    @classmethod
    def shop(cls) -> 'Location':
        return cls.of_kind(cls.Kind.SHOP)


class VariantStock(models.Model):
    """Variantning bitta joydagi qoldig'i — jurnaldan hisoblangan kesh."""

    variant = models.ForeignKey(
        'catalog.Variant',
        on_delete=models.CASCADE,
        related_name='stocks',
        verbose_name=_('Variant'),
    )

    location = models.ForeignKey(
        Location,
        on_delete=models.PROTECT,
        related_name='stocks',
        verbose_name=_('Joy'),
    )

    quantity = models.IntegerField(_('Qoldiq'), default=0)

    class Meta:
        verbose_name = _('Joydagi qoldiq')
        verbose_name_plural = _('Joydagi qoldiqlar')
        ordering = ['location_id', 'variant_id']
        constraints = [
            models.UniqueConstraint(
                fields=['variant', 'location'], name='unique_variant_location'
            ),
        ]
        indexes = [models.Index(fields=['location', 'variant'])]

    def __str__(self):
        return f'{self.variant_id} @ {self.location_id}: {self.quantity}'


class StockMovement(models.Model):
    """Qoldiqning bitta o'zgarishi. Kirim musbat, chiqim manfiy."""

    variant = models.ForeignKey(
        'catalog.Variant',
        on_delete=models.PROTECT,
        related_name='movements',
        verbose_name=_('Variant'),
    )

    #: Qaysi joyda sodir bo'ldi. Ko'chirishda ikkita yozuv bo'ladi:
    #: manbadan chiqim, maqsadga kirim.
    location = models.ForeignKey(
        Location,
        on_delete=models.PROTECT,
        related_name='movements',
        verbose_name=_('Joy'),
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
        indexes = [
            models.Index(fields=['variant', '-created_at']),
            models.Index(fields=['location', '-created_at']),
        ]

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

    #: Qaysi joy sanaldi: zal alohida, ombor alohida
    location = models.ForeignKey(
        Location,
        on_delete=models.PROTECT,
        related_name='stock_counts',
        verbose_name=_('Joy'),
    )

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

    location = models.ForeignKey(
        Location,
        on_delete=models.PROTECT,
        related_name='write_offs',
        verbose_name=_('Joy'),
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


class Transfer(TimeStampedModel):
    """Ko'chirish: ombordan zalga (yoki teskari).

    Tasdiqlash bosqichi yo'q — ko'chirish bir harakatda bo'ladi: tovar
    qo'lga olinib, ikkinchi joyga qo'yiladi. Jurnalga ikkita yozuv
    tushadi: manbadan chiqim, maqsadga kirim.
    """

    number = models.CharField(_('Raqami'), max_length=20, unique=True)
    date = models.DateField(_('Sanasi'))

    source = models.ForeignKey(
        Location,
        on_delete=models.PROTECT,
        related_name='transfers_out',
        verbose_name=_('Qayerdan'),
    )

    target = models.ForeignKey(
        Location,
        on_delete=models.PROTECT,
        related_name='transfers_in',
        verbose_name=_('Qayerga'),
    )

    note = models.CharField(_('Izoh'), max_length=300, blank=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='transfers',
        verbose_name=_('Kim ko‘chirdi'),
    )

    class Meta:
        verbose_name = _('Ko‘chirish')
        verbose_name_plural = _('Ko‘chirishlar')
        ordering = ['-created_at', '-id']

    def __str__(self):
        return self.number


class TransferLine(models.Model):
    """Ko'chirish qatori."""

    transfer = models.ForeignKey(
        Transfer,
        on_delete=models.CASCADE,
        related_name='lines',
        verbose_name=_('Ko‘chirish'),
    )

    variant = models.ForeignKey(
        'catalog.Variant',
        on_delete=models.PROTECT,
        related_name='transfer_lines',
        verbose_name=_('Variant'),
    )

    quantity = models.PositiveIntegerField(_('Miqdor'))

    class Meta:
        verbose_name = _('Ko‘chirish qatori')
        verbose_name_plural = _('Ko‘chirish qatorlari')
        ordering = ['id']

    def __str__(self):
        return f'{self.variant_id}: {self.quantity}'
