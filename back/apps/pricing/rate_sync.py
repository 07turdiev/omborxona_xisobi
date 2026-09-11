"""Markaziy bank kurslarini tashkilot kurs tarixiga yozish.

**Nega bu kerak.** `services.rate_on()` kurs topilmasa eng oxirgi eski
kursni oladi. Ya'ni kursni bir necha hafta hech kim yangilamasa, bugungi
dollar kirimi o'sha eski kurs bilan hisoblanadi — xato chiqmaydi, faqat
tannarx va foyda jimgina noto'g'ri bo'ladi. Kursni har kuni avtomatik
olish bu bo'shliqni yopadi.

Uchta qoida:

1. **Qo'lda kiritilgan kurs hech qachon bosib ketilmaydi.** Agar o'sha
   sana uchun kurs allaqachon bor bo'lsa (qo'lda yoki avvalgi
   sinxronlashdan), u o'zgartirilmaydi. Buxgalter bank kursi bilan emas,
   masalan birja kursi bilan ishlashni tanlagan bo'lishi mumkin.
2. **Qayta ishga tushirish xavfsiz.** Vazifa kuniga bir necha marta
   ishlaydi; ikkinchi chaqiruv hech narsa yozmaydi.
3. **Faqat tashkilot yoqqan valyutalar.** Markaziy bank 70 dan ortiq
   valyuta beradi; tashkilotda faqat `Currency` sifatida qo'shilganlari
   yoziladi, yangi valyuta avtomatik yaratilmaydi.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from django.db import IntegrityError, transaction

from apps.pricing.cbu import CBU_BASE_CURRENCY, CBU_SOURCE, CbuRate
from apps.pricing.models import Currency, ExchangeRate
from apps.pricing.services import base_currency_code


@dataclass
class SyncResult:
    """Bitta tashkilot uchun sinxronlash natijasi."""

    #: Yangi yozilgan kurslar: valyuta kodi
    created: list[str] = field(default_factory=list)

    #: O'sha sana uchun kurs allaqachon bor edi va tegilmadi
    already_present: list[str] = field(default_factory=list)

    #: Tashkilotda bor, lekin Markaziy bank bermaydigan valyutalar
    missing: list[str] = field(default_factory=list)

    #: Kursning amal qilish sanasi (Markaziy bank bergan)
    valid_from: date | None = None

    #: Tashkilot umuman o'tkazib yuborilgan bo'lsa — sababi
    skipped_reason: str = ''

    def as_dict(self) -> dict:
        return {
            'created': self.created,
            'already_present': self.already_present,
            'missing': self.missing,
            'valid_from': self.valid_from.isoformat() if self.valid_from else None,
            'skipped_reason': self.skipped_reason,
        }


@transaction.atomic
def sync_rates_from_cbu(tenant, rates: dict[str, CbuRate]) -> SyncResult:
    """Markaziy bank kurslarini tashkilotning kurs tarixiga yozadi.

    **Tashkilot konteksti ichida chaqirilishi kerak** (`tenant_context`
    yoki HTTP so'rov) — jadvallar RLS bilan himoyalangan.

    Arguments:
        tenant: tashkilot
        rates: `apps.pricing.cbu.fetch_rates()` natijasi. Tarmoqdan
            olish shu funksiyadan tashqarida: fon vazifasi kurslarni bir
            marta olib, barcha tashkilotlarga tarqatadi.
    """
    result = SyncResult()

    base = base_currency_code(tenant)

    if base != CBU_BASE_CURRENCY:
        # Markaziy bank kurslari so'mga nisbatan. Asosiy valyutasi dollar
        # bo'lgan tashkilotga ularni yozish uchun kross-kurs kerak bo'ladi,
        # va noto'g'ri kross-kurs butun tannarxni buzadi — qo'lda qolsin.
        result.skipped_reason = (
            f'Asosiy valyuta {base}: Markaziy bank kurslari faqat so\'mga '
            'nisbatan beriladi, shuning uchun kurslarni qo\'lda kiriting.'
        )
        return result

    currencies = Currency.objects.filter(
        tenant=tenant, is_active=True, is_base=False
    ).order_by('code')

    for currency in currencies:
        cbu_rate = rates.get(currency.code)

        if cbu_rate is None:
            result.missing.append(currency.code)
            continue

        result.valid_from = cbu_rate.valid_from

        # get_or_create emas: mavjud yozuvni hech qachon o'zgartirmaymiz,
        # hatto u Markaziy bankniki bo'lsa ham. Unique constraint
        # (currency, valid_from) parallel ishga tushirishdan himoya qiladi.
        exists = ExchangeRate.objects.filter(
            currency=currency, valid_from=cbu_rate.valid_from
        ).exists()

        if exists:
            result.already_present.append(currency.code)
            continue

        try:
            # Savepoint: parallel ishga tushgan boshqa vazifa shu orada
            # yozib ulgurgan bo'lsa, butun tranzaksiya emas, faqat shu
            # qator bekor bo'ladi.
            with transaction.atomic():
                ExchangeRate.objects.create(
                    tenant=tenant,
                    currency=currency,
                    rate=cbu_rate.rate,
                    valid_from=cbu_rate.valid_from,
                    source=CBU_SOURCE,
                )
        except IntegrityError:
            result.already_present.append(currency.code)
            continue

        result.created.append(currency.code)

    return result
