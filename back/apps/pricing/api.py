"""Valyuta va kurs API si."""

from __future__ import annotations

from rest_framework import viewsets

from apps.core.permissions import IsTenantAdminOrReadOnly
from apps.pricing.models import Currency, ExchangeRate
from apps.pricing.serializers import CurrencySerializer, ExchangeRateSerializer


class CurrencyViewSet(viewsets.ModelViewSet):
    serializer_class = CurrencySerializer
    permission_classes = [IsTenantAdminOrReadOnly]
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
    permission_classes = [IsTenantAdminOrReadOnly]

    def get_queryset(self):
        queryset = ExchangeRate.objects.select_related('currency')

        if currency := self.request.query_params.get('currency', '').strip():
            queryset = queryset.filter(currency_id=currency)

        return queryset.order_by('-valid_from')
