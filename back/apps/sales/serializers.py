from rest_framework import serializers

from apps.catalog.models import Variant
from apps.core.redaction import HideFromCashierMixin
from apps.sales.models import Sale, SaleLine, SaleReturn, SaleReturnLine


class SaleLineSerializer(HideFromCashierMixin, serializers.ModelSerializer):
    """Chek qatori. Tannarx va foyda — faqat administratorga."""

    admin_only_fields = ('unit_cost', 'line_cost', 'profit')

    product_name = serializers.CharField(source='variant.product.name', read_only=True)
    variant_label = serializers.CharField(source='variant.label', read_only=True)
    sku = serializers.CharField(source='variant.sku', read_only=True)
    barcode = serializers.CharField(source='variant.barcode', read_only=True)
    profit = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)
    returned_quantity = serializers.SerializerMethodField()

    class Meta:
        model = SaleLine
        fields = (
            'id', 'variant', 'product_name', 'variant_label', 'sku', 'barcode',
            'quantity', 'unit_price', 'discount_amount', 'line_total', 'unit_cost',
            'line_cost', 'profit', 'returned_quantity',
        )

    def get_returned_quantity(self, obj) -> int:
        from apps.sales.services import returned_quantity

        return returned_quantity(obj)


class SaleSerializer(HideFromCashierMixin, serializers.ModelSerializer):
    """Chek (o'qish uchun)."""

    admin_only_fields = ('profit',)

    lines = SaleLineSerializer(many=True, read_only=True)
    cashier_name = serializers.CharField(source='cashier.username', read_only=True, default=None)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    profit = serializers.SerializerMethodField()

    class Meta:
        model = Sale
        fields = (
            'id', 'number', 'created_at', 'cashier', 'cashier_name', 'subtotal',
            'discount_total', 'total', 'cash_amount', 'card_amount', 'status',
            'status_display', 'voided_at', 'fiscal_receipt_id', 'fiscal_qr_url', 'lines',
            'profit',
        )

    def get_profit(self, obj) -> str:
        total_cost = sum(line.line_cost for line in obj.lines.all())

        return str(obj.total - total_cost)


class SaleLineInputSerializer(serializers.Serializer):
    """Kassadan keladigan qator."""

    variant = serializers.PrimaryKeyRelatedField(queryset=Variant.objects.all())
    quantity = serializers.IntegerField(min_value=1)
    unit_price = serializers.DecimalField(
        max_digits=14, decimal_places=2, required=False, allow_null=True
    )
    discount_amount = serializers.DecimalField(
        max_digits=14, decimal_places=2, required=False, allow_null=True
    )
    discount_percent = serializers.DecimalField(
        max_digits=5, decimal_places=2, required=False, allow_null=True
    )


class SaleCreateSerializer(serializers.Serializer):
    """Sotuvni yaratish: bitta so'rovda yoziladi va tasdiqlanadi."""

    lines = SaleLineInputSerializer(many=True)
    discount_amount = serializers.DecimalField(
        max_digits=14, decimal_places=2, required=False, allow_null=True
    )
    discount_percent = serializers.DecimalField(
        max_digits=5, decimal_places=2, required=False, allow_null=True
    )
    cash_amount = serializers.DecimalField(max_digits=14, decimal_places=2, default=0)
    card_amount = serializers.DecimalField(max_digits=14, decimal_places=2, default=0)

    #: Takroriy yuborishdan himoya
    request_key = serializers.UUIDField(required=False, allow_null=True)


class SaleReturnLineSerializer(HideFromCashierMixin, serializers.ModelSerializer):
    admin_only_fields = ('unit_cost',)

    product_name = serializers.CharField(
        source='sale_line.variant.product.name', read_only=True
    )
    variant_label = serializers.CharField(source='sale_line.variant.label', read_only=True)
    sku = serializers.CharField(source='sale_line.variant.sku', read_only=True)

    class Meta:
        model = SaleReturnLine
        fields = (
            'id', 'sale_line', 'product_name', 'variant_label', 'sku',
            'quantity', 'unit_cost', 'refund_amount',
        )


class SaleReturnSerializer(serializers.ModelSerializer):
    lines = SaleReturnLineSerializer(many=True, read_only=True)
    sale_number = serializers.CharField(source='sale.number', read_only=True)
    refund_method_display = serializers.CharField(
        source='get_refund_method_display', read_only=True
    )

    class Meta:
        model = SaleReturn
        fields = (
            'id', 'number', 'created_at', 'sale', 'sale_number', 'total',
            'refund_method', 'refund_method_display', 'fiscal_receipt_id',
            'fiscal_qr_url', 'lines',
        )


class ReturnItemSerializer(serializers.Serializer):
    sale_line = serializers.PrimaryKeyRelatedField(queryset=SaleLine.objects.all())
    quantity = serializers.IntegerField(min_value=1)


class SaleReturnCreateSerializer(serializers.Serializer):
    sale = serializers.PrimaryKeyRelatedField(queryset=Sale.objects.all())
    items = ReturnItemSerializer(many=True)
    refund_method = serializers.ChoiceField(
        choices=SaleReturn.RefundMethod.choices, default=SaleReturn.RefundMethod.CASH
    )
    request_key = serializers.UUIDField(required=False, allow_null=True)


class ExchangeSerializer(SaleReturnCreateSerializer):
    """Almashtirish: qaytariladigan qatorlar va yangi sotuv qatorlari."""

    lines = SaleLineInputSerializer(many=True)
    discount_amount = serializers.DecimalField(
        max_digits=14, decimal_places=2, required=False, allow_null=True
    )
    discount_percent = serializers.DecimalField(
        max_digits=5, decimal_places=2, required=False, allow_null=True
    )
    cash_amount = serializers.DecimalField(max_digits=14, decimal_places=2, default=0)
    card_amount = serializers.DecimalField(max_digits=14, decimal_places=2, default=0)
