"""Foydalanuvchi va uning roli."""

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _


class User(AbstractUser):
    """Do'kon xodimi.

    Ikkita rol bor. Administrator — hamma narsa; kassir — sotuv, qaytarish
    va tovarni ko'rish. Kassir tannarx, foyda, hisobot, ta'minotchi va
    xarajatlarni ko'ra olmaydi (tekshiruv API tomonda).
    """

    class Role(models.TextChoices):
        ADMIN = 'admin', _('Administrator')
        CASHIER = 'cashier', _('Kassir')

    role = models.CharField(
        _('Rol'),
        max_length=10,
        choices=Role.choices,
        default=Role.CASHIER,
    )

    phone = models.CharField(_('Telefon'), max_length=20, blank=True)

    class Meta:
        verbose_name = _('Xodim')
        verbose_name_plural = _('Xodimlar')
        ordering = ['username']

    def __str__(self):
        return self.get_full_name() or self.username

    @property
    def is_admin(self) -> bool:
        """Django superuser ham administrator hisoblanadi."""
        return self.is_superuser or self.role == self.Role.ADMIN
