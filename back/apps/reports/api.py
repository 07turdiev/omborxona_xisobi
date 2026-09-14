"""Hisobot API si — faqat o'qish."""

from __future__ import annotations

from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_view
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet

#: Barcha hisobot endpointlariga umumiy parametrlar
PERIOD_PARAMS = [
    OpenApiParameter('date_from', str, description='Davr boshi (YYYY-MM-DD)'),
    OpenApiParameter('date_to', str, description='Davr oxiri (YYYY-MM-DD)'),
    OpenApiParameter('warehouse', int, description='Ombor ID si'),
]

from apps.core.export import context_meta, excel_response
from apps.core.access import FinancialRedactionMixin, Perm
from apps.core.permissions import SectionPermission
from apps.reports import services
from apps.reports.export import build_report_workbook

#: Excel fayl turi — sxemada javob shu tarzda e'lon qilinadi
XLSX_MIME = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'


@extend_schema_view(
    list=extend_schema(
        parameters=PERIOD_PARAMS,
        responses={200: dict},
        description="Barcha asosiy hisobotlar bir so'rovda.",
    ),
)
@extend_schema(parameters=PERIOD_PARAMS, responses={200: dict})
class ReportViewSet(FinancialRedactionMixin, ViewSet):
    """Hisobotlar.

    Hisobotlar `reports` ruxsati bilan, boshqaruv paneli — `dashboard`
    ruxsati bilan ochiladi. Standart rollarda hisobotlar deyarli hamma
    uchun ochiq; tannarx va foyda esa alohida ruxsat (`view_profit`)
    bo'lmasa javobdan tozalanadi.
    """

    permission_classes = [SectionPermission]
    section_permissions = {'read': {Perm.REPORTS}, 'dashboard': {Perm.DASHBOARD}}
    extra_permissions = {'export': {Perm.PRINT_REPORTS}}

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
            'losses': self._losses(request, period),
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
        return Response(self._losses(request, self._period(request)))

    def _losses(self, request, period: dict) -> dict:
        """Yo'qotishlar — summasi kirim narxidan hisoblanadi.

        Summa kalitining nomi `amount`, u umumiy yashirish ro'yxatida emas
        (qarz summasi ham shunday ataladi), shuning uchun shu yerda alohida
        tozalanadi.
        """
        data = services.loss_summary(**period)

        if request.membership.has_perm(Perm.VIEW_PURCHASE_PRICE):
            return data

        return {
            'total': None,
            'by_reason': [{**row, 'amount': None} for row in data['by_reason']],
        }

    @action(detail=False, methods=['get'])
    def valuation(self, request):
        return Response(
            services.stock_valuation(request.query_params.get('warehouse') or None)
        )

    @extend_schema(
        parameters=PERIOD_PARAMS,
        responses={(200, XLSX_MIME): bytes},
        description="Butun hisobotni ko'p varaqli Excel fayl sifatida yuklab olish.",
    )
    @action(detail=False, methods=['get'])
    def export(self, request):
        """Hisobotni Excel'ga chiqaradi.

        Ekrandagi filtrlar bilan bir xil davr olinadi — foydalanuvchi
        ko'rib turgan raqamlar bilan fayldagi raqamlar mos kelishi kerak.
        """
        period = self._period(request)
        workbook = build_report_workbook(
            period, self._export_meta(request, period), request.membership
        )

        return excel_response(workbook, 'hisobot')

    def _export_meta(self, request, period: dict) -> list[tuple[str, str]]:
        """Fayl qaysi shartlarda olinganini yozib qo'yadi."""
        date_from = period['date_from'] or '—'
        date_to = period['date_to'] or '—'

        return context_meta(
            request,
            warehouse_id=period['warehouse'],
            extra=[('Davr', f'{date_from} … {date_to}')],
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
