"""Foydalanuvchi modeli.

**Diqqat:** bu modelda `role` maydoni yo'q va bo'lmasligi ham kerak.
Rol tashkilot kesimida saqlanadi — `apps.tenants.Membership` ga qarang.
Bir foydalanuvchi A tashkilotda direktor, B tashkilotda omborchi
bo'lishi mumkin, shuning uchun rol foydalanuvchining xususiyati emas.
"""

from __future__ import annotations

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _


class User(AbstractUser):
    """Loyihaning maxsus foydalanuvchi modeli."""

    phone = models.CharField(_('Telefon'), max_length=20, blank=True)

    class Meta:
        verbose_name = _('Foydalanuvchi')
        verbose_name_plural = _('Foydalanuvchilar')

    def __str__(self):
        return self.get_full_name() or self.username

    def membership_for(self, tenant_id):
        """Berilgan tashkilotdagi faol a'zolikni qaytaradi (yoki None)."""
        if tenant_id is None:
            return None

        return self.memberships.filter(
            tenant_id=tenant_id, is_active=True, tenant__is_active=True
        ).first()
