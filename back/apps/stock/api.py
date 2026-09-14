"""Qoldiq API si."""

from __future__ import annotations

from decimal import Decimal

from django.db.models import DecimalField, ExpressionWrapper, F, Q, Sum
from django.utils import timezone
from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.audit.mixins import Action, AuditMixin
from apps.catalog.models import Category
from apps.core.export import (
    DATE,
    DATETIME,
    MONEY,
    QUANTITY,
    TEXT,
    Column,
    build_workbook,
    context_meta,
    excel_response,
)
from apps.core.access import FinancialRedactionMixin, Perm, visible_columns
from apps.core.permissions import SectionPermission
from apps.stock.enums import MovementReason
from apps.stock.models import Batch, StockBalance, StockMovement
from apps.stock.serializers import (
    BatchSerializer,
    StockAdjustSerializer,
    StockBalanceSerializer,
    StockMovementSerializer,
    StocktakeSerializer,
)
from apps.warehouse.models import WarehouseAccess

#: SQL yig'indisi uchun chiqish turi. Nomi `MONEY`dan farq qiladi:
#: eksport ustunining turi ham shunday atalgan va ular aralashib
#: ketsa, hisobotdagi sonlar matn bo'lib qolar edi.
MONEY_OUTPUT = DecimalField(max_digits=18, decimal_places=2)


