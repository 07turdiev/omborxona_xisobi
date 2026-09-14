"""Valyuta va kurs API si."""

from __future__ import annotations

from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.core.access import Perm
from apps.core.permissions import SectionPermission
from apps.pricing.cbu import CbuError, fetch_rates
from apps.pricing.models import Currency, ExchangeRate
from apps.pricing.rate_sync import sync_rates_from_cbu
from apps.pricing.serializers import CurrencySerializer, ExchangeRateSerializer


class CurrencyViewSet(viewsets.ModelViewSet):
    serializer_class = CurrencySerializer
    permission_classes = [SectionPermission]
    section_permissions = {'write': {Perm.SETTINGS}}
    pagination_class = None

    def get_queryset(self):
        return Currency.objects.all()


class ExchangeRateViewSet(viewsets.ModelViewSet):
    """Valyuta kurslari — tarix bilan.

    Kurs `valid_from` sanasidan boshlab amal qiladi va keyingisi
    qo'shilgunicha kuchda qoladi. Eski yozuvlar o'chirilmasligi kerak:
    ular bilan hisoblangan hujjatlar qayta hisoblanganda o'sha kungi
    kurs topilmay qolardi.
    """

    serializer_class = ExchangeRateSerializer
    permission_classes = [SectionPermission]
    section_permissions = {'write': {Perm.SETTINGS}}

    def get_queryset(self):
        queryset = ExchangeRate.objects.select_related('currency')

        if currency := self.request.query_params.get('currency', '').strip():
            queryset = queryset.filter(currency_id=currency)

        return queryset.order_by('-valid_from')

    @action(detail=False, methods=['post'], url_path='sync-cbu')
    def sync_cbu(self, request):
        """Markaziy bank kursini hozir olish — sozlamalardagi tugma.

        Faqat joriy tashkilot uchun va sinxron: foydalanuvchi natijani
        darhol ko'rishi kerak. Ishlab chiqarishda xuddi shu ishni Celery
        beat har kuni bajaradi (`apps.pricing.tasks.sync_cbu_rates`).

        Tarmoq so'rovi so'rov tranzaksiyasi ichida bajariladi (15 soniya
        chegara bilan). Bu faqat admin bosadigan kamdan-kam tugma, shuning
        uchun qabul qilinadi.
        """
        try:
            rates = fetch_rates()
        except CbuError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_502_BAD_GATEWAY)

        result = sync_rates_from_cbu(request.membership.tenant, rates)

        return Response(result.as_dict())
