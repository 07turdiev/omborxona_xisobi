"""Fiskal provayder ulash nuqtasi.

O'zbekistonda chek soliq tizimida ro'yxatdan o'tishi kerak. Provayder hali
tanlanmagan, shuning uchun bu yerda faqat interfeys va hech narsa
qilmaydigan `NullFiscalProvider` bor.

Provayder **tranzaksiya yakunlangandan keyin** chaqiriladi
(`transaction.on_commit`): chek bazaga yozilmasdan turib soliq tizimiga
yuborilsa, tranzaksiya bekor bo'lganda mavjud bo'lmagan sotuv ro'yxatdan
o'tgan bo'lib qolardi.
"""

import logging
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class FiscalProvider(ABC):
    """Fiskal xizmat bilan ishlash interfeysi."""

    @abstractmethod
    def register_sale(self, sale) -> dict:
        """Sotuvni ro'yxatdan o'tkazadi va javob ma'lumotini qaytaradi."""

    @abstractmethod
    def register_return(self, sale_return) -> dict:
        """Qaytarishni ro'yxatdan o'tkazadi."""


class NullFiscalProvider(FiscalProvider):
    """Standart provayder: hech narsa yubormaydi, faqat logga yozadi."""

    def register_sale(self, sale) -> dict:
        logger.info('Fiskal: sotuv %s ro‘yxatdan o‘tkazilmadi (provayder ulanmagan)', sale.number)
        return {}

    def register_return(self, sale_return) -> dict:
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
    _store_response(sale, get_provider().register_sale(sale))


def register_return(sale_return) -> None:
    _store_response(sale_return, get_provider().register_return(sale_return))
