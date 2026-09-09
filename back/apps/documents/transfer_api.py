"""Ko'chirish API si."""

from __future__ import annotations

from decimal import Decimal

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.db.models import Q
from rest_framework import serializers, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.catalog.models import Variant
from apps.core.permissions import IsTenantMemberOrReadOnly
from apps.documents import transfer_services as services
from apps.documents.transfer_models import Transfer, TransferLine
from apps.stock.models import Batch
from apps.warehouse.models import Warehouse, WarehouseAccess


class TransferLineSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='variant.product.name', read_only=True)
    sku = serializers.CharField(source='variant.sku', read_only=True)
    base_unit = serializers.CharField(
        source='variant.product.effective_unit', read_only=True
    )
    batch_code = serializers.CharField(source='batch.code', read_only=True, default=None)
    shortfall = serializers.DecimalField(
        max_digits=18, decimal_places=3, read_only=True
    )
    is_complete = serializers.BooleanField(read_only=True)

    class Meta:
        model = TransferLine
        fields = (
            'id', 'variant', 'product_name', 'sku', 'batch', 'batch_code',
            'unit', 'base_unit', 'factor',
            'quantity_sent', 'quantity_sent_base',
            'quantity_received', 'quantity_received_base',
            'shortfall', 'is_complete', 'note', 'position',
        )
        read_only_fields = fields


class TransferLineInputSerializer(serializers.Serializer):
    variant = serializers.IntegerField()
    batch = serializers.IntegerField(required=False, allow_null=True)
    unit = serializers.CharField(required=False, allow_blank=True)
    quantity = serializers.DecimalField(max_digits=18, decimal_places=3)
    note = serializers.CharField(required=False, allow_blank=True)


class TransferSerializer(serializers.ModelSerializer):
    lines = TransferLineSerializer(many=True, read_only=True)
    items = TransferLineInputSerializer(many=True, write_only=True, required=False)

    status_display = serializers.CharField(source='get_status_display', read_only=True)
    from_warehouse_name = serializers.CharField(
        source='from_warehouse.name', read_only=True
    )
    to_warehouse_name = serializers.CharField(source='to_warehouse.name', read_only=True)
    transit_warehouse_name = serializers.CharField(
        source='transit_warehouse.name', read_only=True
    )
    is_editable = serializers.BooleanField(read_only=True)
    in_transit = serializers.BooleanField(read_only=True)
    has_shortfall = serializers.BooleanField(read_only=True)
    total_shortfall = serializers.DecimalField(
        max_digits=18, decimal_places=3, read_only=True
    )
    line_count = serializers.SerializerMethodField()

    class Meta:
        model = Transfer
        fields = (
            'id', 'number', 'date', 'status', 'status_display',
            'from_warehouse', 'from_warehouse_name',
            'to_warehouse', 'to_warehouse_name',
            'transit_warehouse', 'transit_warehouse_name',
            'note', 'is_editable', 'in_transit',
            'has_shortfall', 'total_shortfall',
            'sent_at', 'received_at', 'cancelled_at',
            'lines', 'items', 'line_count',
        )
        read_only_fields = (
            'id', 'number', 'status', 'status_display', 'is_editable', 'in_transit',
            'has_shortfall', 'total_shortfall', 'sent_at', 'received_at',
            'cancelled_at', 'lines', 'line_count',
            'from_warehouse_name', 'to_warehouse_name', 'transit_warehouse_name',
        )

    def get_line_count(self, obj) -> int:
        return obj.lines.count()

    def validate(self, attrs):
        instance = self.instance or Transfer()

        for field, value in attrs.items():
            if field != 'items':
                setattr(instance, field, value)

        instance.tenant_id = self.context['request'].tenant_id

        try:
            instance.clean()
        except DjangoValidationError as exc:
            raise serializers.ValidationError(
                exc.message_dict if hasattr(exc, 'message_dict') else exc.messages
            )

        return attrs

    @transaction.atomic
    def create(self, validated_data):
        items = validated_data.pop('items', [])
        request = self.context['request']

        transfer = Transfer.objects.create(
            **validated_data,
            number=services.next_number(validated_data.get('date')),
            created_by=request.user,
        )

        self._replace_lines(transfer, items)

        return transfer

    @transaction.atomic
    def update(self, instance, validated_data):
        items = validated_data.pop('items', None)

        if not instance.is_editable:
            raise serializers.ValidationError({
                'detail': 'Jo\'natilgan ko\'chirishni tahrirlab bo\'lmaydi.'
            })

        for field, value in validated_data.items():
            setattr(instance, field, value)

        instance.save()

        if items is not None:
            self._replace_lines(instance, items)

        return instance

    def _replace_lines(self, transfer: Transfer, items: list) -> None:
        transfer.lines.all().delete()

        for position, item in enumerate(items, start=1):
            try:
                services.build_line(
                    transfer,
                    variant=Variant.objects.get(pk=item['variant']),
                    quantity=item['quantity'],
                    unit=item.get('unit', ''),
                    batch=(
                        Batch.objects.get(pk=item['batch'])
                        if item.get('batch')
                        else None
                    ),
                    note=item.get('note', ''),
                    position=position,
                )
            except DjangoValidationError as exc:
                raise serializers.ValidationError({'items': exc.messages})
            except Variant.DoesNotExist:
                raise serializers.ValidationError({
                    'items': [f'Mahsulot topilmadi: {item["variant"]}']
                })


