"""Mahsulotlar katalogi: kategoriya daraxti, mahsulot, variant, atributlar.

Arxitektura qarorlari shu yerda uchraydi:

- **4-qaror (`ltree`):** `Category.path` — ID lardan qurilgan yo'l.
- **2-qaror (JSONB):** atribut qiymatlari `Variant.attributes` da,
  har biri `{"raw": ..., "num": ...}` juftligi sifatida. Ta'riflar esa
  kategoriyaga bog'langan `AttributeDefinition` da va **jonli meros**
  oladi — ya'ni kategoriyaga yangi atribut qo'shsangiz, o'sha
  kategoriyadagi barcha mahsulotlarda darhol paydo bo'ladi.
- **6-qaror (`Decimal`):** narx va koeffitsientlar `Decimal`.

Dizayndan (`store/`) farqlar:

- Dizaynda mahsulot yassi: `name`, `sku`, `category`, `subcategory`.
  Bizda `Product` (model) → `Variant` (aniq SKU). Kiyim do'konida bir
  ko'ylakning 5 o'lchami × 3 rangi = 15 variant bo'ladi, ularning har
  biri alohida qoldiqqa ega. Qurilishda esa mahsulotning bitta varianti
  bo'ladi — u avtomatik yaratiladi va foydalanuvchi buni sezmaydi.
- Dizaynda kategoriya JS da qattiq yozilgan va 2 daraja. Bizda cheksiz
  chuqurlikdagi daraxt, tashkilot o'zi boshqaradi.
"""

from __future__ import annotations

from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.utils.translation import gettext_lazy as _

from apps.catalog.fields import LtreeField
from apps.core.fields import FactorField, MoneyField, QuantityField
from apps.core.models import TenantOwnedModel


