"""Loyihaning umumiy model maydonlari.

Bu modulda InvenTree loyihasidan (MIT) olingan kod bor.
Manba: InvenTree 1.6.0 dev — InvenTree/fields.py:231-244, 262-270
Litsenziya va to'liq atribut: repo ildizidagi NOTICE faylida.

Loyihaning 6-arxitektura qarori: pul `Decimal(18,2)`, miqdor `Decimal(18,3)`,
`float` hech qayerda ishlatilmaydi. Shu sababli quyidagi maydonlar
`float` qiymatni jimgina qabul qilmaydi — u xato sifatida ko'rinadi.
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation

from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

# Pul: Decimal(18, 2) — UZS uchun tiyin, USD uchun sent.
MONEY_MAX_DIGITS = 18
MONEY_DECIMAL_PLACES = 2

# Miqdor: Decimal(18, 3) — kg, m2, m3 uchun uch kasr yetarli.
QUANTITY_MAX_DIGITS = 18
QUANTITY_DECIMAL_PLACES = 3

# Konversiya koeffitsienti: Decimal(18, 6) — "1 qop = 0.05 tonna" kabi
# nisbatlar uchun uch kasr yetarli emas.
FACTOR_MAX_DIGITS = 18
FACTOR_DECIMAL_PLACES = 6


def round_decimal(value, places: int):
    """Qiymatni berilgan kasr xonasigacha yaxlitlaydi.

    Manba: InvenTree InvenTree/fields.py:231-244 (MIT, NOTICE ga qarang).

    InvenTree'dan farqi: u `float` ni ham qabul qiladi
    (`if type(value) in [Decimal, float]`). Bizda `float` maydonga umuman
    yetib kelmasligi kerak — kelsa bu xato va u ko'rinishi lozim, jimgina
    yaxlitlanmasligi kerak. Shuning uchun `float` bu yerda rad etiladi.
    """
    if value is None:
        return None

    if isinstance(value, float):
        raise ValidationError(
            _('float qiymat qabul qilinmaydi, Decimal ishlating') + f' ({value})'
        )

    if not isinstance(value, Decimal):
        return value

    try:
        return round(value, places)
    except (InvalidOperation, ValueError):
        raise ValidationError(_('Noto\'g\'ri o\'nlik qiymat') + f' ({value})')


class RoundingDecimalField(models.DecimalField):
    """Kiritilgan qiymatni maydon aniqligiga yaxlitlaydigan DecimalField.

    Manba g'oyasi: InvenTree InvenTree/fields.py:262-270 (MIT).

    Nega kerak: `Decimal(18,3)` maydoniga besh kasrli qiymat kelganda
    Django versiyasiga qarab yo `InvalidOperation` beradi, yo jimgina
    kesadi. Yaxlitlashni maydon darajasida qilish bu noaniqlikni yo'q
    qiladi va xatoni bashorat qilinadigan `ValidationError` ga aylantiradi.
    """

    def to_python(self, value):
        """Qiymatni python tipiga o'girib, maydon aniqligiga yaxlitlaydi."""
        return round_decimal(super().to_python(value), self.decimal_places)


class MoneyField(RoundingDecimalField):
    """Pul miqdori — Decimal(18, 2).

    Valyuta kodi alohida maydonda saqlanadi (`apps.pricing`), chunki bir
    yozuvda bir nechta valyutadagi summa bo'lishi mumkin va valyutani
    maydon ichiga yashirish keyin kurs tarixini bog'lashni qiyinlashtiradi.
    """

    def __init__(self, *args, **kwargs):
        kwargs.setdefault('max_digits', MONEY_MAX_DIGITS)
        kwargs.setdefault('decimal_places', MONEY_DECIMAL_PLACES)
        super().__init__(*args, **kwargs)


class QuantityField(RoundingDecimalField):
    """Tovar miqdori — Decimal(18, 3).

    Manfiy miqdorga ruxsat beriladi: `stock_movements` jurnalida chiqim
    manfiy son bilan yoziladi. Manfiylikni taqiqlash kerak bo'lgan joyda
    `positive=True` bering.
    """

    def __init__(self, *args, positive: bool = False, **kwargs):
        kwargs.setdefault('max_digits', QUANTITY_MAX_DIGITS)
        kwargs.setdefault('decimal_places', QUANTITY_DECIMAL_PLACES)

        self.positive = positive

        if positive:
            validators = list(kwargs.get('validators', []))
            validators.append(MinValueValidator(Decimal('0')))
            kwargs['validators'] = validators

        super().__init__(*args, **kwargs)

    def deconstruct(self):
        """Migratsiyalar uchun `positive` argumentini saqlab qoladi."""
        name, path, args, kwargs = super().deconstruct()

        if self.positive:
            kwargs['positive'] = True
            # `positive` validatorni o'zi qo'shadi, migratsiyada takrorlanmasin
            kwargs.pop('validators', None)

        return name, path, args, kwargs


class FactorField(RoundingDecimalField):
    """O'lchov birligi konversiya koeffitsienti — Decimal(18, 6).

    Masalan "1 qop = 50 kg" uchun `factor_to_base = 50.000000`.
    Nol yoki manfiy koeffitsient ma'nosiz, shuning uchun taqiqlangan.
    """

    def __init__(self, *args, **kwargs):
        kwargs.setdefault('max_digits', FACTOR_MAX_DIGITS)
        kwargs.setdefault('decimal_places', FACTOR_DECIMAL_PLACES)
        super().__init__(*args, **kwargs)

    def validate(self, value, model_instance):
        """Koeffitsient noldan katta ekanini tekshiradi."""
        super().validate(value, model_instance)

        if value is not None and value <= Decimal('0'):
            raise ValidationError(_('Koeffitsient noldan katta bo\'lishi kerak'))
