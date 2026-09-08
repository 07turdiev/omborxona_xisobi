from django.contrib import admin

from apps.stock.models import Batch, StockBalance, StockMovement


@admin.register(Batch)
class BatchAdmin(admin.ModelAdmin):
    list_display = ('code', 'variant', 'expiry_date', 'is_expired')
    list_filter = ('expiry_date',)
    search_fields = ('code',)


@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    """Jurnal faqat o'qish uchun — append-only (3-arxitektura qarori)."""

    list_display = ('occurred_at', 'variant', 'warehouse', 'quantity', 'reason')
    list_filter = ('reason', 'warehouse')
    search_fields = ('variant__sku', 'note')
    date_hierarchy = 'occurred_at'

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(StockBalance)
class StockBalanceAdmin(admin.ModelAdmin):
    """Kesh — u ham qo'lda tahrirlanmaydi, jurnaldan hosila."""

    list_display = ('variant', 'warehouse', 'batch', 'quantity', 'reserved_quantity')
    list_filter = ('warehouse',)
    search_fields = ('variant__sku',)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