class Category(TenantOwnedModel):
    """Kategoriya daraxtining tuguni.

    `path` — `ltree` yo'li, ID lardan quriladi (`c1.c7.c23`). Nomdan
    emas: `ltree` faqat `[A-Za-z0-9_]` ga ruxsat beradi, o'zbekcha
    nomlarda esa apostrof va bo'shliq bor. Qolaversa nom o'zgarganda
    yo'l buzilmasligi kerak.
    """

    name = models.CharField(_('Nomi'), max_length=150)

    parent = models.ForeignKey(
        'self',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='children',
        verbose_name=_('Yuqori kategoriya'),
    )

    path = LtreeField(_('Yo\'l'), null=True, blank=True, editable=False)

    #: Yangi mahsulot uchun standart o'lchov birligi (masalan `kg`, `dona`).
    #: Ostki kategoriyalarga meros o'tadi.
    default_unit = models.CharField(_('Standart birlik'), max_length=30, blank=True)

    #: SKU generatsiyasi uchun prefiks (dizayndagi `CATEGORIES[].prefix`).
    code_prefix = models.CharField(_('Kod prefiksi'), max_length=10, blank=True)

    is_active = models.BooleanField(_('Faol'), default=True)

    class Meta:
        verbose_name = _('Kategoriya')
        verbose_name_plural = _('Kategoriyalar')
        ordering = ['path']
        constraints = [
            models.UniqueConstraint(
                fields=['tenant', 'parent', 'name'],
                name='unique_category_name_in_parent',
            )
        ]

    def __str__(self):
        return self.name

    def clean(self):
        """O'zini o'ziga (yoki o'z avlodiga) bo'ysundirishga yo'l qo'ymaydi."""
        super().clean()

        if self.parent_id is None or self.pk is None:
            return

        if self.parent_id == self.pk:
            raise ValidationError({'parent': _('Kategoriya o\'ziga bo\'ysuna olmaydi')})

        if self.path and self.parent.path and self.parent.path.startswith(f'{self.path}.'):
            raise ValidationError({
                'parent': _('Kategoriyani o\'z ostki kategoriyasiga ko\'chirib bo\'lmaydi')
            })

    @transaction.atomic
    def save(self, *args, **kwargs):
        """Saqlaydi va `path` ni qayta hisoblaydi.

        Yo'l ID ga tayangani uchun yangi yozuvda u faqat `INSERT` dan
        keyin ma'lum bo'ladi — shuning uchun ikki bosqichli saqlash.
        Ota o'zgargan bo'lsa, butun ostki daraxt bitta `UPDATE` bilan
        ko'chiriladi.
        """
        old_path = None

        if self.pk:
            old_path = (
                Category.objects.filter(pk=self.pk)
                .values_list('path', flat=True)
                .first()
            )

        super().save(*args, **kwargs)

        parent_path = self.parent.path if self.parent_id else None
        new_path = f'{parent_path}.c{self.pk}' if parent_path else f'c{self.pk}'

        if new_path == old_path:
            return

        self.path = new_path
        super().save(update_fields=['path'])

        if old_path:
            self._move_descendants(old_path, new_path)

    def _move_descendants(self, old_path: str, new_path: str) -> None:
        """Ostki daraxtdagi barcha yo'llarni bitta so'rov bilan ko'chiradi.

        `ltree` ning `subpath` funksiyasi eski prefiksni kesib tashlaydi,
        `||` esa yangisini ulaydi. ORM bilan har bir avlodni alohida
        yangilash o'nlab so'rov bo'lardi.
        """
        from django.db import connection

        with connection.cursor() as cursor:
            cursor.execute(
                """
                UPDATE catalog_category
                SET path = %s::ltree || subpath(path, nlevel(%s::ltree))
                WHERE path <@ %s::ltree
                  AND path <> %s::ltree
                """,
                [new_path, old_path, old_path, old_path],
            )

    def ancestors(self, include_self: bool = True):
        """Ajdodlar, ildizdan boshlab tartiblangan."""
        if not self.path:
            return Category.objects.none()

        query = Category.objects.filter(path__ancestor_of=self.path)

        if not include_self:
            query = query.exclude(pk=self.pk)

        return query.order_by('path')

    def descendants(self, include_self: bool = False):
        """Avlodlar."""
        if not self.path:
            return Category.objects.none()

        query = Category.objects.filter(path__descendant_of=self.path)

        if not include_self:
            query = query.exclude(pk=self.pk)

        return query.order_by('path')

    @property
    def depth(self) -> int:
        """Daraja: ildiz — 1."""
        return len(self.path.split('.')) if self.path else 0


