"""Qoldiq: faqat qo'shiladigan harakat jurnali va undan hosila kesh.

Loyihaning 3-arxitektura qarori: **hech qachon o'zgaruvchan `quantity`
ustuni emas.** `StockMovement` — append-only jurnal, u haqiqat manbai.
`StockBalance` — tezlik uchun kesh, uni istalgan paytda jurnaldan
qayta hisoblash mumkin (`rebuild_balance()`).

Dizayn prototipi (`store/`) buni teskari qiladi: qoldiq mahsulotdagi
`stockByWarehouse` obyektida saqlanadi, kirim va sotuv esa shunchaki
tarix. Unda jurnalni o'chirsangiz qoldiq o'zgarmaydi; bizda esa jurnal
— yagona haqiqat.

InvenTree ham mutable `StockItem.quantity` ishlatadi, lekin uning
mualliflari o'zgarmas jurnalga qarab ketyapti — `order/models.py:4247`
dagi izohga qarang.

Qoldiq kesimi: **variant × ombor × partiya**. Partiya (`Batch`) shu
yerda o'lchov sifatida turadi, chunki yaroqlilik muddati ham, FIFO ham
uni talab qiladi. Partiyasiz tovar uchun `batch = NULL`.
"""

from __future__ import annotations

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.core.fields import MoneyField, QuantityField
from apps.core.models import TenantOwnedModel
from apps.stock.enums import MovementReason


class Batch(TenantOwnedModel):
    """Tovar partiyasi — bir yetkazmada kelgan bir xil tovar.

    Nima uchun kerak: bir xil mahsulotning ikki yetkazmasi turli kirim
    narxiga, turli yaroqlilik muddatiga va turli sifatga ega bo'ladi.
    FIFO tannarx ham, muddati o'tgan tovarni ushlash ham partiyasiz
    ishlamaydi.

    Qurilish mollarida bu ixtiyoriy emas: sement 3-6 oy, quruq
    aralashmalar 6-12 oy saqlanadi.
    """

    variant = models.ForeignKey(
        'catalog.Variant',
        on_delete=models.PROTECT,
        related_name='batches',
        verbose_name=_('Variant'),
    )

    code = models.CharField(
        _('Partiya kodi'),
        max_length=60,
        help_text=_('Yetkazib beruvchi hujjatidagi partiya raqami'),
    )

    expiry_date = models.DateField(_('Yaroqlilik muddati'), null=True, blank=True)
    produced_at = models.DateField(_('Ishlab chiqarilgan sana'), null=True, blank=True)

    note = models.CharField(_('Izoh'), max_length=250, blank=True)

    class Meta:
        verbose_name = _('Partiya')
        verbose_name_plural = _('Partiyalar')
        ordering = ['expiry_date', 'code']
        constraints = [
            models.UniqueConstraint(
                fields=['tenant', 'variant', 'code'], name='unique_variant_batch_code'
            )
        ]
        indexes = [models.Index(fields=['tenant', 'expiry_date'])]

    def __str__(self):
        return self.code

    @property
    def is_expired(self) -> bool:
        """Muddati o'tganmi?"""
        return bool(self.expiry_date and self.expiry_date < timezone.localdate())

    def days_left(self) -> int | None:
        """Muddat tugashiga necha kun qoldi; muddat yo'q bo'lsa `None`."""
        if not self.expiry_date:
            return None

        return (self.expiry_date - timezone.localdate()).days

    def is_stale(self, threshold_days: int = 30) -> bool:
        """Muddati yaqinlashib qolganmi?

        G'oyasi InvenTree ning `StockItem.is_stale()` metodidan
        (stock/models.py:1419), lekin u yerda chegara global sozlamada,
        bizda esa chaqiruvchi beradi.
        """
        left = self.days_left()

        return left is not None and 0 <= left <= threshold_days


