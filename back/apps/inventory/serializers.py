from rest_framework import serializers

from apps.inventory.models import StockCount, StockCountLine, StockMovement, WriteOff


class StockMovementSerializer(serializers.ModelSerializer):
    """Jurnal yozuvi — faqat o'qish uchun."""

    product_name = serializers.CharField(source='variant.product.name', read_only=True)
    variant_label = serializers.CharField(source='variant.label', read_only=True)
    sku = serializers.CharField(source='variant.sku', read_only=True)
    reason_display = serializers.CharField(source='get_reason_display', read_only=True)
    user_name = serializers.CharField(source='user.username', read_only=True, default=None)

    class Meta:
        model = StockMovement
        fields = (
            'id', 'variant', 'product_name', 'variant_label', 'sku', 'quantity',
            'reason', 'reason_display', 'document_type', 'document_id',
            'unit_cost', 'user', 'user_name', 'created_at',
        )


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

    class Meta:
        model = StockCount
        fields = (
            'id', 'number', 'date', 'status', 'status_display', 'category',
            'category_name', 'note', 'confirmed_at', 'lines', 'created_at',
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

    class Meta:
        model = WriteOff
        fields = (
            'id', 'variant', 'product_name', 'variant_label', 'sku',
            'quantity', 'reason', 'unit_cost', 'created_at',
        )
        read_only_fields = ('id', 'created_at')

    def validate_quantity(self, value):
        if value <= 0:
            raise serializers.ValidationError('Miqdor noldan katta bo‘lishi kerak.')

        return value
