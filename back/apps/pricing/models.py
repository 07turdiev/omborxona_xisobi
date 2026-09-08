"""Valyuta, kurs tarixi va FIFO tannarx qatlamlari.

**Bu modul InvenTree'dan hech narsa olmaydi.** Sabab tahlil hisobotining
4.5-bo'limida: InvenTree tannarxni umuman hisoblamaydi. Uning
`PartPricing` modelidagi yigirmata maydon — `min`/`max` juftliklari,
ya'ni "bu mahsulot taxminan qanchaga tushadi" degan **oraliq**, BOM
kalkulyatsiyasi uchun. `FIFO`, `weighted_average`, `COGS` qidiruvi butun
kod bazasida bitta ham natija bermadi.

Chakana va ulgurji savdoda esa sotilgan tovarning tannarxi foyda
hisobotining asosi. Shuning uchun quyidagilar noldan loyihalandi.

Ikkita asosiy g'oya:

1. **Kurs tarixi.** `django-money` ning `Rate` jadvali faqat joriy
   kursni saqlaydi va har yangilanishda ustiga yozadi. Bizga esa
   "o'sha kuni kurs qancha edi" degan savolga javob kerak — aks holda
   eski hujjatlarni qayta hisoblaganda summalar o'zgarib ketadi.

2. **FIFO qatlamlari.** Har kirim o'z tannarxi bilan alohida qatlam
   hosil qiladi. Sotuvda qatlamlar eng eskisidan boshlab yechiladi va
   qaysi qatlamdan qancha olinganini `CostConsumption` yozib boradi —
   ya'ni har sotuvning tannarxini keyin ham tekshirish mumkin.
"""

from __future__ import annotations

from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.fields import FactorField, MoneyField, QuantityField
from apps.core.models import TenantOwnedModel


class Currency(TenantOwnedModel):
    """Tashkilot ishlatadigan valyuta."""

    code = models.CharField(_('Kodi'), max_length=3, help_text=_('UZS, USD, EUR'))
    name = models.CharField(_('Nomi'), max_length=60)
    symbol = models.CharField(_('Belgisi'), max_length=8, blank=True)

    #: Hisobotlar shu valyutada jamlanadi. Tashkilotda bitta bo'lishi kerak.
    is_base = models.BooleanField(_('Asosiy valyuta'), default=False)

    is_active = models.BooleanField(_('Faol'), default=True)

    class Meta:
        verbose_name = _('Valyuta')
        verbose_name_plural = _('Valyutalar')
        ordering = ['-is_base', 'code']
        constraints = [
            models.UniqueConstraint(
                fields=['tenant', 'code'], name='unique_tenant_currency'
            ),
            # Asosiy valyuta tashkilotda faqat bitta bo'lishi mumkin
            models.UniqueConstraint(
                fields=['tenant'],
                condition=models.Q(is_base=True),
                name='single_base_currency_per_tenant',
            ),
        ]

    def __str__(self):
        return self.code


class ExchangeRate(TenantOwnedModel):
    """Valyuta kursi va uning amal qilish sanasi.

    `rate` — 1 birlik valyuta necha asosiy valyutaga teng.
    Masalan USD uchun `12650.00` (1 USD = 12 650 so'm).

    Kurs **tarix bilan** saqlanadi: `valid_from` sanasidan boshlab amal
    qiladi va keyingi kurs paydo bo'lgunicha kuchda qoladi. Shuning
    uchun eski hujjatni qayta hisoblaganda o'sha kungi kurs olinadi va
    summalar o'zgarmaydi.
    """

    currency = models.ForeignKey(
        Currency,
        on_delete=models.CASCADE,
        related_name='rates',
        verbose_name=_('Valyuta'),
    )

    rate = FactorField(
        _('Kurs'),
        help_text=_('1 birlik valyuta necha asosiy valyutaga teng'),
    )

    valid_from = models.DateField(_('Amal qila boshlaydi'))

    source = models.CharField(
        _('Manba'),
        max_length=60,
        blank=True,
        help_text=_('Masalan: Markaziy bank, qo\'lda'),
    )

    class Meta:
        verbose_name = _('Valyuta kursi')
        verbose_name_plural = _('Valyuta kurslari')
        ordering = ['-valid_from']
        constraints = [
            models.UniqueConstraint(
                fields=['currency', 'valid_from'], name='unique_rate_per_day'
            )
        ]
        indexes = [models.Index(fields=['tenant', 'currency', '-valid_from'])]

    def __str__(self):
        return f'{self.currency.code} = {self.rate} ({self.valid_from})'


