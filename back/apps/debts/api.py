"""Qarzdorlar API si."""

from __future__ import annotations

from decimal import Decimal

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import Count, DecimalField, ExpressionWrapper, F, Q, Sum
from django.db.models.functions import Coalesce
from django.utils import timezone
from rest_framework import mixins, serializers, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.audit.mixins import Action, AuditMixin
from apps.core.access import Perm
from apps.core.export import (
    DATE,
    MONEY,
    NUMBER,
    TEXT,
    Column,
    build_workbook,
    context_meta,
    excel_response,
)
from apps.core.permissions import SectionPermission
from apps.debts import services
from apps.debts.models import Debt, DebtPayment
from apps.warehouse.models import WarehouseAccess

MONEY_OUTPUT = DecimalField(max_digits=18, decimal_places=2)
ZERO = Decimal('0')


class DebtPaymentSerializer(serializers.ModelSerializer):
    method_display = serializers.CharField(source='get_method_display', read_only=True)

    class Meta:
        model = DebtPayment
        fields = (
            'id', 'amount', 'method', 'method_display', 'paid_at', 'note', 'created_by_name',
        )
        read_only_fields = fields


class DebtSerializer(serializers.ModelSerializer):
    document_number = serializers.CharField(source='document.number', read_only=True)
    warehouse_name = serializers.CharField(source='warehouse.name', read_only=True)
    partner_name = serializers.CharField(source='partner.name', read_only=True, default=None)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    display_status = serializers.CharField(read_only=True)
    customer_type = serializers.CharField(read_only=True)
    is_overdue = serializers.BooleanField(read_only=True)
    overdue_days = serializers.IntegerField(read_only=True)
    remaining = serializers.DecimalField(max_digits=18, decimal_places=2, read_only=True)
    markup_amount = serializers.DecimalField(max_digits=18, decimal_places=2, read_only=True)
    payments = DebtPaymentSerializer(many=True, read_only=True)

    class Meta:
        model = Debt
        fields = (
            'id', 'number', 'document', 'document_number',
            'warehouse', 'warehouse_name', 'partner', 'partner_name', 'customer_type',
            'customer_name', 'customer_phone', 'customer_document',
            'issued_date', 'due_date', 'is_overdue', 'overdue_days',
            'base_amount', 'markup_percent', 'markup_amount', 'amount',
            'paid_amount', 'remaining', 'currency',
            'status', 'status_display', 'display_status', 'paid_at', 'note',
            'payments',
        )
        read_only_fields = fields


class PaymentInputSerializer(serializers.Serializer):
    amount = serializers.DecimalField(
        max_digits=18, decimal_places=2, min_value=Decimal('0.01')
    )
    method = serializers.ChoiceField(
        choices=DebtPayment.Method.choices, default=DebtPayment.Method.CASH
    )
    note = serializers.CharField(required=False, allow_blank=True, max_length=250)
    #: Interfeys har ochilgan to'lov oynasi uchun bitta kalit yaratadi
    request_key = serializers.CharField(required=False, allow_blank=True, max_length=64)


