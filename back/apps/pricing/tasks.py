"""Narx va valyuta bo'yicha fon vazifalari."""

from __future__ import annotations

import logging
from datetime import date

from celery import shared_task

from apps.core.tenancy import tenant_context
from apps.pricing.cbu import CbuError, CbuRate, fetch_rates
from apps.pricing.rate_sync import sync_rates_from_cbu

logger = logging.getLogger(__name__)


def sync_all_tenants(rates: dict[str, CbuRate], *, tenant_slug: str | None = None) -> dict:
    """Kurslarni barcha faol tashkilotlarga (yoki bittasiga) yozadi.

    Har tashkilot o'z konteksti va o'z tranzaksiyasida ishlanadi: RLS
    to'g'ri qo'llanadi, va bitta tashkilotdagi xato (masalan buzuq
    valyuta yozuvi) qolganlarining kursini to'xtatib qo'ymaydi.

    Returns:
        `{tenant_slug: SyncResult.as_dict() | {"error": "..."}}`
    """
    from apps.tenants.models import Tenant

    # `Tenant` jadvalida RLS yo'q (bootstrap jadvali), shuning uchun
    # kontekstsiz o'qiladi.
    tenants = Tenant.objects.filter(is_active=True).order_by('slug')

    if tenant_slug:
        tenants = tenants.filter(slug=tenant_slug)

    summary = {}

    for tenant in tenants:
        try:
            with tenant_context(tenant.id):
                result = sync_rates_from_cbu(tenant, rates)
        except Exception as exc:
            logger.exception('Kurs sinxronlanmadi: tenant=%s', tenant.slug)
            summary[tenant.slug] = {'error': str(exc)}
            continue

        summary[tenant.slug] = result.as_dict()

        if result.created:
            logger.info(
                'Markaziy bank kursi yozildi: tenant=%s %s (%s)',
                tenant.slug, ', '.join(result.created), result.valid_from,
            )

    return summary


@shared_task(
    autoretry_for=(CbuError,),
    # Bank sayti ishlamay qolsa: 1, 2, 4, 8, 16 daqiqadan keyin qayta.
    # Jadval kuniga uch marta ishga tushgani uchun bundan uzoq kutish
    # shart emas — keyingi jadval baribir to'ldiradi.
    retry_backoff=60,
    retry_backoff_max=960,
    max_retries=5,
)
def sync_cbu_rates(on_date: str | None = None) -> dict:
    """Markaziy bank kurslarini olib, barcha tashkilotlarga yozadi.

    Arguments:
        on_date: `YYYY-MM-DD` — o'tgan sananing kursini to'ldirish uchun.
            Berilmasa joriy kurs. Celery argumentlarni JSON orqali
            uzatgani uchun `date` emas, satr.
    """
    rates = fetch_rates(date.fromisoformat(on_date) if on_date else None)

    return sync_all_tenants(rates)