class CostLayer(TenantOwnedModel):
    """FIFO tannarx qatlami — bitta kirimning tannarxi va qoldig'i.

    Har kirim harakati bitta qatlam hosil qiladi. Sotuvda qatlamlar
    **eng eskisidan** boshlab yechiladi (FIFO), `quantity_remaining`
    kamayib boradi.

    Qatlam kesimi qoldiq kesimiga mos: variant × ombor × partiya.
    Ko'chirishda qatlam yangi omborga ko'chadi (tannarx tovar bilan
    birga yuradi), yangi qatlam hosil bo'lmaydi.
    """

    variant = models.ForeignKey(
        'catalog.Variant',
        on_delete=models.PROTECT,
        related_name='cost_layers',
        verbose_name=_('Variant'),
    )

    warehouse = models.ForeignKey(
        'warehouse.Warehouse',
        on_delete=models.PROTECT,
        related_name='cost_layers',
        verbose_name=_('Ombor'),
    )

    batch = models.ForeignKey(
        'stock.Batch',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='cost_layers',
        verbose_name=_('Partiya'),
    )

    #: Qatlamni hosil qilgan kirim yozuvi. Jurnal append-only bo'lgani
    #: uchun bu havola hech qachon "yetim" qolmaydi.
    #:
    #: Bir-ko'pga, `OneToOne` emas: xaridda bitta harakat bitta qatlam
    #: beradi, lekin ko'chirishda bitta qabul harakati manba ombordagi
    #: bir nechta qatlamni ko'chirishi mumkin — har biri o'z tannarxi
    #: bilan alohida qatlam bo'lib qoladi.
    movement = models.ForeignKey(
        'stock.StockMovement',
        on_delete=models.PROTECT,
        related_name='cost_layers',
        verbose_name=_('Manba harakati'),
    )

    quantity_initial = QuantityField(_('Boshlang\'ich miqdor'), positive=True)
    quantity_remaining = QuantityField(_('Qolgan miqdor'), positive=True)

    #: Hujjatdagi valyutadagi tannarx
    unit_cost = MoneyField(_('Birlik tannarxi'))
    currency = models.CharField(_('Valyuta'), max_length=3)

    #: Asosiy valyutaga keltirilgan tannarx.
    #:
    #: Kirim paytidagi kurs bo'yicha bir marta hisoblanadi va **keyin
    #: o'zgarmaydi**. Aks holda kurs o'zgarganda eski sotuvlarning
    #: foydasi o'z-o'zidan qayta hisoblanib ketardi.
    unit_cost_base = MoneyField(_('Tannarx (asosiy valyutada)'))

    #: Kirim paytida qo'llangan kurs — tekshirish uchun saqlanadi
    exchange_rate = FactorField(_('Kurs'), default=1)

    acquired_at = models.DateTimeField(_('Kirim vaqti'))

    class Meta:
        verbose_name = _('Tannarx qatlami')
        verbose_name_plural = _('Tannarx qatlamlari')
        # FIFO tartibi: eng eski qatlam birinchi
        ordering = ['acquired_at', 'id']
        indexes = [
            models.Index(
                fields=['tenant', 'variant', 'warehouse', 'batch', 'acquired_at'],
                name='cost_layer_fifo_idx',
            ),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(quantity_remaining__lte=models.F('quantity_initial')),
                name='layer_remaining_not_over_initial',
            )
        ]

    def __str__(self):
        return f'{self.variant} @ {self.unit_cost_base} ({self.quantity_remaining})'

    @property
    def is_depleted(self) -> bool:
        return self.quantity_remaining <= 0


class CostConsumption(TenantOwnedModel):
    """Sotuvda qaysi qatlamdan qancha olingani.

    Bu jadval bo'lmasa "shu chekning tannarxi nega shuncha?" degan
    savolga javob bo'lmaydi. Har chiqim harakati bir nechta qatlamni
    yechishi mumkin (partiya tugab, keyingisiga o'tganda), shuning
    uchun bog'lanish ko'p-ko'pga.

    Jurnal kabi bu ham **faqat qo'shiladi**: yozuv o'zgartirilmaydi,
    tuzatish teskari harakat orqali bo'ladi.
    """

    movement = models.ForeignKey(
        'stock.StockMovement',
        on_delete=models.PROTECT,
        related_name='cost_consumptions',
        verbose_name=_('Chiqim harakati'),
    )

    layer = models.ForeignKey(
        CostLayer,
        on_delete=models.PROTECT,
        related_name='consumptions',
        verbose_name=_('Qatlam'),
    )

    quantity = QuantityField(_('Miqdor'), positive=True)

    #: Qatlamdagi tannarx nusxasi — qatlam keyin o'zgarsa ham hisobot
    #: o'zgarmasligi uchun
    unit_cost_base = MoneyField(_('Birlik tannarxi (asosiy valyutada)'))

    class Meta:
        verbose_name = _('Tannarx sarfi')
        verbose_name_plural = _('Tannarx sarflari')
        ordering = ['id']
        indexes = [models.Index(fields=['tenant', 'movement'])]

    def __str__(self):
        return f'{self.quantity} × {self.unit_cost_base}'

    @property
    def total_cost(self):
        return self.quantity * self.unit_cost_base
