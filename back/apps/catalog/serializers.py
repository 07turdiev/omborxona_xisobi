from rest_framework import serializers

from apps.catalog.models import Category, Color, Product, Size, Variant
from apps.catalog.services import sync_variant_matrix
from apps.core.redaction import HideFromCashierMixin


class CategorySerializer(serializers.ModelSerializer):
    product_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Category
        fields = ('id', 'name', 'product_count')


class SizeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Size
        fields = ('id', 'name', 'position')


class ColorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Color
        fields = ('id', 'name')


class VariantSerializer(HideFromCashierMixin, serializers.ModelSerializer):
    """Variant. Tannarxni faqat administrator ko'radi."""

    admin_only_fields = ('average_cost',)

    product_name = serializers.CharField(source='product.name', read_only=True)
    size_name = serializers.CharField(source='size.name', read_only=True, default=None)
    color_name = serializers.CharField(source='color.name', read_only=True, default=None)
    label = serializers.CharField(read_only=True)
    price = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)

    class Meta:
        model = Variant
        fields = (
            'id', 'product', 'product_name', 'size', 'size_name', 'color', 'color_name',
            'label', 'sku', 'barcode', 'sale_price', 'price', 'average_cost',
            'stock_quantity', 'min_stock', 'is_active',
        )
        read_only_fields = (
            'id', 'product', 'size', 'color', 'sku', 'average_cost', 'stock_quantity',
        )


class ProductSerializer(serializers.ModelSerializer):
    """Mahsulot va uning variantlari.

    `size_ids` va `color_ids` — matritsa uchun: har bir yetishmayotgan
    o'lcham × rang juftligiga variant yaratiladi.
    """

    category_name = serializers.CharField(source='category.name', read_only=True)
    variants = VariantSerializer(many=True, read_only=True)

    size_ids = serializers.ListField(
        child=serializers.IntegerField(), write_only=True, required=False
    )
    color_ids = serializers.ListField(
        child=serializers.IntegerField(), write_only=True, required=False
    )

    class Meta:
        model = Product
        fields = (
            'id', 'category', 'category_name', 'name', 'brand', 'description',
            'photo', 'sale_price', 'is_active', 'variants', 'size_ids', 'color_ids',
        )
        read_only_fields = ('id', 'category_name', 'variants')

    def create(self, validated_data):
        sizes = validated_data.pop('size_ids', [])
        colors = validated_data.pop('color_ids', [])

        product = super().create(validated_data)
        sync_variant_matrix(product, sizes, colors)

        return product

    def update(self, instance, validated_data):
        sizes = validated_data.pop('size_ids', None)
        colors = validated_data.pop('color_ids', None)

        product = super().update(instance, validated_data)

        if sizes is not None or colors is not None:
            sync_variant_matrix(product, sizes or [], colors or [])

        return product
