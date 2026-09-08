"""Kontragentlar: yetkazib beruvchilar va mijozlar.

Dizayn prototipidagi `seedCounterparty` maydonlariga mos
(`store/script.js:2479`), ustiga tenant qo'shilgan.

Bitta model ikkala rol uchun: dizayndagidek `type` maydoni bilan emas,
**ikkita bayroq** bilan. Sabab: amalda bir tashkilot ham yetkazib
beruvchi, ham mijoz bo'lishi mumkin (masalan qurilish firmasi sizdan
sement oladi, sizga esa g'isht sotadi). `type` maydoni bunga imkon
bermasdi.
"""

from __future__ import annotations

from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.models import TenantOwnedModel


class Partner(TenantOwnedModel):
    """Yetkazib beruvchi yoki mijoz."""

    name = models.CharField(_('Nomi'), max_length=200)

    is_supplier = models.BooleanField(_('Yetkazib beruvchi'), default=False)
    is_customer = models.BooleanField(_('Mijoz'), default=False)

    inn = models.CharField(_('INN'), max_length=20, blank=True)
    phone = models.CharField(_('Telefon'), max_length=30, blank=True)
    email = models.EmailField(_('Email'), blank=True)
    contact = models.CharField(_('Aloqa shaxsi'), max_length=150, blank=True)
    address = models.CharField(_('Manzil'), max_length=300, blank=True)
    bank = models.CharField(_('Bank rekvizitlari'), max_length=250, blank=True)

    note = models.TextField(_('Izoh'), blank=True)
    is_active = models.BooleanField(_('Faol'), default=True)

    class Meta:
        verbose_name = _('Kontragent')
        verbose_name_plural = _('Kontragentlar')
        ordering = ['name']
        indexes = [
            models.Index(fields=['tenant', 'is_supplier']),
            models.Index(fields=['tenant', 'is_customer']),
        ]

    def __str__(self):
        return self.name

    @property
    def role_display(self) -> str:
        roles = []

        if self.is_supplier:
            roles.append(str(_('Yetkazib beruvchi')))

        if self.is_customer:
            roles.append(str(_('Mijoz')))

        return ' / '.join(roles) or str(_('Belgilanmagan'))
