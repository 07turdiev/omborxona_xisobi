"""Omborlar va ularga kirish huquqi.

Maydonlar StoreFlow dizayn prototipidagi ombor formasidan olingan
(`store/index.html`, `warehouseForm`), ustiga ikkita narsa qo'shilgan:

1. `purpose` — omborning **vazifasi** (asosiy / savdo nuqtasi / tranzit).
   Dizayndagi `type` tovar turini bildiradi (universal, elektronika,
   kiyim...), vazifani emas. Ikkalasi ham kerak: tovar turi faqat
   guruhlash uchun, vazifa esa **qoldiq mantiqiga ta'sir qiladi** —
   tranzitdagi tovar sotuvga chiqmaydi.

2. `tenant` — dizaynda ko'p tashkilot ko'rsatilmagan, biz qo'shamiz.
"""

from __future__ import annotations

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.fields import QuantityField
from apps.core.models import TenantOwnedModel


class Warehouse(TenantOwnedModel):
    """Ombor — tovar saqlanadigan fizik joy."""

    class GoodsType(models.TextChoices):
        """Omborda saqlanadigan tovar turi (dizayndagi `type`).

        Faqat guruhlash va filtrlash uchun; qoldiq mantiqiga ta'sir
        qilmaydi.
        """

        UNIVERSAL = 'universal', _('Universal')
        ELECTRONICS = 'electronics', _('Texnika')
        CLOTHING = 'clothing', _('Kiyim-kechak')
        FOOD = 'food', _('Oziq-ovqat')
        HOUSEHOLD = 'household', _('Maishiy mollar')
        CONSTRUCTION = 'construction', _('Qurilish mollari')

    class Purpose(models.TextChoices):
        """Omborning vazifasi — qoldiq mantiqiga ta'sir qiladi."""

        MAIN = 'main', _('Asosiy ombor')
        RETAIL = 'retail', _('Savdo nuqtasi')
        TRANSIT = 'transit', _('Tranzit')

    #: Qoldig'i sotuvga chiqadigan vazifalar. Tranzitdagi tovar
    #: omborlar orasida yo'lda — u hali hech kimniki emas va sotilmaydi.
    SELLABLE_PURPOSES = frozenset({Purpose.MAIN, Purpose.RETAIL})

    code = models.CharField(
        _('Kodi'),
        max_length=20,
        help_text=_('Qisqa belgi, hujjat raqamlarida ishlatiladi. Masalan: MARKAZ'),
    )

    name = models.CharField(_('Nomi'), max_length=150)

    goods_type = models.CharField(
        _('Tovar turi'),
        max_length=20,
        choices=GoodsType.choices,
        default=GoodsType.UNIVERSAL,
    )

    purpose = models.CharField(
        _('Vazifasi'),
        max_length=20,
        choices=Purpose.choices,
        default=Purpose.MAIN,
        help_text=_('Tranzit omboridagi tovar sotuvga chiqmaydi'),
    )

    manager = models.CharField(_('Mas\'ul shaxs'), max_length=150, blank=True)
    phone = models.CharField(_('Telefon'), max_length=30, blank=True)
    address = models.CharField(_('Manzil'), max_length=300, blank=True)

    area = QuantityField(
        _('Maydoni, m²'),
        positive=True,
        null=True,
        blank=True,
    )

    capacity = QuantityField(
        _('Sig\'imi'),
        positive=True,
        null=True,
        blank=True,
        help_text=_('Taxminiy sig\'im, birliklarda'),
    )

    temperature = models.CharField(
        _('Harorat rejimi'),
        max_length=50,
        blank=True,
        help_text=_('Masalan: +10°C / +25°C'),
    )

    notes = models.TextField(_('Izoh'), blank=True)

    is_active = models.BooleanField(_('Faol'), default=True)

    class Meta:
        verbose_name = _('Ombor')
        verbose_name_plural = _('Omborlar')
        ordering = ['name']
        constraints = [
            models.UniqueConstraint(
                fields=['tenant', 'code'], name='unique_tenant_warehouse_code'
            )
        ]

    def __str__(self):
        return f'{self.name} ({self.code})'

    @property
    def is_sellable(self) -> bool:
        """Bu ombordagi qoldiq sotuvga chiqadimi?"""
        return self.is_active and self.purpose in self.SELLABLE_PURPOSES


class WarehouseAccess(TenantOwnedModel):
    """Foydalanuvchining alohida omborga kirish huquqi.

    **Bu jadval ixtiyoriy cheklov.** Foydalanuvchi uchun bitta ham qator
    bo'lmasa — u tashkilotning **barcha** omborlarini va barcha
    hisobotlarini ko'radi. Aksariyat do'konlarda ombor soni oz va hamma
    hammasini ko'rishi kerak, shuning uchun standart holat ochiq.

    Qator paydo bo'lishi bilan cheklov kuchga kiradi: foydalanuvchi
    faqat o'ziga ochilgan omborlarni ko'radi.

    G'oya InvenTree'ning `StockLocation.owner` yechimidan olingan
    ("egasi yo'q -> ruxsat", `stock/models.py:284`), lekin u yerda
    mexanizm hech qachon API'da chaqirilmagan — faqat testlarda.
    Bizda `visible_to()` orqali queryset darajasida qo'llanadi.
    """

    class Level(models.TextChoices):
        VIEW = 'view', _('Ko\'rish')
        OPERATE = 'operate', _('Kirim-chiqim qilish')
        MANAGE = 'manage', _('To\'liq boshqarish')

    #: Ma'lumot o'zgartira oladigan darajalar
    WRITE_LEVELS = frozenset({Level.OPERATE, Level.MANAGE})

    warehouse = models.ForeignKey(
        Warehouse,
        on_delete=models.CASCADE,
        related_name='access_rules',
        verbose_name=_('Ombor'),
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='warehouse_access',
        verbose_name=_('Foydalanuvchi'),
    )

    level = models.CharField(
        _('Daraja'),
        max_length=20,
        choices=Level.choices,
        default=Level.VIEW,
    )

    class Meta:
        verbose_name = _('Omborga kirish')
        verbose_name_plural = _('Omborga kirish huquqlari')
        constraints = [
            models.UniqueConstraint(
                fields=['warehouse', 'user'], name='unique_warehouse_user_access'
            )
        ]
        indexes = [models.Index(fields=['user'])]

    def __str__(self):
        return f'{self.user} — {self.warehouse} ({self.get_level_display()})'

    @property
    def can_write(self) -> bool:
        return self.level in self.WRITE_LEVELS

    @classmethod
    def visible_to(cls, user, queryset=None):
        """Foydalanuvchi ko'ra oladigan omborlar querysetini qaytaradi.

        Cheklov yozilmagan bo'lsa — hammasi. Yozilgan bo'lsa — faqat
        ochilganlari.

        Diqqat: tashkilotlar orasidagi ajratishni bu metod qilmaydi,
        uni PostgreSQL RLS bajaradi. Bu yerda faqat tashkilot **ichidagi**
        cheklov.
        """
        queryset = Warehouse.objects.all() if queryset is None else queryset

        allowed = cls.objects.filter(user=user).values_list('warehouse_id', flat=True)

        if not allowed:
            return queryset

        return queryset.filter(pk__in=list(allowed))
