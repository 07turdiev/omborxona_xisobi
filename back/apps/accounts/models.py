"""Foydalanuvchi va uning roli."""

from django.contrib.auth.models import AbstractUser, UserManager
from django.db import models
from django.utils.translation import gettext_lazy as _


class ShopUserManager(UserManager):
    """`createsuperuser` administrator rolini beradi.

    Standart rol — kassir. Usiz serverda yaratilgan birinchi
    foydalanuvchi kassa interfeysini ko'rardi: `is_admin` unga ruxsat
    bersa ham, interfeys `role` ga qaraydi.
    """

    def create_superuser(self, *args, **kwargs):
        kwargs.setdefault('role', User.Role.ADMIN)

        return super().create_superuser(*args, **kwargs)


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

    objects = ShopUserManager()

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
