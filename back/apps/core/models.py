"""Umumiy modellar: vaqt belgilari va do'kon sozlamalari."""

from decimal import Decimal

from django.db import models
from django.utils.translation import gettext_lazy as _


class TimeStampedModel(models.Model):
    """Yaratilgan va o'zgartirilgan vaqtni saqlaydigan asos."""

    created_at = models.DateTimeField(_('Yaratilgan'), auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(_('O‘zgartirilgan'), auto_now=True)

    class Meta:
        abstract = True


class ShopSettings(TimeStampedModel):
    """Do'kon sozlamalari — bazada bitta qator.

    Chek va yorliqda chiqadigan nom, yorliq o'lchami va kassirga ruxsat
    etilgan eng katta chegirma shu yerda.
    """

    shop_name = models.CharField(_('Do‘kon nomi'), max_length=120, default='Do‘kon')

    label_width_mm = models.PositiveSmallIntegerField(_('Yorliq eni, mm'), default=40)
    label_height_mm = models.PositiveSmallIntegerField(_('Yorliq bo‘yi, mm'), default=30)

    max_discount_percent = models.DecimalField(
        _('Kassir bera oladigan eng katta chegirma, %'),
        max_digits=5,
        decimal_places=2,
        default=Decimal('10.00'),
    )

    class Meta:
        verbose_name = _('Do‘kon sozlamalari')
        verbose_name_plural = _('Do‘kon sozlamalari')

    def __str__(self):
        return self.shop_name

    def save(self, *args, **kwargs):
        """Sozlama har doim bitta qator bo'lib qoladi."""
        self.pk = 1
        super().save(*args, **kwargs)

    @classmethod
    def load(cls):
        """Sozlamalarni qaytaradi; hali yo'q bo'lsa, standart qiymatlar bilan yaratadi."""
        settings, _created = cls.objects.get_or_create(pk=1)
        return settings
