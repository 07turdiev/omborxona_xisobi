from django.contrib import admin

from apps.tenants.models import Membership, Tenant


class MembershipInline(admin.TabularInline):
    model = Membership
    extra = 0
    fields = ('user', 'role', 'is_active')


@admin.register(Tenant)
class TenantAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'business_type', 'base_currency', 'is_active')
    list_filter = ('business_type', 'is_active')
    search_fields = ('name', 'slug', 'inn')
    inlines = [MembershipInline]


@admin.register(Membership)
class MembershipAdmin(admin.ModelAdmin):
    list_display = ('user', 'tenant', 'role', 'is_active')
    list_filter = ('role', 'is_active', 'tenant')
    search_fields = ('user__username',)
