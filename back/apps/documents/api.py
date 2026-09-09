"""Hujjat API si."""

from __future__ import annotations

from decimal import Decimal

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import Count, Q, Sum
from openpyxl import Workbook
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.core.export import (
    DATE,
    MONEY,
    NUMBER,
    QUANTITY,
    TEXT,
    Column,
    add_sheet,
    context_meta,
    excel_response,
)
from apps.core.permissions import IsTenantMemberOrReadOnly
from apps.documents import services
from apps.documents.models import Document
from apps.documents.serializers import DocumentSerializer
from apps.warehouse.models import WarehouseAccess


class DocumentViewSet(viewsets.ModelViewSet):
    """Kirim va sotuv hujjatlari.

    Tasdiqlash va bekor qilish alohida amallar: ular qoldiqqa ta'sir
    qiladi va oddiy `PATCH` bilan aralashtirib yuborilmasligi kerak.
    """

    serializer_class = DocumentSerializer
    permission_classes = [IsTenantMemberOrReadOnly]
    # Sxema generatori so'rovsiz ishlaydi va `get_queryset()` u yerda
    # yiqiladi — model tipi shu atributdan aniqlanadi
    queryset = Document.objects.none()

    def get_queryset(self):
        queryset = (
            Document.objects.select_related('warehouse', 'partner')
            .prefetch_related('lines__variant__product')
        )

        allowed = WarehouseAccess.visible_to(self.request.user)
        queryset = queryset.filter(warehouse__in=allowed)

        params = self.request.query_params

        if kind := params.get('kind', '').strip():
            queryset = queryset.filter(kind=kind)

        if status_value := params.get('status', '').strip():
            queryset = queryset.filter(status=status_value)

        if warehouse := params.get('warehouse', '').strip():
            queryset = queryset.filter(warehouse_id=warehouse)

        if partner := params.get('partner', '').strip():
            queryset = queryset.filter(partner_id=partner)

        if search := params.get('search', '').strip():
            queryset = queryset.filter(
                Q(number__icontains=search)
                | Q(external_number__icontains=search)
                | Q(partner__name__icontains=search)
            )

        if date_from := params.get('date_from', '').strip():
            queryset = queryset.filter(date__gte=date_from)

        if date_to := params.get('date_to', '').strip():
            queryset = queryset.filter(date__lte=date_to)

        return queryset

    @action(detail=True, methods=['post'])
    def confirm(self, request, pk=None):
        """Hujjatni tasdiqlaydi va qoldiqqa yozadi."""
        document = self.get_object()

        try:
            services.confirm(document, user=request.user)
        except DjangoValidationError as exc:
            return Response({'detail': exc.messages}, status=400)

        return Response(self.get_serializer(self._reload(document)).data)

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """Hujjatni bekor qiladi — teskari yozuvlar bilan."""
        document = self.get_object()

        try:
            services.cancel(
                document, user=request.user, note=request.data.get('note', '')
            )
        except DjangoValidationError as exc:
            return Response({'detail': exc.messages}, status=400)

        return Response(self.get_serializer(self._reload(document)).data)

    def _reload(self, document):
        """Obyektni bazadan qayta o'qiydi.

        `get_object()` `prefetch_related` bilan keladi; amal bajarilgach
        keshdagi qatorlar eskirgan bo'ladi va javobda eski summalar
        ko'rinadi.
        """
        return self.get_queryset().get(pk=document.pk)

    #: Hujjatlar ro'yxati varag'i
    DOCUMENT_COLUMNS = [
        Column('number', 'Raqam', TEXT, width=16),
        Column('date', 'Sana', DATE),
        Column('kind_display', 'Turi', TEXT, width=14),
        Column('status_display', 'Holati', TEXT, width=14),
        Column('warehouse_name', 'Ombor', TEXT),
        Column('partner_name', 'Kontragent', TEXT, width=26),
        Column('external_number', 'Tashqi raqam', TEXT, width=16),
        Column('line_count', 'Qatorlar', NUMBER),
        Column('total_amount', 'Summa', MONEY),
        Column('total_cost', 'Tannarx', MONEY),
        Column('profit', 'Foyda', MONEY),
        Column('currency', 'Valyuta', TEXT, width=10),
        Column('note', 'Izoh', TEXT, width=30),
    ]

    #: Qatorlar varag'i — buxgalterga aynan shu kesim kerak bo'ladi
    LINE_COLUMNS = [
        Column('number', 'Hujjat', TEXT, width=16),
        Column('date', 'Sana', DATE),
        Column('kind_display', 'Turi', TEXT, width=14),
        Column('warehouse_name', 'Ombor', TEXT),
        Column('partner_name', 'Kontragent', TEXT, width=26),
        Column('product_name', 'Mahsulot', TEXT, width=30),
        Column('sku', 'SKU', TEXT, width=16),
        Column('batch_code', 'Partiya', TEXT, width=16),
        Column('quantity', 'Miqdor', QUANTITY),
        Column('unit', 'Birlik', TEXT, width=10),
        Column('quantity_base', 'Bazaviy miqdor', QUANTITY),
        Column('base_unit', 'Bazaviy birlik', TEXT, width=12),
        Column('unit_price', 'Narx', MONEY),
        Column('discount_percent', 'Chegirma, %', MONEY),
        Column('line_total', 'Qator summasi', MONEY),
        Column('line_cost', 'Qator tannarxi', MONEY),
    ]

    @action(detail=False, methods=['get'])
    def export(self, request):
        """Hujjatlarni Excel'ga chiqaradi.

        Ikki varaq: hujjatlar ro'yxati va **qatorlar**. Ro'yxatning
        o'zi yetarli emas — buxgalter odatda qaysi mahsulot qanchadan
        o'tganini ko'rishi kerak.
        """
        documents = self.filter_queryset(self.get_queryset())
        rows = self.get_serializer(documents, many=True).data

        workbook = Workbook()
        meta = self._export_meta(request)

        add_sheet(
            workbook,
            self.DOCUMENT_COLUMNS,
            rows,
            sheet_name='Hujjatlar',
            title='Hujjatlar',
            meta=meta,
            sheet=workbook.active,
        )

        add_sheet(
            workbook,
            self.LINE_COLUMNS,
            self._flatten_lines(rows),
            sheet_name='Qatorlar',
            title='Hujjat qatorlari',
            meta=meta,
        )

        return excel_response(workbook, 'hujjatlar')

    @staticmethod
    def _flatten_lines(rows):
        """Har qatorga hujjat ma'lumotini qo'shib yassilaydi."""
        header_keys = (
            'number', 'date', 'kind_display', 'warehouse_name', 'partner_name'
        )

        for document in rows:
            header = {key: document.get(key) for key in header_keys}

            for line in document.get('lines') or []:
                yield {**line, **header}

    def _export_meta(self, request):
        """Fayl qaysi filtrlar bilan olinganini yozadi."""
        params = request.query_params

        date_from = params.get('date_from') or '—'
        date_to = params.get('date_to') or '—'

        return context_meta(
            request,
            warehouse_id=params.get('warehouse'),
            extra=[
                ('Davr', f'{date_from} … {date_to}'),
                ('Turi', params.get('kind') or 'barchasi'),
                ('Holati', params.get('status') or 'barchasi'),
            ],
        )

    @action(detail=False, methods=['get'])
    def summary(self, request):
        """Davr bo'yicha jamlanma — dizayndagi hisobot kartalari uchun."""
        queryset = self.filter_queryset(self.get_queryset()).filter(
            status=Document.Status.CONFIRMED
        )

        def totals(kind):
            rows = queryset.filter(kind=kind).aggregate(
                count=Count('id'),
                amount=Sum('total_amount'),
                cost=Sum('total_cost'),
            )
            amount = rows['amount'] or Decimal('0')
            cost = rows['cost'] or Decimal('0')

            return {
                'count': rows['count'],
                'amount': amount,
                'cost': cost,
                'profit': amount - cost,
            }

        purchases = totals(Document.Kind.PURCHASE)
        sales = totals(Document.Kind.SALE)

        return Response({
            'purchases': purchases,
            'sales': sales,
            # Foyda faqat sotuvda ma'noga ega: kirimda tannarx nol
            'profit': sales['profit'],
            'margin_percent': (
                round(float(sales['profit'] / sales['amount'] * 100), 1)
                if sales['amount']
                else 0.0
            ),
        })