class TransferViewSet(viewsets.ModelViewSet):
    """Omborlararo ko'chirish — ikki bosqichli.

    `send` va `receive` alohida amallar: ular orasida kunlar o'tishi
    mumkin va har biri qoldiqni o'zgartiradi.
    """

    serializer_class = TransferSerializer
    permission_classes = [IsTenantMemberOrReadOnly]
    queryset = Transfer.objects.none()

    def get_queryset(self):
        queryset = (
            Transfer.objects.select_related(
                'from_warehouse', 'to_warehouse', 'transit_warehouse'
            )
            .prefetch_related('lines__variant__product')
        )

        # Ko'chirish ikki omborga tegishli — foydalanuvchi ikkalasidan
        # birini ko'rsa, hujjat unga ko'rinadi
        allowed = WarehouseAccess.visible_to(self.request.user)
        queryset = queryset.filter(
            Q(from_warehouse__in=allowed) | Q(to_warehouse__in=allowed)
        )

        params = self.request.query_params

        if status_value := params.get('status', '').strip():
            queryset = queryset.filter(status=status_value)

        if warehouse := params.get('warehouse', '').strip():
            queryset = queryset.filter(
                Q(from_warehouse_id=warehouse) | Q(to_warehouse_id=warehouse)
            )

        if search := params.get('search', '').strip():
            queryset = queryset.filter(number__icontains=search)

        return queryset

    @action(detail=True, methods=['post'])
    def send(self, request, pk=None):
        """Jo'natish: tovar tranzit omborga o'tadi."""
        transfer = self.get_object()

        try:
            services.send(transfer, user=request.user)
        except DjangoValidationError as exc:
            return Response({'detail': exc.messages}, status=400)

        return Response(self.get_serializer(self._reload(transfer)).data)

    @action(detail=True, methods=['post'])
    def receive(self, request, pk=None):
        """Qabul qilish. Kamomad bo'lsa alohida yoziladi.

        Kutilgan tana: `{"received": {"<qator_id>": "185"}}`.
        Ko'rsatilmagan qator to'liq qabul qilingan deb hisoblanadi.
        """
        transfer = self.get_object()

        raw = request.data.get('received') or {}

        try:
            received = {int(key): Decimal(str(value)) for key, value in raw.items()}
        except (TypeError, ValueError):
            return Response({'detail': ['Miqdorlar noto\'g\'ri formatda.']}, status=400)

        try:
            services.receive(transfer, received=received, user=request.user)
        except DjangoValidationError as exc:
            return Response({'detail': exc.messages}, status=400)

        return Response(self.get_serializer(self._reload(transfer)).data)

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """Bekor qilish. Yo'ldagi tovar manba omborga qaytariladi."""
        transfer = self.get_object()

        try:
            services.cancel(transfer, user=request.user)
        except DjangoValidationError as exc:
            return Response({'detail': exc.messages}, status=400)

        return Response(self.get_serializer(self._reload(transfer)).data)

    def _reload(self, transfer):
        """Obyektni bazadan qayta o'qiydi — prefetch keshi eskirgan bo'ladi."""
        return self.get_queryset().get(pk=transfer.pk)

    @action(detail=False, methods=['get'], url_path='transit-warehouses')
    def transit_warehouses(self, request):
        """Tranzit vazifasidagi omborlar — forma uchun."""
        rows = Warehouse.objects.filter(
            purpose=Warehouse.Purpose.TRANSIT, is_active=True
        ).values('id', 'name', 'code')

        return Response(list(rows))