class AttributeDefinition(TenantOwnedModel):
    """Kategoriyaga bog'langan atribut ta'rifi.

    Ostki kategoriyalarga **jonli meros** o'tadi: qiymat mahsulotga
    nusxalanmaydi, o'qish paytida kategoriya ajdodlari bo'ylab yig'iladi.
    InvenTree buni teskari qiladi — mahsulot yaratilganda default
    qiymatlarni nusxalab qo'yadi (`part/models.py:2349`), natijada
    kategoriyaga keyin qo'shilgan atribut eski mahsulotlarda paydo
    bo'lmaydi.
    """

    class ValueType(models.TextChoices):
        TEXT = 'text', _('Matn')
        NUMBER = 'number', _('Son')
        CHOICE = 'choice', _('Ro\'yxatdan tanlash')
        BOOLEAN = 'boolean', _('Ha / yo\'q')

    class Uniqueness(models.IntegerChoices):
        """Qiymat unikal bo'lishi shartmi?

        Manba g'oyasi: InvenTree `ParameterTemplate.UniqueOptions`
        (common/models.py:2624). Bizda tashkilot doirasida.
        """

        NONE = 0, _('Talab qilinmaydi')
        TENANT = 1, _('Tashkilot ichida unikal')

    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        related_name='attribute_definitions',
        verbose_name=_('Kategoriya'),
    )

    #: JSONB kaliti. Faqat lotin harflari va pastki chiziq.
    key = models.CharField(
        _('Kalit'),
        max_length=50,
        help_text=_('JSONB kaliti. Masalan: qalinlik, rang, olcham'),
    )

    name = models.CharField(_('Nomi'), max_length=150)

    value_type = models.CharField(
        _('Qiymat turi'),
        max_length=20,
        choices=ValueType.choices,
        default=ValueType.TEXT,
    )

    unit = models.CharField(
        _('O\'lchov birligi'),
        max_length=30,
        blank=True,
        help_text=_('Son atributlar uchun. Masalan: mm, kg'),
    )

    choices = models.JSONField(
        _('Tanlovlar'),
        default=list,
        blank=True,
        help_text=_('"Ro\'yxatdan tanlash" turi uchun qiymatlar ro\'yxati'),
    )

    default_value = models.CharField(_('Standart qiymat'), max_length=200, blank=True)

    is_required = models.BooleanField(_('Majburiy'), default=False)

    #: Variantni ajratuvchi atributmi? (kiyimda o'lcham va rang — ha)
    is_variant_axis = models.BooleanField(
        _('Variant o\'qi'),
        default=False,
        help_text=_('Belgilansa, bu atribut bo\'yicha alohida variantlar hosil bo\'ladi'),
    )

    uniqueness = models.PositiveSmallIntegerField(
        _('Unikallik'),
        choices=Uniqueness.choices,
        default=Uniqueness.NONE,
    )

    position = models.PositiveSmallIntegerField(_('Tartib'), default=0)

    class Meta:
        verbose_name = _('Atribut ta\'rifi')
        verbose_name_plural = _('Atribut ta\'riflari')
        ordering = ['position', 'name']
        constraints = [
            models.UniqueConstraint(
                fields=['category', 'key'], name='unique_attribute_key_in_category'
            )
        ]

    def __str__(self):
        return f'{self.name} ({self.key})'

    def clean(self):
        super().clean()

        self.key = (self.key or '').strip()

        if not self.key.isidentifier():
            raise ValidationError({
                'key': _('Kalit lotin harfi bilan boshlanib, faqat harf, raqam '
                         'va pastki chiziqdan iborat bo\'lishi kerak')
            })

        if self.value_type == self.ValueType.CHOICE and not self.choices:
            raise ValidationError({
                'choices': _('"Ro\'yxatdan tanlash" turi uchun tanlovlar kerak')
            })

        if self.unit and self.value_type != self.ValueType.NUMBER:
            raise ValidationError({
                'unit': _('O\'lchov birligi faqat son atributlarga beriladi')
            })


class Product(TenantOwnedModel):
    """Mahsulot — nomenklatura birligi (model darajasi).

    Qoldiq mahsulotda emas, uning **variantlarida** hisoblanadi.
    Bir variantli mahsulot ham variantga ega — u avtomatik yaratiladi.
    """

    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name='products',
        verbose_name=_('Kategoriya'),
    )

    name = models.CharField(_('Nomi'), max_length=250)
    brand = models.CharField(_('Brend'), max_length=100, blank=True)
    model = models.CharField(_('Model'), max_length=100, blank=True)

    description = models.TextField(_('Tavsif'), blank=True)

    #: Qoldiq va narx shu birlikda yuritiladi. Bo'sh bo'lsa kategoriyaning
    #: standart birligi olinadi.
    base_unit = models.CharField(
        _('Asosiy birlik'),
        max_length=30,
        blank=True,
        help_text=_('Qoldiq shu birlikda hisoblanadi. Masalan: kg, dona, m2'),
    )

    is_active = models.BooleanField(_('Faol'), default=True)

    class Meta:
        verbose_name = _('Mahsulot')
        verbose_name_plural = _('Mahsulotlar')
        ordering = ['name']
        indexes = [models.Index(fields=['tenant', 'category'])]

    def __str__(self):
        return self.name

    @property
    def effective_unit(self) -> str:
        """Asosiy birlik; berilmagan bo'lsa kategoriyadan meros olinadi."""
        if self.base_unit:
            return self.base_unit

        for category in self.category.ancestors().order_by('-path'):
            if category.default_unit:
                return category.default_unit

        return ''


