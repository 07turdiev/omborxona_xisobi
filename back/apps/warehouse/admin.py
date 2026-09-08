from django.contrib import admin

from apps.warehouse.models import Warehouse, WarehouseAccess


@admin.register(Warehouse)
class WarehouseAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'goods_type', 'purpose', 'is_active', 'tenant')
    list_filter = ('goods_type', 'purpose', 'is_active', 'tenant')
    search_fields = ('name', 'code', 'address', 'manager')


@admin.register(WarehouseAccess)
class WarehouseAccessAdmin(admin.ModelAdmin):
    list_display = ('user', 'warehouse', 'level')
    list_filter = ('level',)
