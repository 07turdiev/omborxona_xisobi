from django.contrib import admin

from apps.partners.models import Partner


@admin.register(Partner)
class PartnerAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_supplier', 'is_customer', 'phone', 'is_active')
    list_filter = ('is_supplier', 'is_customer', 'is_active')
    search_fields = ('name', 'inn', 'phone')