class StockMovement(TenantOwnedModel):
    """Qoldiq harakati — faqat qo'shiladigan jurnal yozuvi.

    **O'zgartirib va o'chirib bo'lmaydi.** Bu ikki qatlamda qotirilgan:
    model darajasida (`save()` va `delete()` xato beradi) va baza
    darajasida (migratsiyadagi trigger). Ikkinchisi asosiy — ORM ni
    chetlab o'tgan xom SQL ham to'xtatiladi.

    Xato yozuvni tuzatish uchun **teskari yozuv** qo'shiladi, o'chirish
    emas. Shunda tarix to'liq qoladi va "kim, qachon, nima uchun
    tuzatgan" savoliga javob bo'ladi.
    """

    variant = models.ForeignKey(
        'catalog.Variant',
        on_delete=models.PROTECT,
        related_name='movements',
        verbose_name=_('Variant'),
    )

    warehouse = models.ForeignKey(
        'warehouse.Warehouse',
        on_delete=models.PROTECT,
        related_name='movements',
        verbose_name=_('Ombor'),
    )

    batch = models.ForeignKey(
        Batch,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='movements',
        verbose_name=_('Partiya'),
    )

    #: Ishorali miqdor: musbat — kirim, manfiy — chiqim.
    #: Ikki alohida ustun (`in`/`out`) o'rniga bittasi: yig'indi
    #: to'g'ridan-to'g'ri qoldiqni beradi va "ikkalasi ham to'ldirilgan"
    #: degan yaroqsiz holat umuman bo'lmaydi.
    quantity = QuantityField(_('Miqdor'))

    reason = models.CharField(
        _('Sababi'),
        max_length=30,
        choices=MovementReason.choices,
    )

    #: Kirimda birlik tannarxi. FIFO qatlamlari shundan quriladi.
    unit_cost = MoneyField(_('Birlik tannarxi'), null=True, blank=True)
    currency = models.CharField(_('Valyuta'), max_length=3, blank=True)

    #: Hujjatga havola. Hujjat modullari hali yozilmagani uchun
    #: FK emas, tur + ID juftligi. Bu bog'liqlikni ham kamaytiradi.
    document_type = models.CharField(_('Hujjat turi'), max_length=30, blank=True)
    document_id = models.PositiveBigIntegerField(_('Hujjat ID'), null=True, blank=True)

    #: Erkin qo'shimcha ma'lumot. G'oyasi InvenTree ning
    #: `StockItemTracking.deltas` maydonidan (stock/models.py:3796):
    #: yangi harakat turlarini sxemani o'zgartirmasdan qo'shish imkonini
    #: beradi. Farq: u yerda sonlar `float` sifatida yoziladi
    #: (stock/models.py:2373), bizda `str(Decimal)` — audit jurnalining
    #: o'zi yaxlitlash xatosi manbai bo'lmasligi kerak.
    meta = models.JSONField(_('Qo\'shimcha'), default=dict, blank=True)

    note = models.CharField(_('Izoh'), max_length=250, blank=True)

    occurred_at = models.DateTimeField(_('Sodir bo\'lgan vaqt'), default=timezone.now)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='stock_movements',
        verbose_name=_('Kim'),
    )

    class Meta:
        verbose_name = _('Qoldiq harakati')
        verbose_name_plural = _('Qoldiq harakatlari')
        ordering = ['-occurred_at', '-id']
        indexes = [
            # Qoldiqni qayta hisoblash uchun asosiy kesim
            models.Index(fields=['tenant', 'variant', 'warehouse', 'batch']),
            models.Index(fields=['tenant', 'occurred_at']),
            models.Index(fields=['tenant', 'document_type', 'document_id']),
        ]
        constraints = [
            models.CheckConstraint(
                condition=~models.Q(quantity=0),
                name='movement_quantity_not_zero',
            )
        ]

    def __str__(self):
        return f'{self.get_reason_display()}: {self.quantity}'

    @property
    def is_inbound(self) -> bool:
        return self.quantity > 0

    def save(self, *args, **kwargs):
        """Faqat yangi yozuvga ruxsat beradi."""
        if self.pk is not None:
            raise ValidationError(
                _('Qoldiq harakatini o\'zgartirib bo\'lmaydi. '
                  'Xatoni tuzatish uchun teskari yozuv qo\'shing.')
            )

        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError(
            _('Qoldiq harakatini o\'chirib bo\'lmaydi. '
              'Xatoni tuzatish uchun teskari yozuv qo\'shing.')
        )


