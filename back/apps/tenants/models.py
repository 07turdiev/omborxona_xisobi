"""Tashkilotlar (tenant) va ularga a'zolik.

**Bu ikki jadvalda RLS YO'Q — bu ataylab qilingan.**

Sabab: tenant kontekstini o'rnatish uchun avval "bu foydalanuvchi qaysi
tashkilotlarga a'zo?" degan savolga javob kerak. Agar `Membership` ning
o'zi RLS bilan himoyalangan bo'lsa, kontekst o'rnatilmaguncha u bo'sh
qaytadi, kontekst esa shu jadvalsiz o'rnatilmaydi — o'zaro bog'liq halqa.

Shuning uchun bu ikkisi "bootstrap" jadvallari: ular `user` bo'yicha
filtrlanadi, `tenant_id` bo'yicha emas. API darajasida foydalanuvchi
faqat o'z a'zoliklarini ko'radi. Qolgan barcha jadvallar
`apps.core.models.TenantOwnedModel` dan meros oladi va RLS bilan
himoyalanadi.
"""

from __future__ import annotations

import uuid

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.models import TimeStampedModel


class Tenant(TimeStampedModel):
    """Tizimdan foydalanuvchi tashkilot (do'kon, savdo shoxobchasi).

    `id` — UUID: tenant identifikatori URL va sarlavhalarda ochiq yuradi
    (`X-Tenant-Id`), ketma-ket son bo'lsa mijozlar sonini va bir-birining
    mavjudligini taxmin qilish mumkin bo'lardi.
    """

    class BusinessType(models.TextChoices):
        """Tashkilot faoliyat turi.

        Bu maydon huquqlarga ta'sir qilmaydi — u faqat yangi tashkilot
        yaratilganda qanday o'lchov birliklari, kategoriyalar va atributlar
        bilan to'ldirishni belgilaydi (seed ma'lumotlari).
        """

        CONSTRUCTION = 'construction', _('Qurilish mollari')
        CLOTHING = 'clothing', _('Kiyim-kechak')
        GROCERY = 'grocery', _('Oziq-ovqat')
        GENERAL = 'general', _('Aralash / boshqa')

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    name = models.CharField(_('Nomi'), max_length=200)

    slug = models.SlugField(
        _('Qisqa nomi'),
        max_length=60,
        unique=True,
        help_text=_('Lotin harflari, raqam va chiziqcha. Hisobotlarda ishlatiladi.'),
    )

    business_type = models.CharField(
        _('Faoliyat turi'),
        max_length=20,
        choices=BusinessType.choices,
        default=BusinessType.GENERAL,
        help_text=_('Boshlang\'ich o\'lchov birliklari va kategoriyalarni tanlash uchun'),
    )

    base_currency = models.CharField(
        _('Asosiy valyuta'),
        max_length=3,
        default='UZS',
        help_text=_('Hisobotlar shu valyutada jamlanadi'),
    )

    is_active = models.BooleanField(_('Faol'), default=True)

    class Meta:
        verbose_name = _('Tashkilot')
        verbose_name_plural = _('Tashkilotlar')
        ordering = ['name']

    def __str__(self):
        return self.name


class Membership(TimeStampedModel):
    """Foydalanuvchining tashkilotdagi a'zoligi va roli.

    Rol tashkilot kesimida saqlanadi, foydalanuvchida emas: bir odam A
    tashkilotda direktor, B tashkilotda omborchi bo'lishi mumkin.
    """

    class Role(models.TextChoices):
        """Tashkilot ichidagi rol.

        Ruxsatlar shu roldan kelib chiqadi. Ombor darajasidagi qo'shimcha
        cheklov `apps.warehouse.WarehouseAccess` orqali beriladi va u
        **ixtiyoriy**: cheklov yozilmagan bo'lsa, foydalanuvchi tashkilotning
        barcha omborlarini va barcha hisobotlarini ko'radi.
        """

        OWNER = 'owner', _('Egasi')
        MANAGER = 'manager', _('Menejer')
        STOREKEEPER = 'storekeeper', _('Omborchi')
        SALESPERSON = 'salesperson', _('Sotuvchi')
        VIEWER = 'viewer', _('Kuzatuvchi')

    #: Ma'lumot o'zgartira oladigan rollar
    WRITE_ROLES = frozenset({Role.OWNER, Role.MANAGER, Role.STOREKEEPER, Role.SALESPERSON})

    #: Tashkilot sozlamalarini boshqara oladigan rollar
    ADMIN_ROLES = frozenset({Role.OWNER, Role.MANAGER})

    tenant = models.ForeignKey(
        Tenant,
        on_delete=models.CASCADE,
        related_name='memberships',
        verbose_name=_('Tashkilot'),
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='memberships',
        verbose_name=_('Foydalanuvchi'),
    )

    role = models.CharField(
        _('Rol'),
        max_length=20,
        choices=Role.choices,
        default=Role.VIEWER,
    )

    is_active = models.BooleanField(_('Faol'), default=True)

    class Meta:
        verbose_name = _('A\'zolik')
        verbose_name_plural = _('A\'zoliklar')
        constraints = [
            models.UniqueConstraint(
                fields=['tenant', 'user'], name='unique_tenant_user_membership'
            )
        ]
        indexes = [
            models.Index(fields=['user', 'is_active']),
        ]

    def __str__(self):
        return f'{self.user} — {self.tenant} ({self.get_role_display()})'

    @property
    def can_write(self) -> bool:
        """Foydalanuvchi ma'lumot o'zgartira oladimi?"""
        return self.is_active and self.role in self.WRITE_ROLES

    @property
    def is_admin(self) -> bool:
        """Foydalanuvchi tashkilot sozlamalarini boshqara oladimi?"""
        return self.is_active and self.role in self.ADMIN_ROLES
