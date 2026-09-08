from django.contrib import admin

from apps.catalog.models import (
    AttributeDefinition,
    Barcode,
    Category,
    Product,
    ProductUnit,
    Variant,
)


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'path', 'parent', 'default_unit', 'is_active')
    list_filter = ('is_active', 'tenant')
    search_fields = ('name',)


@admin.register(AttributeDefinition)
class AttributeDefinitionAdmin(admin.ModelAdmin):
    list_display = ('name', 'key', 'category', 'value_type', 'unit', 'is_required')
    list_filter = ('value_type', 'is_required', 'is_variant_axis')
    search_fields = ('name', 'key')


class VariantInline(admin.TabularInline):
    model = Variant
    extra = 0
    fields = ('sku', 'name', 'purchase_price', 'sale_price', 'is_active')


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'brand', 'base_unit', 'is_active')
    list_filter = ('is_active', 'category')
    search_fields = ('name', 'brand', 'model')
    inlines = [VariantInline]


@admin.register(Variant)
class VariantAdmin(admin.ModelAdmin):
    list_display = ('sku', 'product', 'name', 'purchase_price', 'sale_price')
    search_fields = ('sku', 'product__name')


@admin.register(ProductUnit)
class ProductUnitAdmin(admin.ModelAdmin):
    list_display = ('variant', 'unit', 'factor_to_base')


@admin.register(Barcode)
class BarcodeAdmin(admin.ModelAdmin):
    list_display = ('code', 'variant', 'code_type')
    search_fields = ('code', 'code_normalized')
