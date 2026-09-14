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

    # -- Rekvizitlar (hujjat va cheklarda chiqadi) ---------------------

    inn = models.CharField(_('INN'), max_length=20, blank=True)
    phone = models.CharField(_('Telefon'), max_length=30, blank=True)
    address = models.CharField(_('Manzil'), max_length=300, blank=True)

    # -- Hujjat raqamlari ----------------------------------------------
    #
    # Dizayndagi `importPrefix` / `salePrefix` sozlamalariga mos.
    # Prefiks o'zgarsa **eski hujjatlar o'z raqamini saqlaydi** — raqam
    # yaratilganda bir marta yoziladi va keyin tegilmaydi.

    purchase_prefix = models.CharField(_('Kirim prefiksi'), max_length=10, default='KIR')
    sale_prefix = models.CharField(_('Sotuv prefiksi'), max_length=10, default='SOT')
    transfer_prefix = models.CharField(
        _("Ko'chirish prefiksi"), max_length=10, default='KOCH'
    )

    # -- Ogohlantirish chegaralari -------------------------------------

    expiry_warning_days = models.PositiveSmallIntegerField(
        _('Yaroqlilik ogohlantirishi, kun'),
        default=30,
        help_text=_('Muddat tugashiga shuncha kun qolganda ogohlantiriladi'),
    )

    # -- Qarzga sotuv ----------------------------------------------------

    debt_prefix = models.CharField(_('Qarz prefiksi'), max_length=10, default='QRZ')

    debt_default_days = models.PositiveSmallIntegerField(
        _('Qarz muddati, kun'),
        default=30,
        help_text=_('Qarzga sotuvda to‘lov muddati ko‘rsatilmasa'),
    )

    credit_markup_default = models.DecimalField(
        _('Kredit ustamasi, %'),
        max_digits=6,
        decimal_places=2,
        default=0,
        help_text=_('Qarzga sotuv formasida oldindan to‘ldiriladi'),
    )

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
        SALESPERSON = 'salesperson', _('Sotuvchi / kassir')
        ACCOUNTANT = 'accountant', _('Buxgalter')
        VIEWER = 'viewer', _('Kuzatuvchi')

    #: Ma'lumot o'zgartira oladigan rollar. Kuzatuvchi bu yerda yo'q va
    #: unga qanday ruxsat berilmasin, u hech narsani o'zgartira olmaydi.
    WRITE_ROLES = frozenset({
        Role.OWNER, Role.MANAGER, Role.STOREKEEPER, Role.SALESPERSON, Role.ACCOUNTANT,
    })

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

    #: Xodimning alohida ruxsatlari (`apps.core.access.Perm` kodlari).
    #: `None` — roldagi standart ruxsatlar amal qiladi va rol o'zgarsa
    #: ular ham o'zgaradi. Ro'yxat berilsa — aynan shu ro'yxat, roldan
    #: qat'i nazar. Egasiga bu maydon ta'sir qilmaydi.
    permissions = models.JSONField(
        _('Ruxsatlar'),
        null=True,
        blank=True,
        help_text=_('Bo‘sh — rolning standart ruxsatlari'),
    )

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
        """Rol bo'yicha boshqaruvchimi (egasi yoki menejer)?

        Faqat ko'rsatish uchun. Ruxsat tekshiruvlari `has_perm()` orqali
        bo'ladi — xodimga alohida "sozlamalar" ruxsati berilishi mumkin.
        """
        return self.is_active and self.role in self.ADMIN_ROLES

    @property
    def uses_role_defaults(self) -> bool:
        """Ruxsatlar roldan olinadimi (alohida sozlanmaganmi)?"""
        return self.role == self.Role.OWNER or self.permissions is None

    @property
    def effective_permissions(self) -> frozenset[str]:
        """Amaldagi ruxsatlar to'plami."""
        from apps.core.access import ALL_PERMISSIONS, ROLE_DEFAULTS

        if not self.is_active:
            return frozenset()

        # Egasini hech kim, hatto o'zi ham, ruxsatsiz qoldira olmaydi
        if self.role == self.Role.OWNER:
            return ALL_PERMISSIONS

        if self.permissions is None:
            return ROLE_DEFAULTS.get(self.role, frozenset())

        return frozenset(self.permissions) & ALL_PERMISSIONS

    def has_perm(self, permission: str) -> bool:
        return permission in self.effective_permissions

    def has_any(self, permissions) -> bool:
        return bool(self.effective_permissions & set(permissions))

    def has_all(self, permissions) -> bool:
        return set(permissions) <= self.effective_permissions
