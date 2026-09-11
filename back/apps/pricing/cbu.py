"""O'zbekiston Respublikasi Markaziy banki (cbu.uz) valyuta kurslari.

Markaziy bank kurslarni ochiq JSON API orqali beradi:

    https://cbu.uz/uz/arkhiv-kursov-valyut/json/              — joriy
    https://cbu.uz/uz/arkhiv-kursov-valyut/json/all/YYYY-MM-DD/ — sana bo'yicha

Har yozuv shunday ko'rinadi (keraksiz maydonlar tushirib qoldirilgan):

    {"Ccy": "USD", "Nominal": "1",  "Rate": "11783.47", "Date": "11.09.2026"}
    {"Ccy": "IDR", "Nominal": "10", "Rate": "6.72",     "Date": "11.09.2026"}

Uchta nozik joy bor, har biri jimgina xato kurs berishi mumkin edi:

1. **`Nominal`.** Kurs `Nominal` birlik uchun berilgan. IDR uchun bu 10:
   "10 rupiya = 6.72 so'm", ya'ni 1 rupiya 0.672 so'm. Bo'lmasdan
   olinsa kurs 10 barobar oshib ketadi va xato hech qayerda ko'rinmaydi.
2. **Sana formati** `dd.mm.yyyy` — ISO emas.
3. **Son satr sifatida keladi.** U to'g'ridan-to'g'ri `Decimal` ga
   o'giriladi; `float` orqali o'tkazilmaydi (6-arxitektura qarori).

Bu modul faqat tarmoqdan o'qiydi va javobni tahlil qiladi — bazaga
yozmaydi. Yozish `apps.pricing.services.sync_rates_from_cbu()` da.
"""

from __future__ import annotations

import json
import logging
import ssl
import urllib.request
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from apps.core.fields import FACTOR_DECIMAL_PLACES

logger = logging.getLogger(__name__)

CBU_LATEST_URL = 'https://cbu.uz/uz/arkhiv-kursov-valyut/json/'
CBU_ON_DATE_URL = 'https://cbu.uz/uz/arkhiv-kursov-valyut/json/all/{date}/'

#: Markaziy bank kurslari so'mga nisbatan beriladi. Asosiy valyutasi
#: boshqa bo'lgan tashkilot uchun ular to'g'ridan-to'g'ri yaramaydi.
CBU_BASE_CURRENCY = 'UZS'

#: `ExchangeRate.source` ga yoziladigan belgi. Qo'lda kiritilgan kursni
#: avtomatik kursdan ajratish uchun ishlatiladi.
CBU_SOURCE = 'Markaziy bank'

REQUEST_TIMEOUT = 15

_QUANT = Decimal(1).scaleb(-FACTOR_DECIMAL_PLACES)


class CbuError(Exception):
    """Markaziy bankdan kurs olib bo'lmadi (tarmoq yoki javob formati)."""


@dataclass(frozen=True)
class CbuRate:
    """Bitta valyutaning 1 birligi necha so'm ekanligi."""

    code: str
    rate: Decimal
    valid_from: date


def _ssl_context() -> ssl.SSLContext:
    """Operatsion tizim sertifikat omboridan foydalanuvchi SSL konteksti.

    `truststore` bo'lsa u ishlatiladi: korporativ tarmoqlarda TLS
    trafigi o'z sertifikati bilan qayta imzolanadi va Python'ning
    o'z `certifi` to'plami uni tanimaydi. Serverda (Linux) standart
    kontekst ham ishlaydi, shuning uchun `truststore` majburiy emas.
    """
    try:
        import truststore

        return truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    except ImportError:
        return ssl.create_default_context()


def _parse_row(row: dict) -> CbuRate | None:
    """Bitta yozuvni tahlil qiladi; buzuq bo'lsa `None` (va log)."""
    try:
        code = str(row['Ccy']).strip().upper()
        nominal = int(str(row['Nominal']).strip())
        raw_rate = Decimal(str(row['Rate']).strip())
        valid_from = datetime.strptime(str(row['Date']).strip(), '%d.%m.%Y').date()
    except (KeyError, ValueError, TypeError, InvalidOperation):
        logger.warning('Markaziy bank javobida buzuq yozuv: %r', row)
        return None

    if len(code) != 3 or nominal <= 0 or raw_rate <= 0:
        logger.warning('Markaziy bank javobida yaroqsiz qiymat: %r', row)
        return None

    return CbuRate(
        code=code,
        rate=(raw_rate / nominal).quantize(_QUANT),
        valid_from=valid_from,
    )


def parse_rates(payload) -> dict[str, CbuRate]:
    """Markaziy bank javobini `{kod: CbuRate}` lug'atiga aylantiradi.

    Buzuq yozuvlar tashlab yuboriladi (bitta xato yozuv qolgan
    valyutalarni to'xtatmasligi kerak). Javob umuman ro'yxat bo'lmasa
    yoki bitta ham yaroqli yozuv bo'lmasa — `CbuError`.
    """
    if not isinstance(payload, list):
        raise CbuError('Markaziy bank javobi kutilgan formatda emas')

    rates = {}

    for row in payload:
        if isinstance(row, dict) and (parsed := _parse_row(row)):
            rates[parsed.code] = parsed

    if not rates:
        raise CbuError('Markaziy bank javobida yaroqli kurs topilmadi')

    return rates


def fetch_rates(on_date: date | None = None) -> dict[str, CbuRate]:
    """Markaziy bankdan kurslarni oladi.

    `on_date` berilsa — o'sha sanadagi kurslar, aks holda joriy kurslar.

    Raises:
        CbuError: tarmoq xatosi, vaqt tugashi yoki javob tahlil qilinmasa.
    """
    url = (
        CBU_ON_DATE_URL.format(date=on_date.isoformat())
        if on_date
        else CBU_LATEST_URL
    )

    request = urllib.request.Request(url, headers={'Accept': 'application/json'})

    try:
        with urllib.request.urlopen(
            request, timeout=REQUEST_TIMEOUT, context=_ssl_context()
        ) as response:
            payload = json.load(response)
    except (OSError, ValueError) as exc:
        # OSError: tarmoq, DNS, SSL, vaqt tugashi; ValueError: JSON emas
        raise CbuError(f'Markaziy bankka ulanib bo\'lmadi: {exc}') from exc

    return parse_rates(payload)
