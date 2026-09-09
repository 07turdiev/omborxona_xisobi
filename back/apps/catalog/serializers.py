"""Katalog serializerlari."""

from __future__ import annotations

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from rest_framework import serializers

from apps.catalog import attributes as attr_service
from apps.catalog.models import (
    AttributeDefinition,
    Barcode,
    Category,
    Product,
    ProductUnit,
    Variant,
)


def _as_drf_error(exc: DjangoValidationError):
    """Django validatsiya xatosini DRF formatiga o'giradi."""
    if hasattr(exc, 'message_dict'):
        return serializers.ValidationError(exc.message_dict)

    return serializers.ValidationError(exc.messages)


def _clean_or_raise(instance, attrs, request):
    """Model `clean()` ini chaqirib, xatoni DRF formatida qaytaradi."""
    for field, value in attrs.items():
        setattr(instance, field, value)

    instance.tenant_id = request.tenant_id

    try:
        instance.clean()
    except DjangoValidationError as exc:
        raise _as_drf_error(exc)


class CategorySerializer(serializers.ModelSerializer):
    depth = serializers.IntegerField(read_only=True)
    product_count = serializers.IntegerField(read_only=True)

    #: `ltree` maydoni — DRF va drf-spectacular uni bilmaydi, shuning
    #: uchun ochiq matn sifatida e'lon qilinadi
    path = serializers.CharField(read_only=True)

    class Meta:
        model = Category
        fields = (
            'id', 'name', 'parent', 'path', 'depth',
            'default_unit', 'code_prefix', 'is_active', 'product_count',
        )
        read_only_fields = ('id', 'path', 'depth', 'product_count')

    def validate(self, attrs):
        _clean_or_raise(self.instance or Category(), attrs, self.context['request'])
        return attrs


class AttributeDefinitionSerializer(serializers.ModelSerializer):
    value_type_display = serializers.CharField(
        source='get_value_type_display', read_only=True
    )
    category_name = serializers.CharField(source='category.name', read_only=True)

    class Meta:
        model = AttributeDefinition
        fields = (
            'id', 'category', 'category_name', 'key', 'name',
            'value_type', 'value_type_display', 'unit', 'choices',
            'default_value', 'is_required', 'is_variant_axis',
            'uniqueness', 'position',
        )
        read_only_fields = ('id', 'value_type_display', 'category_name')

    def validate(self, attrs):
        _clean_or_raise(
            self.instance or AttributeDefinition(), attrs, self.context['request']
        )
        return attrs


class ProductUnitSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductUnit
        fields = (
            'id', 'variant', 'unit', 'factor_to_base',
            'is_default_purchase', 'is_default_sale',
        )
        read_only_fields = ('id',)


class BarcodeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Barcode
        fields = ('id', 'variant', 'code', 'code_normalized', 'code_type')
        read_only_fields = ('id', 'code_normalized')


class VariantSerializer(serializers.ModelSerializer):
    """Variant. `attributes` xom qiymatlar sifatida qabul qilinadi.

    Kirishda `{"qalinlik": "12 mm"}` kutiladi, saqlashda esa
    `{"qalinlik": {"raw": "12 mm", "num": "0.012"}}` ga aylantiriladi.
    Chiqishda `attributes` — xom qiymatlar (forma uchun),
    `attributes_full` — to'liq juftliklar (filtrlash uchun).
    """

    display_name = serializers.CharField(read_only=True)
    product_name = serializers.CharField(source='product.name', read_only=True)
    category = serializers.IntegerField(source='product.category_id', read_only=True)
    attributes_full = serializers.JSONField(source='attributes', read_only=True)
    units = ProductUnitSerializer(many=True, read_only=True)
    barcodes = BarcodeSerializer(many=True, read_only=True)

    class Meta:
        model = Variant
        fields = (
            'id', 'product', 'product_name', 'category', 'sku', 'name',
            'display_name', 'attributes', 'attributes_full',
            'purchase_price', 'sale_price', 'currency', 'min_stock',
            'is_active', 'units', 'barcodes',
        )
        read_only_fields = (
            'id', 'display_name', 'product_name', 'category',
            'attributes_full', 'units', 'barcodes',
        )

    def to_representation(self, instance):
        """`attributes` ni xom qiymatlar sifatida qaytaradi."""
        data = super().to_representation(instance)

        data['attributes'] = {
            key: (entry.get('raw') if isinstance(entry, dict) else entry)
            for key, entry in (instance.attributes or {}).items()
        }

        return data

    def validate(self, attrs):
        product = attrs.get('product') or getattr(self.instance, 'product', None)

        if product is None:
            raise serializers.ValidationError({'product': 'Mahsulot korsatilmagan.'})

        raw_values = attrs.get('attributes')

        # Tahrirlashda atributlar berilmasa, mavjudlari o'zgarishsiz qoladi
        if raw_values is None and self.instance is not None:
            return attrs

        instance = self.instance or Variant()
        instance.tenant_id = self.context['request'].tenant_id

        try:
            built = attr_service.build_attributes(product.category, raw_values or {})
            attr_service.validate_uniqueness(instance, product.category, built)
        except DjangoValidationError as exc:
            raise _as_drf_error(exc)

        attrs['attributes'] = built

        return attrs


class ProductSerializer(serializers.ModelSerializer):
    """Mahsulot. Variantsiz yaratilsa, bitta standart variant hosil bo'ladi."""

    category_name = serializers.CharField(source='category.name', read_only=True)
    effective_unit = serializers.CharField(read_only=True)
    variants = VariantSerializer(many=True, read_only=True)

    #: Faqat yozish uchun: bitta variantli mahsulotni bir so'rovda yaratish
    sku = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = Product
        fields = (
            'id', 'category', 'category_name', 'name', 'brand', 'model',
            'description', 'base_unit', 'effective_unit', 'is_active',
            'variants', 'sku',
        )
        read_only_fields = ('id', 'category_name', 'effective_unit', 'variants')

    @transaction.atomic
    def create(self, validated_data):
        """Mahsulot va standart variantni yaratadi.

        Qurilish mollarida mahsulotning odatda bitta varianti bo'ladi va
        foydalanuvchi "variant" tushunchasini umuman ko'rmasligi kerak.
        Kiyimda esa o'lcham va rang bo'yicha variantlar qo'lda qo'shiladi.
        """
        sku = (validated_data.pop('sku', '') or '').strip()
        product = super().create(validated_data)

        Variant.objects.create(
            tenant=product.tenant,
            product=product,
            sku=sku or f'P{product.pk}',
        )

        return product
