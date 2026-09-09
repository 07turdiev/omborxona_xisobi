from django.contrib import admin

from apps.pricing.models import CostConsumption, CostLayer, Currency, ExchangeRate


@admin.register(Currency)
class CurrencyAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'is_base', 'is_active', 'tenant')
    list_filter = ('is_base', 'is_active')


@admin.register(ExchangeRate)
class ExchangeRateAdmin(admin.ModelAdmin):
    list_display = ('currency', 'rate', 'valid_from', 'source')
    list_filter = ('currency',)
    date_hierarchy = 'valid_from'


@admin.register(CostLayer)
class CostLayerAdmin(admin.ModelAdmin):
    """Qatlamlar jurnaldan hosila — qo'lda tahrirlanmaydi."""

    list_display = (
        'variant', 'warehouse', 'batch',
        'quantity_initial', 'quantity_remaining', 'unit_cost_base', 'acquired_at',
    )
    list_filter = ('warehouse',)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(CostConsumption)
class CostConsumptionAdmin(admin.ModelAdmin):
    list_display = ('movement', 'layer', 'quantity', 'unit_cost_base')

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
