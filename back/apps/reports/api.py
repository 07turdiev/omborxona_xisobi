"""Hisobot API si — faqat o'qish."""

from __future__ import annotations

from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet

from apps.core.permissions import HasTenantMembership
from apps.reports import services


class ReportViewSet(ViewSet):
    """Hisobotlar.

    **Barcha a'zolarga ochiq.** Siz shunday xohlagansiz: ombor soni oz
    va hamma hisobotlarni ko'rishi kerak. Cheklov kerak bo'lsa,
    `WarehouseAccess` orqali ombor darajasida qo'shiladi.
    """

    permission_classes = [HasTenantMembership]

    def _period(self, request) -> dict:
        params = request.query_params

        return {
            'date_from': params.get('date_from') or None,
            'date_to': params.get('date_to') or None,
            'warehouse': params.get('warehouse') or None,
        }

    def list(self, request):
        """Barcha asosiy hisobotlar bir so'rovda.

        Hisobot sahifasi to'rt-besh bo'limdan iborat va ularni alohida
        so'rov bilan olish sahifani sekinlashtirardi.
        """
        period = self._period(request)

        return Response({
            'summary': services.period_summary(**period),
            'by_category': services.by_category(**period),
            'by_warehouse': services.by_warehouse(
                period['date_from'], period['date_to']
            ),
            'top_products': services.top_products(**period, limit=10),
            'daily_sales': services.daily_sales(**period),
            'losses': services.loss_summary(**period),
            'valuation': services.stock_valuation(period['warehouse']),
        })

    @action(detail=False, methods=['get'])
    def summary(self, request):
        return Response(services.period_summary(**self._period(request)))

    @action(detail=False, methods=['get'], url_path='by-category')
    def by_category(self, request):
        return Response(services.by_category(**self._period(request)))

    @action(detail=False, methods=['get'], url_path='by-warehouse')
    def by_warehouse(self, request):
        period = self._period(request)

        return Response(
            services.by_warehouse(period['date_from'], period['date_to'])
        )

    @action(detail=False, methods=['get'])
    def losses(self, request):
        return Response(services.loss_summary(**self._period(request)))

    @action(detail=False, methods=['get'])
    def valuation(self, request):
        return Response(
            services.stock_valuation(request.query_params.get('warehouse') or None)
        )

    @action(detail=False, methods=['get'])
    def dashboard(self, request):
        """Boshqaruv paneli uchun yig'ma ma'lumot."""
        period = self._period(request)

        return Response({
            'summary': services.period_summary(**period),
            'valuation': services.stock_valuation(None),
            'daily_sales': services.daily_sales(**period),
            'recent_movements': services.recent_movements(limit=8),
            'low_stock': services.low_stock(limit=6),
            'expiring': services.expiring_batches(days=30, limit=6),
        })
