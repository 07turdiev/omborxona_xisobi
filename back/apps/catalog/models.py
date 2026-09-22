"""Katalog: kategoriya, o'lcham, rang, mahsulot va variant.

Mahsulot — model (masalan "Ayollar ko'ylagi"), variant — sotiladigan aniq
dona (o'sha ko'ylakning M o'lchami, qora rangi). Qoldiq, shtrix-kod va
tannarx variantda yuritiladi.
"""

from django.core.validators import RegexValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.fields import MoneyField
from apps.core.models import TimeStampedModel

#: Rang kodi — katalogdagi rang doirachasi shu kod bilan chiziladi.
HEX_VALIDATOR = RegexValidator(
    regex=r'^#[0-9A-Fa-f]{6}$',
    message=_('Rang kodi #RRGGBB ko‘rinishida bo‘lishi kerak, masalan #1A2B3C.'),
)


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
    """Rang. `hex_code` — katalogdagi rang doirachasi uchun."""

    name = models.CharField(_('Nomi'), max_length=40, unique=True)

    hex_code = models.CharField(
        _('Rang kodi'),
        max_length=7,
        validators=[HEX_VALIDATOR],
        help_text=_('#RRGGBB ko‘rinishida.'),
    )

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
    description = models.TextField(_('Tavsif'), blank=True)

    material = models.CharField(
        _('Tarkibi'), max_length=200, blank=True,
        help_text=_('Masalan: 60% paxta, 40% polyester.'),
    )

    care = models.CharField(
        _('Parvarish'), max_length=300, blank=True,
        help_text=_('Yuvish va dazmollash ko‘rsatmasi.'),
    )

    #: Onlayn do'kon manzilida ishlatiladi. Hozir hech qayerda
    #: ko'rinmaydi, lekin keyin o'zgartirilsa tashqi havolalar uziladi —
    #: shuning uchun mahsulot yaratilganda darhol beriladi.
    slug = models.SlugField(
        _('Manzil qismi'), max_length=220, unique=True,
        help_text=_('Nomdan avtomatik yasaladi. O‘zgartirish mumkin, lekin keyin emas.'),
    )

    sale_price = MoneyField(_('Sotuv narxi'), default=0)

    is_active = models.BooleanField(_('Faol'), default=True)

    class Meta:
        verbose_name = _('Mahsulot')
        verbose_name_plural = _('Mahsulotlar')
        ordering = ['name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            # Xizmat modelga emas, model xizmatga tayanmasligi uchun
            # import shu yerda: `services` modellarni import qiladi
            from apps.catalog.services import unique_slug

            self.slug = unique_slug(self.name, exclude_pk=self.pk)

        super().save(*args, **kwargs)


class ProductImage(TimeStampedModel):
    """Mahsulot rasmi — uchta o'lchamda saqlanadi.

    Rasm bitta rangga bog'langan bo'lishi mumkin (qora ko'ylakning
    surati) yoki umumiy bo'lishi mumkin (o'lcham jadvali, brend yorlig'i)
    — u holda `color` bo'sh qoladi.

    Yuklangan asl fayl saqlanmaydi, faqat qayta o'lchangan uchta WebP
    (izoh: `images.py`).
    """

    #: Bitta mahsulotga bundan ortiq rasm biriktirib bo'lmaydi
    MAX_PER_PRODUCT = 10

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='images',
        verbose_name=_('Mahsulot'),
    )

    color = models.ForeignKey(
        Color,
        on_delete=models.PROTECT,
        related_name='images',
        null=True,
        blank=True,
        verbose_name=_('Rang'),
        help_text=_('Bo‘sh bo‘lsa rasm butun mahsulotga tegishli.'),
    )

    thumb = models.ImageField(_('Kichik'), upload_to='products/thumb/')
    medium = models.ImageField(_('O‘rta'), upload_to='products/medium/')
    large = models.ImageField(_('Katta'), upload_to='products/large/')

    sort_order = models.PositiveSmallIntegerField(_('Tartib'), default=0)
    is_primary = models.BooleanField(_('Asosiy'), default=False)

    class Meta:
        verbose_name = _('Mahsulot rasmi')
        verbose_name_plural = _('Mahsulot rasmlari')
        ordering = ['sort_order', 'id']
        constraints = [
            # Ro'yxatdagi karta aynan bitta rasmni ko'rsatadi
            models.UniqueConstraint(
                fields=['product'],
                condition=models.Q(is_primary=True),
                name='one_primary_image_per_product',
            ),
        ]

    def __str__(self):
        return f'{self.product.name} — {self.color or "umumiy"}'


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


#: Tugayotgan variant: minimal qoldiq belgilangan va qoldiq unga yetgan.
#: Qoldiq ro'yxati ham, katalog ham shu bitta qoidaga qaraydi.
LOW_STOCK = models.Q(min_stock__gt=0, stock_quantity__lte=models.F('min_stock'))
