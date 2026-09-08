"""Tashkilotning o'z o'lchov birliklari.

Bu modulda InvenTree loyihasidan (MIT) olingan kod bor.
Manba: InvenTree 1.6.0 dev — common/models.py:1812-1857
Litsenziya va to'liq atribut: repo ildizidagi NOTICE faylida.
"""

from __future__ import annotations

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver
from django.utils.translation import gettext_lazy as _

from apps.core.models import TenantOwnedModel


class CustomUnit(TenantOwnedModel):
    """Tashkilot qo'shgan o'lchov birligi.

    `pint` sintaksisida ta'riflanadi, masalan:

        name='mashina', definition='6 * m3', symbol='msh'
        -> "mashina = 6 * m3 = msh"

    **InvenTree'dan farq:** u yerda `name` va `symbol` global unikal
    (`common/models.py:1861`). Bizda unikallik tashkilot ichida — aks holda
    bir mijoz "mashina" nomini band qilsa, boshqasi o'z ta'rifini yarata
    olmasdi.
    """

    name = models.CharField(
        _('Nomi'),
        max_length=50,
        help_text=_('Lotin harflari va pastki chiziq. Masalan: mashina, katta_qop'),
    )

    symbol = models.CharField(
        _('Belgisi'),
        max_length=10,
        blank=True,
        help_text=_('Qisqartma, ixtiyoriy. Masalan: msh'),
    )

    definition = models.CharField(
        _('Ta\'rifi'),
        max_length=100,
        help_text=_('Mavjud birliklar orqali. Masalan: 6 * m3'),
    )

    description = models.CharField(_('Izoh'), max_length=250, blank=True)

    class Meta:
        verbose_name = _('O\'lchov birligi')
        verbose_name_plural = _('O\'lchov birliklari')
        ordering = ['name']
        constraints = [
            models.UniqueConstraint(
                fields=['tenant', 'name'], name='unique_tenant_unit_name'
            ),
            models.UniqueConstraint(
                fields=['tenant', 'symbol'],
                condition=~models.Q(symbol=''),
                name='unique_tenant_unit_symbol',
            ),
        ]

    def __str__(self):
        return f'{self.name} ({self.symbol})' if self.symbol else self.name

    @property
    def definition_string(self) -> str:
        """`pint` uchun to'liq ta'rif satri: "nom = ta'rif = belgi".

        Manba: InvenTree common/models.py:1812-1819 (MIT, NOTICE ga qarang).
        """
        text = f'{self.name} = {self.definition}'

        if self.symbol:
            text += f' = {self.symbol}'

        return text

    def clean(self):
        """Ta'rifni saqlashdan oldin `pint` bilan sinab ko'radi.

        Manba g'oyasi: InvenTree common/models.py:1830-1857 (MIT).

        Uch bosqichli tekshiruv — ketma-ketlik muhim:
        1. `name` yaroqli identifikatormi (aks holda `pint` ta'rifni
           umuman ajrata olmaydi);
        2. `definition` ning o'zi alohida tushunarlimi;
        3. va faqat shundan keyin to'liq ta'rif registrga qo'shilib
           ko'riladi.

        Ikkinchi bosqichsiz xato xabari tushunarsiz bo'ladi: `pint`
        "mashina = 6 * qwerty" ni ajratolmaganda muammo `qwerty` da
        ekanini aytmaydi.
        """
        super().clean()

        from apps.units.registry import get_registry

        self.name = (self.name or '').strip()
        self.definition = (self.definition or '').strip()
        self.symbol = (self.symbol or '').strip()

        if not self.name.isidentifier():
            raise ValidationError({
                'name': _('Nom lotin harfi bilan boshlanib, faqat harf, raqam '
                          'va pastki chiziqdan iborat bo\'lishi kerak')
            })

        registry = get_registry(self.tenant_id)

        # Bu birlik allaqachon registrda bo'lsa (tahrirlash holati),
        # o'zining eski ta'rifi bilan to'qnashmasligi uchun tekshiruvni
        # toza registrda o'tkazamiz.
        if not self.definition:
            raise ValidationError({'definition': _('Ta\'rif kiritilmagan')})

        try:
            registry.Quantity(self.definition)
        except Exception as exc:
            raise ValidationError({'definition': _('Ta\'rifni tushunib bo\'lmadi: %(err)s')
                                   % {'err': exc}})

        try:
            registry.define(self.definition_string)
        except Exception as exc:
            raise ValidationError(_('Birlik ta\'rifi qabul qilinmadi: %(err)s')
                                  % {'err': exc})


@receiver(post_save, sender=CustomUnit, dispatch_uid='custom_unit_saved')
@receiver(post_delete, sender=CustomUnit, dispatch_uid='custom_unit_deleted')
def _invalidate_unit_registry(sender, instance, **kwargs):
    """Birlik o'zgarganda tashkilotning registrini bekor qiladi.

    Manba g'oyasi: InvenTree common/models.py:1881-1889 (MIT).
    Farq: InvenTree global registrni butunlay qayta yuklaydi, bizda
    faqat shu tashkilotning registri bekor qilinadi.
    """
    from apps.units.registry import invalidate_registry

    if instance.tenant_id:
        invalidate_registry(instance.tenant_id)
