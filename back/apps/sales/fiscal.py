"""Fiskal provayder ulash nuqtasi.

O'zbekistonda chek soliq tizimida ro'yxatdan o'tishi kerak. Provayder hali
tanlanmagan, shuning uchun bu yerda interfeys, yuboriladigan ma'lumot va
hech narsa qilmaydigan `NullFiscalProvider` bor.

Provayder **tranzaksiya yakunlangandan keyin** chaqiriladi
(`transaction.on_commit`): chek bazaga yozilmasdan turib soliq tizimiga
yuborilsa, tranzaksiya bekor bo'lganda mavjud bo'lmagan sotuv ro'yxatdan
o'tgan bo'lib qolardi.

Ma'lumot provayderga tayyor lug'at (`payload`) bo'lib beriladi. Shunday
qilingani uchun provayder ulanganda model tuzilishini bilishi shart
emas — faqat shu lug'atni o'z formatiga o'giradi. Soliq tasnifi kodi
(MXIK) do'kon soliq tizimi bilan ishlamagani uchun olib tashlangan;
provayder ulanadigan bo'lsa, u shu yerga qaytariladi.
"""

import logging
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


def _line_payload(variant, quantity, unit_price, discount_amount, line_total) -> dict:
    product = variant.product

    return {
        'name': f'{product.name} {variant.label}'.strip(),
        'barcode': variant.barcode,
        'quantity': quantity,
        'unit_price': str(unit_price),
        'discount_amount': str(discount_amount),
        'line_total': str(line_total),
    }


def sale_payload(sale) -> dict:
    """Sotuv bo'yicha provayderga yuboriladigan ma'lumot."""
    return {
        'document': 'sale',
        'number': sale.number,
        'created_at': sale.created_at.isoformat(),
        'total': str(sale.total),
        'discount_total': str(sale.discount_total),
        'cash_amount': str(sale.cash_amount),
        'card_amount': str(sale.card_amount),
        'lines': [
            _line_payload(
                line.variant, line.quantity, line.unit_price,
                line.discount_amount, line.line_total,
            )
            for line in sale.lines.select_related('variant__product')
        ],
    }


def return_payload(sale_return) -> dict:
    """Qaytarish bo'yicha ma'lumot. Qatorlar asl chekdan olinadi."""
    lines = sale_return.lines.select_related('sale_line__variant__product')

    return {
        'document': 'return',
        'number': sale_return.number,
        'sale_number': sale_return.sale.number,
        'created_at': sale_return.created_at.isoformat(),
        'total': str(sale_return.total),
        'refund_method': sale_return.refund_method,
        'lines': [
            _line_payload(
                line.sale_line.variant, line.quantity, line.sale_line.unit_price,
                0, line.refund_amount,
            )
            for line in lines
        ],
    }


class FiscalProvider(ABC):
    """Fiskal xizmat bilan ishlash interfeysi."""

    @abstractmethod
    def register_sale(self, sale, payload: dict) -> dict:
        """Sotuvni ro'yxatdan o'tkazadi va javob ma'lumotini qaytaradi."""

    @abstractmethod
    def register_return(self, sale_return, payload: dict) -> dict:
        """Qaytarishni ro'yxatdan o'tkazadi."""


class NullFiscalProvider(FiscalProvider):
    """Standart provayder: hech narsa yubormaydi, faqat logga yozadi."""

    def register_sale(self, sale, payload: dict) -> dict:
        logger.info(
            'Fiskal: sotuv %s ro‘yxatdan o‘tkazilmadi (provayder ulanmagan)', sale.number
        )
        return {}

    def register_return(self, sale_return, payload: dict) -> dict:
        logger.info(
            'Fiskal: qaytarish %s ro‘yxatdan o‘tkazilmadi (provayder ulanmagan)',
            sale_return.number,
        )
        return {}


def get_provider() -> FiscalProvider:
    """Amaldagi provayder. Haqiqiysi ulanganda shu yer o'zgaradi."""
    return NullFiscalProvider()


def _store_response(document, response: dict) -> None:
    """Provayder javobidagi chek raqami va QR havolasini saqlaydi."""
    receipt_id = (response or {}).get('receipt_id', '')
    qr_url = (response or {}).get('qr_url', '')

    if not receipt_id and not qr_url:
        return

    document.fiscal_receipt_id = receipt_id
    document.fiscal_qr_url = qr_url
    document.save(update_fields=['fiscal_receipt_id', 'fiscal_qr_url', 'updated_at'])


def register_sale(sale) -> None:
    """`transaction.on_commit` orqali chaqiriladi."""
    _store_response(sale, get_provider().register_sale(sale, sale_payload(sale)))


def register_return(sale_return) -> None:
    _store_response(
        sale_return,
        get_provider().register_return(sale_return, return_payload(sale_return)),
    )