class Variant(TenantOwnedModel):
    """Mahsulotning aniq varianti — qoldiq va narx shu darajada.

    `attributes` — JSONB, har kalit `{"raw": "12 mm", "num": "0.012"}`
    ko'rinishida. `raw` foydalanuvchi kiritgani (ko'rsatish uchun),
    `num` bazaviy SI birlikka keltirilgan son (filtrlash uchun,
    `Decimal` aniqligini saqlash uchun **satr sifatida**).

    Bu juftlik g'oyasi InvenTree ning `data` / `data_numeric`
    ustunlaridan (common/models.py:2810), lekin u yerda EAV jadval,
    bizda JSONB.
    """

    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name='variants',
        verbose_name=_('Mahsulot'),
    )

    sku = models.CharField(_('SKU'), max_length=50)

    #: Variantni ajratuvchi qisqa nom: "XL / Qora". Bitta variantli
    #: mahsulotda bo'sh bo'ladi.
    name = models.CharField(_('Variant nomi'), max_length=150, blank=True)

    attributes = models.JSONField(_('Atributlar'), default=dict, blank=True)

    purchase_price = MoneyField(_('Kirim narxi'), null=True, blank=True)
    sale_price = MoneyField(_('Sotuv narxi'), null=True, blank=True)
    currency = models.CharField(_('Valyuta'), max_length=3, default='UZS')

    min_stock = QuantityField(
        _('Minimal qoldiq'),
        positive=True,
        null=True,
        blank=True,
        help_text=_('Shundan kam qolganda ogohlantiriladi'),
    )

    is_active = models.BooleanField(_('Faol'), default=True)

    class Meta:
        verbose_name = _('Variant')
        verbose_name_plural = _('Variantlar')
        ordering = ['product__name', 'sku']
        constraints = [
            models.UniqueConstraint(fields=['tenant', 'sku'], name='unique_tenant_sku')
        ]
        indexes = [
            models.Index(fields=['tenant', 'product']),
            # JSONB atributlari bo'yicha qidiruv uchun GIN indeksi
            # migratsiyada qo'lda qo'shiladi (Django `jsonb_path_ops` ni
            # bermaydi) — 0002 migratsiyasiga qarang.
        ]

    def __str__(self):
        label = f'{self.product.name}'
        return f'{label} — {self.name}' if self.name else label

    @property
    def display_name(self) -> str:
        return str(self)

    def attribute_value(self, key: str):
        """Atributning ko'rsatish uchun mo'ljallangan xom qiymati."""
        entry = (self.attributes or {}).get(key)

        if isinstance(entry, dict):
            return entry.get('raw')

        return entry