class DebtViewSet(
    AuditMixin, mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet
):
    """Qarzdorlar.

    Qarz sotuv hujjati tasdiqlanganda avtomatik yaratiladi — bu yerdan
    qarz qo'shib yoki o'chirib bo'lmaydi. Bu yerda faqat ko'rish va
    to'lov qabul qilish.
    """

    serializer_class = DebtSerializer
    audit_object_type = 'debt'
    permission_classes = [SectionPermission]
    section_permissions = {'read': {Perm.DEBTORS}}
    extra_permissions = {'export': {Perm.PRINT_REPORTS}}
    queryset = Debt.objects.none()

    def _base_queryset(self):
        """Holat filtrisiz queryset — ro'yxat va jamlanma uchun umumiy."""
        queryset = Debt.objects.select_related(
            'document', 'warehouse', 'partner'
        ).prefetch_related('payments')

        allowed = WarehouseAccess.visible_to(self.request.user)
        queryset = queryset.filter(warehouse__in=allowed)

        params = self.request.query_params

        if search := params.get('search', '').strip():
            queryset = queryset.filter(
                Q(number__icontains=search)
                | Q(document__number__icontains=search)
                | Q(customer_name__icontains=search)
                | Q(customer_phone__icontains=search)
                | Q(customer_document__icontains=search)
            )

        if warehouse := params.get('warehouse', '').strip():
            queryset = queryset.filter(warehouse_id=warehouse)

        if partner := params.get('partner', '').strip():
            queryset = queryset.filter(partner_id=partner)

        customer_type = params.get('customer_type', '').strip()

        if customer_type == 'retail':
            queryset = queryset.filter(partner__isnull=True)
        elif customer_type == 'counterparty':
            queryset = queryset.filter(partner__isnull=False)

        return queryset

    def get_queryset(self):
        queryset = self._base_queryset()
        status_value = self.request.query_params.get('status', '').strip()

        if status_value == Debt.OVERDUE:
            queryset = queryset.filter(
                status=Debt.Status.ACTIVE, due_date__lt=timezone.localdate()
            )
        elif status_value:
            queryset = queryset.filter(status=status_value)

        return queryset.order_by('status', 'due_date', 'id')

    @action(detail=False, methods=['get'])
    def summary(self, request):
        """Beshta ko'rsatkich — holat filtrisiz (qolgan filtrlar amal qiladi)."""
        queryset = self._base_queryset()
        today = timezone.localdate()

        remaining = ExpressionWrapper(
            F('amount') - F('paid_amount'), output_field=MONEY_OUTPUT
        )
        active = Q(status=Debt.Status.ACTIVE)
        overdue = active & Q(due_date__lt=today)

        totals = queryset.aggregate(
            active_count=Count('id', filter=active),
            active_amount=Coalesce(
                Sum(remaining, filter=active), ZERO, output_field=MONEY_OUTPUT
            ),
            overdue_count=Count('id', filter=overdue),
            overdue_amount=Coalesce(
                Sum(remaining, filter=overdue), ZERO, output_field=MONEY_OUTPUT
            ),
            paid_amount=Coalesce(
                Sum('paid_amount', filter=~Q(status=Debt.Status.CANCELLED)),
                ZERO,
                output_field=MONEY_OUTPUT,
            ),
        )

        return Response(totals)

    @action(detail=True, methods=['post'])
    def pay(self, request, pk=None):
        """To'lov qabul qiladi. Qisman to'lov mumkin; qoldiqdan ko'p — yo'q."""
        debt = self.get_object()

        serializer = PaymentInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            payment, created = services.pay(
                debt,
                amount=data['amount'],
                method=data['method'],
                note=data.get('note', ''),
                request_key=data.get('request_key', ''),
                user=request.user,
            )
        except DjangoValidationError as exc:
            return Response({'detail': exc.messages}, status=400)

        debt = self._base_queryset().get(pk=debt.pk)

        # Takroriy so'rov (bir xil kalit) avvalgi to'lovni qaytaradi —
        # tarixga u ikkinchi marta yozilmasligi kerak
        if created:
            self.audit(
                Action.PAYMENT,
                debt,
                details=(
                    f'{payment.amount} ({payment.get_method_display()}), '
                    f'qoldiq {debt.remaining}'
                ),
            )

        return Response(DebtSerializer(debt).data)

    EXPORT_COLUMNS = [
        Column('number', 'Qarz', TEXT, width=16),
        Column('document_number', 'Sotuv', TEXT, width=16),
        Column('customer_name', 'Mijoz', TEXT, width=28),
        Column('customer_phone', 'Telefon', TEXT, width=16),
        Column('warehouse_name', 'Ombor', TEXT),
        Column('issued_date', 'Qarz sanasi', DATE),
        Column('due_date', 'Muddati', DATE),
        Column('overdue_days', 'Kechikkan kun', NUMBER),
        Column('base_amount', 'Asosiy summa', MONEY),
        Column('markup_amount', 'Ustama', MONEY),
        Column('amount', 'Qarz summasi', MONEY),
        Column('paid_amount', 'To‘langan', MONEY),
        Column('remaining', 'Qoldiq', MONEY),
        Column('status_display', 'Holati', TEXT, width=14),
    ]

    @action(detail=False, methods=['get'])
    def export(self, request):
        """Qarzdorlar ro'yxati — joriy filtrlar bilan."""
        rows = self.get_serializer(self.get_queryset(), many=True).data

        workbook = build_workbook(
            self.EXPORT_COLUMNS,
            rows,
            sheet_name='Qarzdorlar',
            title='Qarzdorlar',
            meta=context_meta(request, warehouse_id=request.query_params.get('warehouse')),
        )

        return excel_response(workbook, 'qarzdorlar')
