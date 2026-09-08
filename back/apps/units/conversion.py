"""Qiymatlarni o'lchov birligiga keltirish va tekshirish.

G'oyasi InvenTree'ning `InvenTree/conversion.py:212-320` funksiyasidan
olingan, lekin kodi ko'chirilmagan — sabab uch xil:

1. **`Decimal`.** InvenTree funksiyasining oxirgi uchdan biri `float` ga
   qurilgan (`conversion.py:307`). Bizda butun zanjir `Decimal` da qoladi.
2. **Muhandislik notatsiyasi olinmadi.** `1K2 -> 1.2K` — rezistor va
   kondensator qiymatlari uchun. Savdo domenida ma'nosiz.
3. **Imperial o'lchovlar olinmadi.** `6' -> 6 feet`, `6" -> 6 inches`.
   O'zbekiston metrik, va `"` belgisi o'zbek matnida qo'shtirnoq sifatida
   uchraydi — bu qoida foyda emas, xato manbai bo'lardi.

InvenTree'dan olingan g'oyalar (kod emas):

- **Urinishlar ro'yxati:** qiymatni bir necha talqinda sinab ko'rish va
  birinchi muvaffaqiyatlisini olish.
- **Birlikni oldindan tekshirish:** aks holda `pint` tushunarsiz
  `UndefinedUnitError` beradi.
- **O'lchovsiz qiymat maxsus ishlanadi:** foydalanuvchi `"12"` yozsa va
  atribut `mm` talab qilsa, bu `12 mm` deb qabul qilinadi. Amalda
  foydalanuvchilar birlikni kamdan-kam yozadi.
"""

from __future__ import annotations

import uuid
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from apps.units.registry import get_current_registry, get_registry


def _registry(tenant_id: uuid.UUID | None, registry=None):
    """Berilgan registr, tenant registri yoki joriy kontekst registri."""
    if registry is not None:
        return registry

    if tenant_id is not None:
        return get_registry(tenant_id)

    return get_current_registry()


def is_valid_unit(unit: str, *, tenant_id: uuid.UUID | None = None, registry=None) -> bool:
    """Birlik registrda mavjudligini tekshiradi."""
    unit = (unit or '').strip()

    if not unit:
        return False

    try:
        return unit in _registry(tenant_id, registry)
    except Exception:
        return False


def validate_unit(unit: str, *, tenant_id: uuid.UUID | None = None, registry=None) -> str:
    """Birlikni tekshiradi va normallashtirilgan holda qaytaradi."""
    unit = (unit or '').strip()

    if not unit:
        return ''

    if not is_valid_unit(unit, tenant_id=tenant_id, registry=registry):
        raise ValidationError(_('Noma\'lum o\'lchov birligi: %(unit)s') % {'unit': unit})

    return unit


def is_dimensionless(quantity) -> bool:
    """Miqdorning o'lchami yo'qmi (`3`, `3 dona`, `2 dozen`)?

    Diqqat: bu `3` va `3 dona` ni ajratmaydi — ikkalasi ham o'lchovsiz.
    Maqsad birlikni biriktirish uchun `is_bare_number()` ishlating.
    """
    return quantity.to_base_units().dimensionality == {}


def is_bare_number(quantity, registry) -> bool:
    """Miqdor birliksiz yozilganmi (`"12"`, lekin `"12 qop"` emas)?

    **Nega bu farq muhim.** InvenTree bu ikkisini ajratmaydi: uning
    `is_dimensionless()` funksiyasi (InvenTree/conversion.py:322) `3` ni
    ham, `3 dozen` ni ham o'lchovsiz deb hisoblaydi, va o'lchovsiz
    qiymatga maqsad birlikni shunchaki biriktiradi (`conversion.py:196`).

    Bizda bu jimgina xatoga olib kelardi: `"1 qop"` ni `kg` ga
    keltirganda natija `1 kg` bo'lib chiqadi — mutlaqo noto'g'ri, chunki
    bir qop sement 50 kg. Xato hech qanday xabar bermaydi, faqat
    qoldiqni buzadi.

    Shuning uchun maqsad birlik faqat **haqiqatan birliksiz** songa
    biriktiriladi. `"1 qop"` ni `kg` ga keltirish esa xato beradi —
    mahsulotga xos konversiya `apps.catalog.ProductUnit` orqali,
    aniq kontekstda bajarilishi kerak.
    """
    return quantity.units == registry.dimensionless


