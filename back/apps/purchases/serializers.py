from django.db import transaction
from rest_framework import serializers

from apps.core.numbering import next_number
from apps.purchases.models import Purchase, PurchaseLine, Supplier, SupplierPayment
from apps.purchases.services import recalculate_total, supplier_balance


class SupplierSerializer(serializers.ModelSerializer):
    balance = serializers.SerializerMethodField()

    class Meta:
        model = Supplier
        fields = ('id', 'name', 'phone', 'note', 'is_active', 'balance')

    def get_balance(self, obj) -> str:
        return str(supplier_balance(obj))


class SupplierPaymentSerializer(serializers.ModelSerializer):
    supplier_name = serializers.CharField(source='supplier.name', read_only=True)

    class Meta:
        model = SupplierPayment
        fields = ('id', 'supplier', 'supplier_name', 'date', 'amount', 'note', 'created_at')
        read_only_fields = ('id', 'created_at')

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError('Summa noldan katta bo‘lishi kerak.')

        return value


class PurchaseLineSerializer(serializers.ModelSerializer):
    #: Qoralamani qayta ochganda qatorlar model bo'yicha guruhlanadi —
    #: interfeys o'lcham × rang katakchasini shu maydondan tiklaydi
    product = serializers.IntegerField(source='variant.product_id', read_only=True)

    product_name = serializers.CharField(source='variant.product.name', read_only=True)
    variant_label = serializers.CharField(source='variant.label', read_only=True)

    #: Ochilgan hujjatda qatorlar model bo'yicha o'lcham × rang
    #: katakchasiga yig'iladi — nomlar shu yerdan olinadi
    size = serializers.IntegerField(source='variant.size_id', read_only=True)
    size_name = serializers.CharField(source='variant.size.name', read_only=True, default=None)
    color = serializers.IntegerField(source='variant.color_id', read_only=True)
    color_name = serializers.CharField(source='variant.color.name', read_only=True, default=None)
    sku = serializers.CharField(source='variant.sku', read_only=True)
    barcode = serializers.CharField(source='variant.barcode', read_only=True)

    #: Yorliqda chiqadigan narx. Usiz interfeys har qator uchun alohida
    #: so'rov yuborib variantni qidirardi.
    price = serializers.DecimalField(
        source='variant.price', max_digits=14, decimal_places=2, read_only=True
    )

    line_total = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)

    class Meta:
        model = PurchaseLine
        fields = (
            'id', 'variant', 'product', 'product_name', 'variant_label',
            'size', 'size_name', 'color', 'color_name', 'sku', 'barcode',
            'price', 'quantity', 'unit_cost', 'new_sale_price', 'line_total',
        )
        read_only_fields = ('id',)

    def validate_quantity(self, value):
        if value <= 0:
            raise serializers.ValidationError('Miqdor noldan katta bo‘lishi kerak.')

        return value

    def validate_new_sale_price(self, value):
        if value is not None and value <= 0:
            raise serializers.ValidationError('Sotuv narxi noldan katta bo‘lishi kerak.')

        return value


class PurchaseSerializer(serializers.ModelSerializer):
    """Kirim hujjati. Qatorlar bitta so'rovda keladi."""

    lines = PurchaseLineSerializer(many=True)
    supplier_name = serializers.CharField(source='supplier.name', read_only=True, default=None)
    created_by_name = serializers.SerializerMethodField()
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    is_editable = serializers.BooleanField(read_only=True)
    debt = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)

    class Meta:
        model = Purchase
        fields = (
            'id', 'number', 'date', 'supplier', 'supplier_name', 'created_by_name',
            'status', 'status_display', 'note', 'total', 'amount_paid', 'debt',
            'is_editable', 'confirmed_at', 'cancelled_at', 'lines', 'created_at',
        )
        read_only_fields = (
            'id', 'number', 'status', 'total', 'confirmed_at', 'cancelled_at', 'created_at',
        )

    def get_created_by_name(self, purchase) -> str:
        user = purchase.created_by

        return (user.get_full_name() or user.username) if user else ''

    def validate(self, attrs):
        if self.instance is not None and not self.instance.is_editable:
            raise serializers.ValidationError(
                'Tasdiqlangan kirimni tahrirlab bo‘lmaydi.'
            )

        return attrs

    def _replace_lines(self, purchase, lines):
        purchase.lines.all().delete()

        PurchaseLine.objects.bulk_create([
            PurchaseLine(
                purchase=purchase,
                variant=line['variant'],
                quantity=line['quantity'],
                unit_cost=line['unit_cost'],
                new_sale_price=line.get('new_sale_price'),
            )
            for line in lines
        ])

    @transaction.atomic
    def create(self, validated_data):
        lines = validated_data.pop('lines', [])
        request = self.context['request']

        purchase = Purchase.objects.create(
            number=next_number('KIR', Purchase.objects, validated_data.get('date')),
            created_by=request.user,
            **validated_data,
        )

        self._replace_lines(purchase, lines)

        return recalculate_total(purchase)

    @transaction.atomic
    def update(self, instance, validated_data):
        lines = validated_data.pop('lines', None)

        for field, value in validated_data.items():
            setattr(instance, field, value)

        instance.save()

        if lines is not None:
            self._replace_lines(instance, lines)

        return recalculate_total(instance)