class ProductUnit(TenantOwnedModel):
    """Mahsulotga xos o'ram konversiyasi: "1 qop = 50 kg".

    **Nega global `pint` registrida emas.** Konversiya mahsulotga
    bog'liq: sement qopi 50 kg, gips qopi 30 kg, quruq aralashma 25 kg.
    Registr esa butun tashkilot uchun bitta. Shuning uchun `qop`
    registrda o'lchovsiz sanoq birligi bo'lib qoladi, og'irlikka
    bog'lanish esa shu jadvalda.

    InvenTree buni `SupplierPart.pack_quantity` orqali qiladi, ya'ni
    o'ramni **yetkazib beruvchiga** bog'laydi. Bizda u mahsulotning o'z
    xususiyati va bir nechta bo'la oladi: qop, palet, tonna.
    """

    variant = models.ForeignKey(
        Variant,
        on_delete=models.CASCADE,
        related_name='units',
        verbose_name=_('Variant'),
    )

    unit = models.CharField(
        _('Birlik'),
        max_length=30,
        help_text=_('Registrdagi birlik nomi. Masalan: qop, palet'),
    )

    factor_to_base = FactorField(
        _('Asosiy birlikka koeffitsient'),
        help_text=_('1 birlik necha asosiy birlikka teng. Masalan qop uchun 50'),
    )

    is_default_purchase = models.BooleanField(_('Kirimda standart'), default=False)
    is_default_sale = models.BooleanField(_('Sotuvda standart'), default=False)

    class Meta:
        verbose_name = _('O\'ram birligi')
        verbose_name_plural = _('O\'ram birliklari')
        ordering = ['unit']
        constraints = [
            models.UniqueConstraint(
                fields=['variant', 'unit'], name='unique_variant_unit'
            )
        ]

    def __str__(self):
        return f'{self.unit} = {self.factor_to_base}'

    def to_base(self, quantity):
        """Berilgan miqdorni asosiy birlikka o'giradi."""
        return quantity * self.factor_to_base

    def from_base(self, quantity):
        """Asosiy birlikdagi miqdorni shu o'ramga o'giradi."""
        return quantity / self.factor_to_base


class Barcode(TenantOwnedModel):
    """Variantga biriktirilgan shtrix-kod. Bir variantga bir nechta.

    `code` — xom qiymat (ko'rsatish uchun), `code_normalized` —
    qidiruv kaliti. Ikkalasini saqlash g'oyasi InvenTree ning
    `barcode_data` / `barcode_hash` juftligidan (InvenTree/models.py:1519),
    lekin u yerda bu **modeldagi ikki ustun**, ya'ni bir obyektga bitta
    kod. Bizda alohida jadval.

    InvenTree hashni xom qiymatdan hisoblaydi, ya'ni `" 12345 "` va
    `"12345"` turli kod bo'lib qoladi. Bizda avval normalizatsiya.
    """

    class CodeType(models.TextChoices):
        EAN13 = 'ean13', 'EAN-13'
        EAN8 = 'ean8', 'EAN-8'
        CODE128 = 'code128', 'Code 128'
        INTERNAL = 'internal', _('Ichki kod')
        OTHER = 'other', _('Boshqa')

    variant = models.ForeignKey(
        Variant,
        on_delete=models.CASCADE,
        related_name='barcodes',
        verbose_name=_('Variant'),
    )

    code = models.CharField(_('Kod'), max_length=100)

    code_normalized = models.CharField(
        _('Normallashtirilgan kod'),
        max_length=100,
        editable=False,
        db_index=True,
    )

    code_type = models.CharField(
        _('Turi'),
        max_length=20,
        choices=CodeType.choices,
        default=CodeType.OTHER,
    )

    class Meta:
        verbose_name = _('Shtrix-kod')
        verbose_name_plural = _('Shtrix-kodlar')
        constraints = [
            models.UniqueConstraint(
                fields=['tenant', 'code_normalized'], name='unique_tenant_barcode'
            )
        ]

    def __str__(self):
        return self.code

    @staticmethod
    def normalize(code: str) -> str:
        """Qidiruv uchun kalit: bo'shliqsiz, katta harfda.

        Skaner ba'zan boshida yoki oxirida bo'shliq qo'shadi, ba'zi
        kodlarda esa kichik harf bo'ladi. Normalizatsiyasiz bir xil
        tovar ikki marta ro'yxatga tushadi.
        """
        return ''.join((code or '').split()).upper()

    def save(self, *args, **kwargs):
        self.code = (self.code or '').strip()
        self.code_normalized = self.normalize(self.code)

        super().save(*args, **kwargs)

    def clean(self):
        super().clean()

        if not self.normalize(self.code):
            raise ValidationError({'code': _('Kod bo\'sh bo\'lishi mumkin emas')})