class StockBalanceViewSet(
    AuditMixin, FinancialRedactionMixin, mixins.ListModelMixin, viewsets.GenericViewSet
):
    """Qoldiqlar.

    Faqat o'qish uchun: qoldiq jurnaldan hosila, uni to'g'ridan-to'g'ri
    o'zgartirib bo'lmaydi (3-arxitektura qarori). O'zgartirish
    `adjust`, `stocktake` va hujjatlar orqali bo'ladi.
    """

    serializer_class = StockBalanceSerializer
    audit_object_type = 'stock'
    permission_classes = [SectionPermission]
    #: Qoldiq sotuv, kirim va ko'chirish formalarida ham kerak (mavjud miqdor)
    section_permissions = {
        'read': {Perm.STOCK, Perm.SALES, Perm.IMPORTS, Perm.TRANSFERS, Perm.DASHBOARD},
        'write': {Perm.STOCK},
    }
    extra_permissions = {'export': {Perm.PRINT_REPORTS}}

    def get_queryset(self):
        queryset = (
            StockBalance.objects.select_related(
                'variant__product__category', 'warehouse', 'batch'
            )
            # Nol qoldiqli qatorlar ro'yxatni to'ldirib yuboradi.
            # Ular o'chirilmaydi (jurnal tarixi uchun kerak), faqat
            # yashiriladi. Dizayn prototipida bu muammo `delete_on_deplete`
            # bilan hal qilinadi — bizda esa shunchaki filtr.
            .exclude(quantity=0)
        )

        # Ombor darajasidagi ixtiyoriy cheklov
        allowed = WarehouseAccess.visible_to(self.request.user)
        queryset = queryset.filter(warehouse__in=allowed)

        params = self.request.query_params

        if search := params.get('search', '').strip():
            queryset = queryset.filter(
                Q(variant__product__name__icontains=search)
                | Q(variant__sku__icontains=search)
                | Q(batch__code__icontains=search)
            )

        if warehouse := params.get('warehouse', '').strip():
            queryset = queryset.filter(warehouse_id=warehouse)

        if category := params.get('category', '').strip():
            node = Category.objects.filter(pk=category).first()

            if node and node.path:
                queryset = queryset.filter(
                    variant__product__category__path__descendant_of=node.path
                )
            else:
                queryset = queryset.none()

        status = params.get('status', '').strip()

        if status == 'low':
            queryset = queryset.filter(
                variant__min_stock__isnull=False,
                quantity__lte=F('variant__min_stock'),
            )
        elif status == 'expired':
            queryset = queryset.filter(
                batch__expiry_date__lt=timezone.localdate()
            )
        elif status == 'sellable':
            queryset = queryset.filter(
                warehouse__purpose__in=list(
                    self._sellable_purposes()
                ),
                warehouse__is_active=True,
            )
        elif status == 'reserved':
            queryset = queryset.filter(reserved_quantity__gt=0)

        return queryset.order_by('variant__product__name', 'warehouse__name')

    @staticmethod
    def _sellable_purposes():
        from apps.warehouse.models import Warehouse

        return Warehouse.SELLABLE_PURPOSES

    @action(detail=False, methods=['get'])
    def summary(self, request):
        """Jamlanma: pozitsiya soni, miqdor va qiymat.

        Dizayndagi qoldiqlar sahifasining tepasidagi to'rtta karta shu
        yerdan to'ldiriladi (`store/index.html`, `stockPositions` va
        boshqalar).
        """
        queryset = self.filter_queryset(self.get_queryset())

        totals = queryset.aggregate(
            positions=Sum(Decimal('1')),
            units=Sum('quantity'),
            reserved=Sum('reserved_quantity'),
            purchase_value=Sum(
                ExpressionWrapper(
                    F('quantity') * F('variant__purchase_price'),
                    output_field=MONEY_OUTPUT,
                )
            ),
            retail_value=Sum(
                ExpressionWrapper(
                    F('quantity') * F('variant__sale_price'),
                    output_field=MONEY_OUTPUT,
                )
            ),
        )

        low_count = queryset.filter(
            variant__min_stock__isnull=False, quantity__lte=F('variant__min_stock')
        ).count()

        expired_count = queryset.filter(
            batch__expiry_date__lt=timezone.localdate()
        ).count()

        # Haqiqiy tannarx FIFO qatlamlaridan. `qoldiq × joriy narx`
        # turli narxdagi partiyalar bo'lganda noto'g'ri javob beradi.
        from apps.pricing.services import stock_value

        cost_value = stock_value()

        return Response({
            'positions': queryset.count(),
            'cost_value': cost_value,
            'units': totals['units'] or Decimal('0'),
            'reserved': totals['reserved'] or Decimal('0'),
            'purchase_value': totals['purchase_value'] or Decimal('0'),
            'retail_value': totals['retail_value'] or Decimal('0'),
            'low_count': low_count,
            'expired_count': expired_count,
        })

    @action(detail=False, methods=['post'])
    def adjust(self, request):
        """Qo'lda kirim yoki chiqim qo'shadi."""
        serializer = StockAdjustSerializer(
            data=request.data, context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        movement = serializer.save()

        self.audit(
            Action.ADJUST,
            movement.variant,
            warehouse=movement.warehouse,
            details=f'{movement.quantity:+} · {movement.get_reason_display()}',
        )

        return Response(StockMovementSerializer(movement).data, status=201)

    @action(detail=False, methods=['post'])
    def stocktake(self, request):
        """Inventarizatsiya natijasini qabul qiladi."""
        serializer = StocktakeSerializer(
            data=request.data, context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        movement = serializer.save()

        if movement is None:
            return Response({'detail': 'Farq yo\'q, tuzatish kerak emas.'})

        self.audit(
            Action.STOCKTAKE,
            movement.variant,
            warehouse=movement.warehouse,
            details=f'Farq: {movement.quantity:+}',
        )

        return Response(StockMovementSerializer(movement).data, status=201)

    @action(detail=False, methods=['get'])
    def export(self, request):
        """Qoldiqlarni Excel'ga chiqaradi — joriy filtrlar bilan."""
        rows = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(rows, many=True)

        columns = [
            Column('product_name', 'Mahsulot', TEXT, width=30),
            Column('sku', 'SKU', TEXT, width=16),
            Column('variant_name', 'Variant', TEXT, width=16),
            Column('category_name', 'Kategoriya', TEXT),
            Column('warehouse_name', 'Ombor', TEXT),
            Column('batch_code', 'Partiya', TEXT, width=16),
            Column('expiry_date', 'Yaroqlilik muddati', DATE),
            Column('quantity', 'Qoldiq', QUANTITY),
            Column('unit', 'Birlik', TEXT, width=10),
            Column('reserved_quantity', 'Band', QUANTITY),
            Column('available_quantity', 'Mavjud', QUANTITY),
            Column('avg_unit_cost', 'Birlik tannarxi', MONEY),
            Column('cost_value', 'Tannarx (FIFO)', MONEY),
            Column('sale_price', 'Sotuv narxi', MONEY),
        ]

        columns = visible_columns(columns, request.membership)

        workbook = build_workbook(
            columns,
            serializer.data,
            sheet_name='Qoldiqlar',
            title='Ombor qoldiqlari',
            meta=context_meta(
                request, warehouse_id=request.query_params.get('warehouse')
            ),
        )

        return excel_response(workbook, 'qoldiqlar')

    @action(detail=False, methods=['get'])
    def reasons(self, request):
        """Harakat sabablari ro'yxati — formalar uchun."""
        return Response([
            {
                'value': value,
                'label': str(label),
                'direction': (
                    'in' if value in MovementReason.inbound()
                    else 'out' if value in MovementReason.outbound()
                    else 'both'
                ),
                'is_loss': MovementReason.is_loss(value),
            }
            for value, label in MovementReason.choices
        ])


class _MovementExportMixin:
    """Jurnalni Excel'ga chiqarish."""

    @action(detail=False, methods=['get'])
    def export(self, request):
        rows = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(rows, many=True)

        columns = [
            Column('occurred_at', 'Sana', DATETIME),
            Column('product_name', 'Mahsulot', TEXT, width=30),
            Column('sku', 'SKU', TEXT, width=16),
            Column('warehouse_name', 'Ombor', TEXT),
            Column('batch_code', 'Partiya', TEXT, width=16),
            Column('quantity', 'Miqdor', QUANTITY),
            Column('reason_display', 'Sababi', TEXT, width=28),
            Column('unit_cost', 'Birlik tannarxi', MONEY),
            Column('document_type', 'Hujjat turi', TEXT, width=14),
            Column('document_id', 'Hujjat', TEXT, width=10),
            Column('user_name', 'Kim', TEXT),
            Column('note', 'Izoh', TEXT, width=30),
        ]

        columns = visible_columns(columns, request.membership)

        workbook = build_workbook(
            columns,
            serializer.data,
            sheet_name='Harakatlar',
            title='Qoldiq harakatlari jurnali',
            meta=context_meta(
                request, warehouse_id=request.query_params.get('warehouse')
            ),
        )

        return excel_response(workbook, 'harakatlar')


class StockMovementViewSet(
    FinancialRedactionMixin,
    _MovementExportMixin,
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    """Harakatlar jurnali — faqat o'qish.

    Yozuvni o'zgartirish va o'chirish baza triggeri bilan taqiqlangan,
    shuning uchun API da ham bunday amallar yo'q.
    """

    serializer_class = StockMovementSerializer
    permission_classes = [SectionPermission]
    section_permissions = {'read': {Perm.STOCK, Perm.HISTORY}}
    extra_permissions = {'export': {Perm.PRINT_REPORTS}}

    def get_queryset(self):
        queryset = StockMovement.objects.select_related(
            'variant__product', 'warehouse', 'batch', 'created_by'
        )

        allowed = WarehouseAccess.visible_to(self.request.user)
        queryset = queryset.filter(warehouse__in=allowed)

        params = self.request.query_params

        if variant := params.get('variant', '').strip():
            queryset = queryset.filter(variant_id=variant)

        if warehouse := params.get('warehouse', '').strip():
            queryset = queryset.filter(warehouse_id=warehouse)

        if reason := params.get('reason', '').strip():
            queryset = queryset.filter(reason=reason)

        if date_from := params.get('date_from', '').strip():
            queryset = queryset.filter(occurred_at__date__gte=date_from)

        if date_to := params.get('date_to', '').strip():
            queryset = queryset.filter(occurred_at__date__lte=date_to)

        return queryset


class BatchViewSet(AuditMixin, viewsets.ModelViewSet):
    """Partiyalar: kod va yaroqlilik muddati."""

    serializer_class = BatchSerializer
    audit_object_type = 'batch'
    permission_classes = [SectionPermission]
    section_permissions = {
        'read': {Perm.STOCK, Perm.IMPORTS, Perm.SALES, Perm.TRANSFERS},
        'write': {Perm.IMPORTS, Perm.STOCK},
    }

    def get_queryset(self):
        queryset = Batch.objects.select_related('variant__product')

        params = self.request.query_params

        if variant := params.get('variant', '').strip():
            queryset = queryset.filter(variant_id=variant)

        if params.get('expiring', '').strip() == 'true':
            queryset = queryset.filter(expiry_date__isnull=False).order_by('expiry_date')

        return queryset
