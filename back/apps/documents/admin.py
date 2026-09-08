from django.contrib import admin

from apps.documents.models import Document, DocumentLine


class DocumentLineInline(admin.TabularInline):
    model = DocumentLine
    extra = 0
    fields = ('variant', 'unit', 'quantity', 'quantity_base', 'unit_price', 'line_total')
    readonly_fields = ('quantity_base', 'line_total')


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ('number', 'kind', 'date', 'warehouse', 'partner', 'status', 'total_amount')
    list_filter = ('kind', 'status', 'warehouse')
    search_fields = ('number', 'external_number', 'partner__name')
    date_hierarchy = 'date'
    inlines = [DocumentLineInline]

    def has_change_permission(self, request, obj=None):
        """Tasdiqlangan hujjat admin panelidan ham tahrirlanmaydi."""
        if obj is not None and not obj.is_editable:
            return False

        return super().has_change_permission(request, obj)
