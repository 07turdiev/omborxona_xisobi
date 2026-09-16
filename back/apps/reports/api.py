from datetime import timedelta

from django.utils import timezone
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet

from apps.core.export import (
    DATETIME,
    MONEY,
    NUMBER,
    TEXT,
    Column,
    build_workbook,
    excel_response,
)
from apps.core.dates import local_bounds
from apps.core.permissions import IsAdmin
from apps.inventory.models import StockMovement
from apps.reports import services


def parse_date(value, default):
    """`YYYY-MM-DD` ni sanaga o'giradi."""
    if not value:
        return default

    parsed = timezone.datetime.strptime(value, '%Y-%m-%d').date()

    return parsed


class ReportViewSet(ViewSet):
    """Hisobotlar — faqat administrator uchun."""

    permission_classes = [IsAdmin]

    def _period(self, request):
        today = timezone.localdate()

        try:
            date_from = parse_date(request.query_params.get('date_from'), today - timedelta(days=29))
            date_to = parse_date(request.query_params.get('date_to'), today)
        except ValueError:
            raise ValidationError({'date_from': 'Sana formati: YYYY-MM-DD'})

        if date_to < date_from:
            raise ValidationError({'date_to': 'Tugash sanasi boshlanishdan oldin bo‘lmasin'})

        return date_from, date_to

    @action(detail=False)
    def dashboard(self, request):
        return Response(services.dashboard())

    @action(detail=False)
    def sales(self, request):
        date_from, date_to = self._period(request)

        return Response(services.sales_report(date_from, date_to))

    @action(detail=False, url_path='top-products')
    def top_products(self, request):
        date_from, date_to = self._period(request)
        limit = int(request.query_params.get('limit', 10))

        return Response(services.top_products(date_from, date_to, limit))

    @action(detail=False)
    def stock(self, request):
        return Response(
            services.stock_report(
                category=request.query_params.get('category'),
                low_stock=request.query_params.get('low_stock') == 'true',
            )
        )

    @action(detail=False)
    def suppliers(self, request):
        return Response(services.supplier_balances())

    # -- Excel ---------------------------------------------------------

    @action(detail=False, url_path='sales/export')
    def sales_export(self, request):
        date_from, date_to = self._period(request)
        report = services.sales_report(date_from, date_to)

        rows = [
            {'name': 'Tushum', 'amount': report['revenue']},
            {'name': 'Qaytarishlar', 'amount': report['returns']},
            {'name': 'Sof tushum', 'amount': report['net_revenue']},
            {'name': 'Chegirmalar', 'amount': report['discounts']},
            {'name': 'Tannarx', 'amount': report['cost']},
            {'name': 'Yalpi foyda', 'amount': report['gross_profit']},
            {'name': 'Yo‘qotishlar', 'amount': report['losses']},
            {'name': 'Xarajatlar', 'amount': report['expenses']},
            {'name': 'Sof foyda', 'amount': report['net_profit']},
            {'name': 'Naqd', 'amount': report['payments']['cash']},
            {'name': 'Karta', 'amount': report['payments']['card']},
        ]

        workbook = build_workbook(
            [Column('name', 'Ko‘rsatkich', TEXT, width=28), Column('amount', 'Summa', MONEY)],
            rows,
            sheet_name='Sotuv',
            title=f'Sotuv hisoboti: {date_from} — {date_to}',
        )

        return excel_response(workbook, 'sotuv-hisoboti')

    @action(detail=False, url_path='stock/export')
    def stock_export(self, request):
        report = services.stock_report(
            category=request.query_params.get('category'),
            low_stock=request.query_params.get('low_stock') == 'true',
        )

        columns = [
            Column('sku', 'Artikul', TEXT, width=14),
            Column('product', 'Mahsulot', TEXT, width=30),
            Column('label', 'O‘lcham / rang', TEXT),
            Column('category', 'Kategoriya', TEXT),
            Column('quantity', 'Qoldiq', NUMBER),
            Column('average_cost', 'O‘rtacha tannarx', MONEY),
            Column('cost_value', 'Tannarx qiymati', MONEY),
            Column('price', 'Sotuv narxi', MONEY),
            Column('retail_value', 'Chakana qiymati', MONEY),
        ]

        return excel_response(
            build_workbook(columns, report['rows'], sheet_name='Qoldiq', title='Qoldiqlar'),
            'qoldiqlar',
        )

    @action(detail=False, url_path='movements/export')
    def movements_export(self, request):
        date_from, date_to = self._period(request)
        start, end = local_bounds(date_from, date_to)

        movements = (
            StockMovement.objects.select_related('variant__product', 'user')
            .filter(created_at__gte=start, created_at__lt=end)
            .order_by('created_at')
        )

        columns = [
            Column('created_at', 'Vaqti', DATETIME),
            Column('variant.sku', 'Artikul', TEXT, width=14),
            Column('variant.product.name', 'Mahsulot', TEXT, width=30),
            Column('quantity', 'Miqdor', NUMBER),
            Column('reason', 'Sabab', TEXT),
            Column('unit_cost', 'Tannarx', MONEY),
            Column('user.username', 'Xodim', TEXT),
        ]

        return excel_response(
            build_workbook(
                columns,
                movements,
                sheet_name='Harakatlar',
                title=f'Ombor harakatlari: {date_from} — {date_to}',
            ),
            'ombor-harakatlari',
        )
