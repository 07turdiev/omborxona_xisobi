"""Xarajatlar — sof foydani hisoblash uchun."""

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.fields import MoneyField
from apps.core.models import TimeStampedModel


class Expense(TimeStampedModel):
    """Do'kon xarajati."""

    class Category(models.TextChoices):
        RENT = 'rent', _('Ijara')
        SALARY = 'salary', _('Ish haqi')
        UTILITIES = 'utilities', _('Kommunal')
        OTHER = 'other', _('Boshqa')

    date = models.DateField(_('Sanasi'))

    category = models.CharField(
        _('Turi'), max_length=15, choices=Category.choices, default=Category.OTHER
    )

    amount = MoneyField(_('Summa'))
    note = models.CharField(_('Izoh'), max_length=300, blank=True)

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='expenses',
        verbose_name=_('Kim kiritdi'),
    )

    class Meta:
        verbose_name = _('Xarajat')
        verbose_name_plural = _('Xarajatlar')
        ordering = ['-date', '-id']

    def __str__(self):
        return f'{self.get_category_display()}: {self.amount}'