class StockBalance(TenantOwnedModel):
    """Qoldiq keshi — jurnaldan hosila.

    Bu jadval **haqiqat manbai emas**: uni butunlay o'chirib, jurnaldan
    qayta qurish mumkin (`apps.stock.services.rebuild_balance`). Mavjud
    bo'lishining yagona sababi — tezlik: har "sotish mumkinmi?"
    tekshiruvida million qatorli jurnalni yig'ib bo'lmaydi.

    Kesh **jurnal yozuvi bilan bir tranzaksiyada** yangilanadi, fon
    vazifasida emas. Aks holda savdo eskirgan ma'lumot ustida ishlaydi.
    """

    variant = models.ForeignKey(
        'catalog.Variant',
        on_delete=models.PROTECT,
        related_name='balances',
        verbose_name=_('Variant'),
    )

    warehouse = models.ForeignKey(
        'warehouse.Warehouse',
        on_delete=models.PROTECT,
        related_name='balances',
        verbose_name=_('Ombor'),
    )

    batch = models.ForeignKey(
        Batch,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='balances',
        verbose_name=_('Partiya'),
    )

    quantity = QuantityField(_('Qoldiq'), default=0)

    #: Buyurtmaga band qilingan miqdor.
    #:
    #: Nima uchun alohida ustun: omborda 100 qop sement bor, lekin 80
    #: tasi ertaga jo'natiladigan buyurtmaga band. Sotuvchiga "100 bor"
    #: deyish xato bo'ladi. InvenTree bu farqni har so'rovda
    #: annotatsiya bilan hisoblaydi (part/filters.py:465), bizda esa
    #: materiallashgan ustun — kassada har chek uchun agregatsiya
    #: qilib bo'lmaydi.
    reserved_quantity = QuantityField(_('Band qilingan'), positive=True, default=0)

    last_movement = models.ForeignKey(
        StockMovement,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='+',
        verbose_name=_('Oxirgi harakat'),
    )

    class Meta:
        verbose_name = _('Qoldiq')
        verbose_name_plural = _('Qoldiqlar')
        ordering = ['variant__product__name', 'warehouse__name']
        constraints = [
            models.UniqueConstraint(
                fields=['tenant', 'variant', 'warehouse', 'batch'],
                name='unique_stock_balance',
                # PostgreSQL 15+ : NULL partiyalar ham bir xil deb
                # hisoblanadi. Busiz partiyasiz tovar uchun cheksiz
                # dublikat qator hosil bo'lardi.
                nulls_distinct=False,
            )
        ]
        indexes = [
            models.Index(fields=['tenant', 'variant']),
            models.Index(fields=['tenant', 'warehouse']),
        ]

    def __str__(self):
        return f'{self.variant} @ {self.warehouse}: {self.quantity}'

    @property
    def available_quantity(self):
        """Sotish mumkin bo'lgan miqdor.

        `Greatest(..., 0)` mantiqi InvenTree dan (part/filters.py:472):
        ortiqcha band qilingan holatda manfiy son ko'rsatilmaydi.
        Ortiqcha band qilish faktining o'zi `is_overallocated` orqali
        alohida ko'rinadi — u miqdorga yashirilmaydi.
        """
        return max(self.quantity - self.reserved_quantity, 0)

    @property
    def is_overallocated(self) -> bool:
        return self.reserved_quantity > self.quantity

    @property
    def is_sellable(self) -> bool:
        """Bu qoldiq sotuvga chiqadimi?

        Tranzit ombordagi tovar yo'lda — u hali hech kimniki emas.
        Muddati o'tgan partiya ham sotilmaydi.
        """
        if not self.warehouse.is_sellable:
            return False

        if self.batch and self.batch.is_expired:
            return False

        return self.available_quantity > 0
