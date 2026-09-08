"""Qoldiq serializerlari."""

from __future__ import annotations

from decimal import Decimal

from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from apps.stock import services
from apps.stock.models import Batch, StockBalance, StockMovement


class BatchSerializer(serializers.ModelSerializer):
    is_expired = serializers.BooleanField(read_only=True)
    days_left = serializers.IntegerField(read_only=True, allow_null=True)

    class Meta:
        model = Batch
        fields = (
            'id', 'variant', 'code', 'expiry_date', 'produced_at',
            'note', 'is_expired', 'days_left',
        )
        read_only_fields = ('id', 'is_expired', 'days_left')


class StockBalanceSerializer(serializers.ModelSerializer):
    """Qoldiq qatori — ro'yxat uchun."""

    product_name = serializers.CharField(source='variant.product.name', read_only=True)
    variant_name = serializers.CharField(source='variant.name', read_only=True)
    sku = serializers.CharField(source='variant.sku', read_only=True)
    unit = serializers.CharField(source='variant.product.effective_unit', read_only=True)
    category_name = serializers.CharField(
        source='variant.product.category.name', read_only=True
    )

    warehouse_name = serializers.CharField(source='warehouse.name', read_only=True)
    warehouse_purpose = serializers.CharField(source='warehouse.purpose', read_only=True)

    batch_code = serializers.CharField(source='batch.code', read_only=True, default=None)
    expiry_date = serializers.DateField(
        source='batch.expiry_date', read_only=True, default=None
    )
    is_expired = serializers.SerializerMethodField()

    available_quantity = serializers.DecimalField(
        max_digits=18, decimal_places=3, read_only=True
    )
    is_sellable = serializers.BooleanField(read_only=True)
    is_overallocated = serializers.BooleanField(read_only=True)

    #: Kam qolgan tovarni ajratish uchun (dizayndagi "lowStock")
    is_low = serializers.SerializerMethodField()

    purchase_price = serializers.DecimalField(
        source='variant.purchase_price', max_digits=18, decimal_places=2,
        read_only=True, allow_null=True,
    )
    sale_price = serializers.DecimalField(
        source='variant.sale_price', max_digits=18, decimal_places=2,
        read_only=True, allow_null=True,
    )

    class Meta:
        model = StockBalance
        fields = (
            'id', 'variant', 'product_name', 'variant_name', 'sku', 'unit',
            'category_name', 'warehouse', 'warehouse_name', 'warehouse_purpose',
            'batch', 'batch_code', 'expiry_date', 'is_expired',
            'quantity', 'reserved_quantity', 'available_quantity',
            'is_sellable', 'is_overallocated', 'is_low',
            'purchase_price', 'sale_price',
        )

    def get_is_expired(self, obj) -> bool:
        return bool(obj.batch and obj.batch.is_expired)

    def get_is_low(self, obj) -> bool:
        minimum = obj.variant.min_stock

        return bool(minimum is not None and obj.quantity <= minimum)


class StockMovementSerializer(serializers.ModelSerializer):
    """Jurnal yozuvi — faqat o'qish uchun.

    Yozuvni API orqali o'zgartirib yoki o'chirib bo'lmaydi: jurnal
    append-only (3-arxitektura qarori). Yangi yozuv `adjust`, `transfer`
    va shunga o'xshash amallar orqali qo'shiladi.
    """

    product_name = serializers.CharField(source='variant.product.name', read_only=True)
    sku = serializers.CharField(source='variant.sku', read_only=True)
    warehouse_name = serializers.CharField(source='warehouse.name', read_only=True)
    batch_code = serializers.CharField(source='batch.code', read_only=True, default=None)
    reason_display = serializers.CharField(source='get_reason_display', read_only=True)
    user_name = serializers.CharField(
        source='created_by.get_full_name', read_only=True, default=''
    )

    class Meta:
        model = StockMovement
        fields = (
            'id', 'variant', 'product_name', 'sku',
            'warehouse', 'warehouse_name', 'batch', 'batch_code',
            'quantity', 'reason', 'reason_display',
            'unit_cost', 'currency', 'document_type', 'document_id',
            'note', 'meta', 'occurred_at', 'user_name',
        )
        read_only_fields = fields


class StockAdjustSerializer(serializers.Serializer):
    """Qo'lda kirim yoki chiqim."""

    variant = serializers.IntegerField()
    warehouse = serializers.IntegerField()
    batch = serializers.IntegerField(required=False, allow_null=True)
    quantity = serializers.DecimalField(max_digits=18, decimal_places=3)
    reason = serializers.CharField()
    note = serializers.CharField(required=False, allow_blank=True)

    def create(self, validated_data):
        from apps.catalog.models import Variant
        from apps.warehouse.models import Warehouse

        request = self.context['request']

        try:
            return services.record_movement(
                variant=Variant.objects.get(pk=validated_data['variant']),
                warehouse=Warehouse.objects.get(pk=validated_data['warehouse']),
                batch=(
                    Batch.objects.get(pk=validated_data['batch'])
                    if validated_data.get('batch')
                    else None
                ),
                quantity=Decimal(validated_data['quantity']),
                reason=validated_data['reason'],
                note=validated_data.get('note', ''),
                user=request.user,
            )
        except DjangoValidationError as exc:
            raise serializers.ValidationError({'detail': exc.messages})


class StocktakeSerializer(serializers.Serializer):
    """Inventarizatsiya: sanalgan miqdorni yuborish."""

    variant = serializers.IntegerField()
    warehouse = serializers.IntegerField()
    batch = serializers.IntegerField(required=False, allow_null=True)
    counted_quantity = serializers.DecimalField(max_digits=18, decimal_places=3)
    note = serializers.CharField(required=False, allow_blank=True)

    def create(self, validated_data):
        from apps.catalog.models import Variant
        from apps.warehouse.models import Warehouse

        request = self.context['request']

        try:
            return services.stocktake(
                variant=Variant.objects.get(pk=validated_data['variant']),
                warehouse=Warehouse.objects.get(pk=validated_data['warehouse']),
                batch=(
                    Batch.objects.get(pk=validated_data['batch'])
                    if validated_data.get('batch')
                    else None
                ),
                counted_quantity=Decimal(validated_data['counted_quantity']),
                note=validated_data.get('note', ''),
                user=request.user,
            )
        except DjangoValidationError as exc:
            raise serializers.ValidationError({'detail': exc.messages})
