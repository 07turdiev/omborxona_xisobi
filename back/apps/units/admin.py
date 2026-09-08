from django.contrib import admin

from apps.units.models import CustomUnit


@admin.register(CustomUnit)
class CustomUnitAdmin(admin.ModelAdmin):
    list_display = ('name', 'symbol', 'definition', 'tenant')
    list_filter = ('tenant',)
    search_fields = ('name', 'symbol', 'definition')
