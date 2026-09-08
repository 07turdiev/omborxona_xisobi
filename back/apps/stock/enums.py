"""Qoldiq harakatining sabablari.

Bu modulda InvenTree loyihasidan (MIT) olingan taksonomiya bor.
Manba: InvenTree 1.6.0 dev — stock/status_codes.py:44-140
Litsenziya va to'liq atribut: repo ildizidagi NOTICE faylida.

Ro'yxatning o'zi qimmatli: bu sakkiz yillik ekspluatatsiyada to'plangan
"ombor harakatining qancha turi bor" javobi. Noldan yozganda bunday
holatlar bittalab, har biri migratsiya bilan qo'shila boshlaydi.

InvenTree dan olinmagan kodlar: barcha `BUILD_*` (ishlab chiqarish yo'q),
`INSTALLED_*` / `REMOVED_*_ASSEMBLY` (yig'ma tovar yo'q), `ASSIGNED_SERIAL`
va `STOCK_SERIALIZED` (seriya raqami MVP da yo'q), `DISASSEMBLED`,
`CONVERTED_TO_VARIANT`.

Qo'shilgan kodlar (InvenTree da yo'q): `TRANSFER_OUT` / `TRANSFER_IN` /
`TRANSIT_LOSS`, `STOCKTAKE_CORRECTION`, `WRITE_OFF_*`.
"""

from __future__ import annotations

from django.db import models
from django.utils.translation import gettext_lazy as _


class MovementReason(models.TextChoices):
    """Jurnaldagi har bir yozuvning sababi.

    **Ikki tomonlama amallar ikki yozuv qoldiradi.** InvenTree ham
    shunday qiladi (`SPLIT_FROM_PARENT` / `SPLIT_CHILD_ITEM`), va bu
    bizda majburiy: bitta jurnal qatori faqat bitta ombor qoldig'ini
    o'zgartiradi. Ko'chirish `TRANSFER_OUT` + `TRANSFER_IN` bo'ladi,
    aks holda "bir yozuv — bir o'zgarish" qoidasi buziladi.
    """

    # Kirim
    PURCHASE = 'purchase', _('Yetkazib beruvchidan kirim')
    RETURN_FROM_CUSTOMER = 'return_from_customer', _('Mijozdan qaytdi')
    MANUAL_ADD = 'manual_add', _('Qo\'lda kiritildi')
    OPENING_BALANCE = 'opening_balance', _('Boshlang\'ich qoldiq')

    # Chiqim
    SALE = 'sale', _('Sotuv')
    RETURN_TO_SUPPLIER = 'return_to_supplier', _('Yetkazib beruvchiga qaytarildi')
    MANUAL_REMOVE = 'manual_remove', _('Qo\'lda chiqarildi')

    # Omborlararo ko'chirish — ikki bosqichli (6-band)
    TRANSFER_OUT = 'transfer_out', _('Ko\'chirish: jo\'natildi')
    TRANSFER_IN = 'transfer_in', _('Ko\'chirish: qabul qilindi')
    TRANSIT_LOSS = 'transit_loss', _('Yo\'lda yo\'qolgan')

    # Tuzatishlar va yo'qotishlar
    STOCKTAKE_CORRECTION = 'stocktake_correction', _('Inventarizatsiya farqi')
    WRITE_OFF_DAMAGED = 'write_off_damaged', _('Buzilgan tovar hisobdan chiqarildi')
    WRITE_OFF_EXPIRED = 'write_off_expired', _('Muddati o\'tgan tovar hisobdan chiqarildi')

    @classmethod
    def inbound(cls) -> frozenset[str]:
        """Qoldiqni oshiradigan sabablar."""
        return frozenset({
            cls.PURCHASE, cls.RETURN_FROM_CUSTOMER, cls.MANUAL_ADD,
            cls.OPENING_BALANCE, cls.TRANSFER_IN,
        })

    @classmethod
    def outbound(cls) -> frozenset[str]:
        """Qoldiqni kamaytiradigan sabablar."""
        return frozenset({
            cls.SALE, cls.RETURN_TO_SUPPLIER, cls.MANUAL_REMOVE,
            cls.TRANSFER_OUT, cls.TRANSIT_LOSS,
            cls.WRITE_OFF_DAMAGED, cls.WRITE_OFF_EXPIRED,
        })

    @classmethod
    def bidirectional(cls) -> frozenset[str]:
        """Ikki tomonga ham bo'lishi mumkin bo'lgan sabablar.

        Inventarizatsiya farqi musbat ham, manfiy ham bo'ladi: sanashda
        ortiqcha topilishi ham, kam chiqishi ham mumkin.
        """
        return frozenset({cls.STOCKTAKE_CORRECTION})

    @classmethod
    def is_loss(cls, reason: str) -> bool:
        """Bu sabab yo'qotishmi (savdo emas)?

        Foyda hisobotida yo'qotishlar sotuvdan alohida ko'rsatilishi
        kerak, aks holda tannarx tahlili buziladi.
        """
        return reason in {
            cls.TRANSIT_LOSS, cls.WRITE_OFF_DAMAGED,
            cls.WRITE_OFF_EXPIRED, cls.STOCKTAKE_CORRECTION,
        }