def convert_to_unit(
    value,
    unit: str | None = None,
    *,
    tenant_id: uuid.UUID | None = None,
    registry=None,
) -> Decimal:
    """Qiymatni berilgan birlikka keltirib, `Decimal` son qaytaradi.

    Arguments:
        value: foydalanuvchi kiritgan qiymat (`"12 mm"`, `"12"`, `Decimal("12")`)
        unit: maqsad birlik (`"mm"`). Berilmasa qiymat bazaviy SI birlikka
            keltiriladi.

    Returns:
        `Decimal` — `unit` berilgan bo'lsa o'sha birlikdagi son, aks holda
        bazaviy SI birlikdagi son.

    Raises:
        ValidationError: qiymat bo'sh, tushunarsiz, yoki berilgan birlikka
            keltirib bo'lmaydigan bo'lsa.

    Namunalar:
        convert_to_unit('12 mm', 'm')   -> Decimal('0.012')
        convert_to_unit('12', 'mm')     -> Decimal('12')      # o'lchovsiz -> mm deb qabul qilinadi
        convert_to_unit('1 kg', 'm')    -> ValidationError    # mos kelmaydigan o'lchamlar
    """
    ureg = _registry(tenant_id, registry)

    original = str(value).strip() if value is not None else ''

    if not original:
        raise ValidationError(_('Qiymat kiritilmagan'))

    unit = (unit or '').strip()

    if unit and not is_valid_unit(unit, registry=ureg):
        raise ValidationError(_('Noma\'lum o\'lchov birligi: %(unit)s') % {'unit': unit})

    # Qiymat bir marta ajratiladi. InvenTree bu yerda "urinishlar ro'yxati"
    # ishlatadi va har urinishda qiymatga birlikni qo'shib ko'radi
    # (InvenTree/conversion.py:270-274). Bizda bu xavfli edi: "1 qop" +
    # "kg" -> "1 qop kg" satri `pint` tomonidan `1 * qop * kg` deb
    # ajratiladi va natija jimgina `1 kg` bo'lib chiqadi. Shuning uchun
    # birlik faqat qiymat umuman ajratilmagan holda qo'shiladi.
    quantity = None

    try:
        quantity = ureg.Quantity(original)
    except Exception:
        quantity = None

    if quantity is None and unit:
        # Qiymatni ajratib bo'lmadi — ehtimol u sof son emas, lekin
        # birlik bilan birga ma'noga ega ("1/2" kabi holatlar).
        try:
            quantity = ureg.Quantity(f'{original} {unit}')
        except Exception:
            quantity = None

    if quantity is None:
        raise ValidationError(
            _('"%(value)s" — tushunarsiz miqdor') % {'value': original}
        )

    if unit:
        if is_bare_number(quantity, ureg):
            # Birliksiz songa maqsad birlik biriktiriladi ("12" -> "12 mm").
            quantity = ureg.Quantity(quantity.magnitude, unit)
        else:
            # Birligi bor qiymat, o'lchovsiz bo'lsa ham, `to()` orqali
            # o'tadi — shunda "1 qop" ni "kg" ga aylantirib bo'lmaydi.
            try:
                quantity = quantity.to(unit)
            except Exception:
                raise ValidationError(
                    _('"%(value)s" qiymatini %(unit)s ga keltirib bo\'lmadi')
                    % {'value': original, 'unit': unit}
                )

    magnitude = quantity.magnitude if unit else quantity.to_base_units().magnitude

    if not isinstance(magnitude, Decimal):
        # Registr `non_int_type=Decimal` bilan qurilgani uchun bu yerga
        # tushmasligi kerak; tushsa — registr noto'g'ri qurilgan.
        raise ValidationError(
            _('Ichki xato: miqdor Decimal emas (%(type)s)')
            % {'type': type(magnitude).__name__}
        )

    return magnitude


def to_base_units(
    value,
    unit: str | None = None,
    *,
    tenant_id: uuid.UUID | None = None,
    registry=None,
) -> Decimal | None:
    """Qiymatni bazaviy SI birlikka keltiradi; keltirib bo'lmasa `None`.

    Atributlarning `num` kalitini to'ldirish uchun ishlatiladi: qiymat
    normallashtirilsa `"10 mm"` va `"1 sm"` bir xil songa aylanadi va
    filtrlash to'g'ri ishlaydi. Keltirib bo'lmasa (masalan `"Yog'och"`)
    `None` qaytadi — bu xato emas, matnli atribut shunday bo'ladi.
    """
    try:
        ureg = _registry(tenant_id, registry)
        text = str(value).strip() if value is not None else ''

        if not text:
            return None

        if unit:
            quantity = convert_to_unit(text, unit, registry=ureg)
            return ureg.Quantity(quantity, unit).to_base_units().magnitude

        return ureg.Quantity(text).to_base_units().magnitude
    except Exception:
        return None
