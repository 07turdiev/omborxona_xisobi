"""Pul maydoni.

Butun loyihada pul faqat shu maydon orqali saqlanadi: valyuta bitta (UZS),
`float` hech qayerda ishlatilmaydi.
"""

from django.db import models

MONEY_MAX_DIGITS = 14
MONEY_DECIMAL_PLACES = 2


class MoneyField(models.DecimalField):
    """Summa — `Decimal(14, 2)`, ya'ni tiyingacha aniq."""

    def __init__(self, *args, **kwargs):
        kwargs.setdefault('max_digits', MONEY_MAX_DIGITS)
        kwargs.setdefault('decimal_places', MONEY_DECIMAL_PLACES)
        super().__init__(*args, **kwargs)
