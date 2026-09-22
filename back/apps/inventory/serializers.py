from rest_framework import serializers

from apps.inventory.models import (
    Location,
    StockCount,
    StockCountLine,
    StockMovement,
    Transfer,
    TransferLine,
    WriteOff,
)


class LocationSerializer(serializers.ModelSerializer):
    """Joy: ombor yoki savdo zali."""

    kind_display = serializers.CharField(source='get_kind_display', read_only=True)

    class Meta:
        model = Location
        fields = ('id', 'name', 'kind', 'kind_display', 'is_active')


class StockMovementSerializer(serializers.ModelSerializer):
    """Jurnal yozuvi — faqat o'qish uchun."""

    product_name = serializers.CharField(source='variant.product.name', read_only=True)
    variant_label = serializers.CharField(source='variant.label', read_only=True)
    sku = serializers.CharField(source='variant.sku', read_only=True)
    reason_display = serializers.CharField(source='get_reason_display', read_only=True)
    location_name = serializers.CharField(source='location.name', read_only=True)
    user_name = serializers.CharField(source='user.username', read_only=True, default=None)

    #: Hujjat raqami (KIR-…, SOT-…). Jurnalda faqat turi va id saqlanadi,
    #: raqamlar sahifa uchun bir yo'la olinadi (`inventory.api`)
    document_number = serializers.SerializerMethodField()

    #: Qaytarishda — qaysi chekdan qaytgani: havola o'sha chekka olib boradi
    document_sale_number = serializers.SerializerMethodField()

    class Meta:
        model = StockMovement
        fields = (
            'id', 'variant', 'product_name', 'variant_label', 'sku', 'quantity',
            'location', 'location_name',
            'reason', 'reason_display', 'document_type', 'document_id',
            'document_number', 'document_sale_number',
            'unit_cost', 'user', 'user_name', 'created_at',
        )

    def _document(self, movement) -> dict:
        documents = self.context.get('documents', {})

        return documents.get((movement.document_type, movement.document_id), {})

    def get_document_number(self, movement):
        return self._document(movement).get('number')

    def get_document_sale_number(self, movement):
        return self._document(movement).get('sale_number')


class StockCountLineSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='variant.product.name', read_only=True)
    variant_label = serializers.CharField(source='variant.label', read_only=True)
    sku = serializers.CharField(source='variant.sku', read_only=True)
    difference = serializers.IntegerField(read_only=True)
    average_cost = serializers.DecimalField(
        source='variant.average_cost', max_digits=14, decimal_places=2, read_only=True
    )

    class Meta:
        model = StockCountLine
        fields = (
            'id', 'variant', 'product_name', 'variant_label', 'sku',
            'expected_quantity', 'counted_quantity', 'difference', 'average_cost',
        )
        read_only_fields = ('id', 'expected_quantity')


class StockCountSerializer(serializers.ModelSerializer):
    """Inventarizatsiya. Qatorlar bitta so'rovda yuboriladi."""

    lines = StockCountLineSerializer(many=True, required=False)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True, default=None)

    #: Qaysi joy sanaladi. Ko'rsatilmasa — savdo zali: zal tez-tez,
    #: ombor esa kamdan-kam sanaladi.
    location = serializers.PrimaryKeyRelatedField(
        queryset=Location.objects.filter(is_active=True), required=False
    )
    location_name = serializers.CharField(source='location.name', read_only=True)

    class Meta:
        model = StockCount
        fields = (
            'id', 'number', 'date', 'status', 'status_display', 'category',
            'category_name', 'location', 'location_name', 'note', 'confirmed_at',
            'lines', 'created_at',
        )
        read_only_fields = ('id', 'number', 'status', 'confirmed_at', 'created_at')

    def validate(self, attrs):
        if self.instance is not None and self.instance.status != StockCount.Status.DRAFT:
            raise serializers.ValidationError(
                'Tasdiqlangan inventarizatsiyani o‘zgartirib bo‘lmaydi.'
            )

        return attrs

    def _replace_lines(self, stock_count, lines):
        stock_count.lines.all().delete()

        StockCountLine.objects.bulk_create([
            StockCountLine(
                stock_count=stock_count,
                variant=line['variant'],
                counted_quantity=line.get('counted_quantity', 0),
            )
            for line in lines
        ])

    def create(self, validated_data):
        from apps.core.numbering import next_number

        lines = validated_data.pop('lines', [])
        request = self.context['request']

        validated_data.setdefault('location', Location.shop())

        stock_count = StockCount.objects.create(
            number=next_number('INV', StockCount.objects, validated_data.get('date')),
            created_by=request.user,
            **validated_data,
        )

        self._replace_lines(stock_count, lines)

        return stock_count

    def update(self, instance, validated_data):
        lines = validated_data.pop('lines', None)

        for field, value in validated_data.items():
            setattr(instance, field, value)

        instance.save()

        if lines is not None:
            self._replace_lines(instance, lines)

        return instance


class WriteOffSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='variant.product.name', read_only=True)
    variant_label = serializers.CharField(source='variant.label', read_only=True)
    sku = serializers.CharField(source='variant.sku', read_only=True)
    unit_cost = serializers.DecimalField(
        source='variant.average_cost', max_digits=14, decimal_places=2, read_only=True
    )

    location = serializers.PrimaryKeyRelatedField(
        queryset=Location.objects.filter(is_active=True), required=False
    )
    location_name = serializers.CharField(source='location.name', read_only=True)

    class Meta:
        model = WriteOff
        fields = (
            'id', 'variant', 'product_name', 'variant_label', 'sku',
            'location', 'location_name', 'quantity', 'reason', 'unit_cost',
            'created_at',
        )
        read_only_fields = ('id', 'created_at')

    def validate_quantity(self, value):
        if value <= 0:
            raise serializers.ValidationError('Miqdor noldan katta bo‘lishi kerak.')

        return value


class TransferLineSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='variant.product.name', read_only=True)
    variant_label = serializers.CharField(source='variant.label', read_only=True)
    sku = serializers.CharField(source='variant.sku', read_only=True)

    class Meta:
        model = TransferLine
        fields = ('id', 'variant', 'product_name', 'variant_label', 'sku', 'quantity')
        read_only_fields = ('id',)

    def validate_quantity(self, value):
        if value <= 0:
            raise serializers.ValidationError('Miqdor noldan katta bo‘lishi kerak.')

        return value


class TransferSerializer(serializers.ModelSerializer):
    """Ko'chirish: ombordan zalga yoki teskari."""

    lines = TransferLineSerializer(many=True)

    #: Ko'rsatilmasa — bugun. Ko'chirish odatda shu zahoti bo'ladi.
    date = serializers.DateField(required=False)

    source_name = serializers.CharField(source='source.name', read_only=True)
    target_name = serializers.CharField(source='target.name', read_only=True)
    created_by_name = serializers.SerializerMethodField()

    class Meta:
        model = Transfer
        fields = (
            'id', 'number', 'date', 'source', 'source_name', 'target', 'target_name',
            'note', 'lines', 'created_by_name', 'created_at',
        )
        read_only_fields = ('id', 'number', 'created_at')

    def get_created_by_name(self, transfer) -> str:
        user = transfer.created_by

        return (user.get_full_name() or user.username) if user else ''
