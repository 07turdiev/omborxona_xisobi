from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """Loyihaning maxsus foydalanuvchi modeli."""

    class Role(models.TextChoices):
        ADMIN = "admin", "Administrator"
        MANAGER = "manager", "Menejer"
        STOREKEEPER = "storekeeper", "Omborchi"

    role = models.CharField(
        "Rol", max_length=20, choices=Role.choices, default=Role.STOREKEEPER
    )
    phone = models.CharField("Telefon", max_length=20, blank=True)

    class Meta:
        verbose_name = "Foydalanuvchi"
        verbose_name_plural = "Foydalanuvchilar"

    def __str__(self):
        return self.get_full_name() or self.username
