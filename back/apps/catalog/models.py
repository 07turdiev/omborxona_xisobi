"""Katalog: kategoriya, o'lcham, rang, mahsulot va variant.

Mahsulot — model (masalan "Ayollar ko'ylagi"), variant — sotiladigan aniq
dona (o'sha ko'ylakning M o'lchami, qora rangi). Qoldiq, shtrix-kod va
tannarx variantda yuritiladi.
"""

from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.fields import MoneyField
from apps.core.models import TimeStampedModel


class Category(TimeStampedModel):
    """Kategoriya — oddiy ro'yxat, ichma-ich emas."""

    name = models.CharField(_('Nomi'), max_length=100, unique=True)

    class Meta:
        verbose_name = _('Kategoriya')
        verbose_name_plural = _('Kategoriyalar')
        ordering = ['name']

    def __str__(self):
        return self.name


class Size(TimeStampedModel):
    """O'lcham. `position` bilan tartiblanadi: XS, S, M, L, XL."""

    name = models.CharField(_('Nomi'), max_length=20, unique=True)
    position = models.PositiveSmallIntegerField(_('Tartib'), default=0)

    class Meta:
        verbose_name = _('O‘lcham')
        verbose_name_plural = _('O‘lchamlar')
        ordering = ['position', 'name']

    def __str__(self):
        return self.name


class Color(TimeStampedModel):
    """Rang."""

    name = models.CharField(_('Nomi'), max_length=40, unique=True)

    class Meta:
        verbose_name = _('Rang')
        verbose_name_plural = _('Ranglar')
        ordering = ['name']

    def __str__(self):
        return self.name


class Product(TimeStampedModel):
    """Mahsulot — model darajasi. Sotuv narxi shu yerda."""

    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name='products',
        verbose_name=_('Kategoriya'),
    )

    name = models.CharField(_('Nomi'), max_length=200)
    brand = models.CharField(_('Brend'), max_length=100, blank=True)
    description = models.CharField(_('Izoh'), max_length=300, blank=True)

    photo = models.ImageField(_('Rasm'), upload_to='products/', blank=True, null=True)

    sale_price = MoneyField(_('Sotuv narxi'), default=0)

    is_active = models.BooleanField(_('Faol'), default=True)

    class Meta:
        verbose_name = _('Mahsulot')
        verbose_name_plural = _('Mahsulotlar')
        ordering = ['name']

    def __str__(self):
        return self.name


class Variant(TimeStampedModel):
    """Sotiladigan dona: mahsulot + o'lcham + rang.

    O'lchamsiz va rangsiz mahsulotda bitta variant bo'ladi — u avtomatik
    yaratiladi va foydalanuvchiga ko'rinmaydi.
    """

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='variants',
        verbose_name=_('Mahsulot'),
    )

    size = models.ForeignKey(
        Size,
        on_delete=models.PROTECT,
        related_name='variants',
        null=True,
        blank=True,
        verbose_name=_('O‘lcham'),
    )

    color = models.ForeignKey(
        Color,
        on_delete=models.PROTECT,
        related_name='variants',
        null=True,
        blank=True,
        verbose_name=_('Rang'),
    )

    sku = models.CharField(_('Artikul'), max_length=40, unique=True)
    barcode = models.CharField(_('Shtrix-kod'), max_length=32, unique=True)

    #: Bo'sh bo'lsa mahsulotning narxi ishlatiladi
    sale_price = MoneyField(_('Sotuv narxi'), null=True, blank=True)

    #: O'rtacha tannarx — kirim va qaytarishda qayta hisoblanadi
    average_cost = MoneyField(_('O‘rtacha tannarx'), default=0)

    #: Jurnal asosidagi qoldiq keshi. Faqat `apps.inventory.services` yozadi.
    stock_quantity = models.IntegerField(_('Qoldiq'), default=0)

    min_stock = models.PositiveIntegerField(_('Minimal qoldiq'), default=0)

    is_active = models.BooleanField(_('Faol'), default=True)

    class Meta:
        verbose_name = _('Variant')
        verbose_name_plural = _('Variantlar')
        ordering = ['product__name', 'size__position', 'color__name']
        constraints = [
            models.UniqueConstraint(
                fields=['product', 'size', 'color'],
                name='unique_product_size_color',
                # O'lchamsiz/rangsiz variant ikki marta yaratilmasin
                nulls_distinct=False,
            ),
            # Xizmat darajasidagi tekshiruv ortidagi so'nggi himoya:
            # qoldiq hech qachon manfiy bo'lmasin (migratsiya 0003)
            models.CheckConstraint(
                condition=models.Q(stock_quantity__gte=0),
                name='variant_stock_not_negative',
            ),
        ]
        indexes = [models.Index(fields=['barcode'])]

    def __str__(self):
        return f'{self.product.name} {self.label}'.strip()

    @property
    def label(self) -> str:
        """"M / qora" ko'rinishidagi qisqa belgi."""
        parts = [part.name for part in (self.size, self.color) if part]
        return ' / '.join(parts)

    @property
    def price(self):
        """Amaldagi sotuv narxi: variantniki bo'lmasa — mahsulotniki."""
        return self.sale_price if self.sale_price is not None else self.product.sale_price
