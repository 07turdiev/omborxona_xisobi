"""Tashkilot a'zoligiga asoslangan ruxsatlar.

Ruxsat ikki qatlamda ishlaydi:

1. **PostgreSQL RLS** — begona tashkilot ma'lumoti umuman ko'rinmaydi.
   Bu asosiy va chetlab o'tib bo'lmaydigan himoya.
2. **Bu yerdagi permission klasslari** — tashkilot ichidagi rolga qarab
   yozish huquqini cheklaydi (kuzatuvchi o'zgartira olmaydi).

Ombor darajasidagi cheklov (`apps.warehouse.WarehouseAccess`) **ixtiyoriy**:
foydalanuvchi uchun bitta ham cheklov yozilmagan bo'lsa, u tashkilotning
barcha omborlarini va barcha hisobotlarini ko'radi. Aksariyat do'konlarda
ombor soni oz va hamma hammasini ko'rishi kerak, shuning uchun standart
holat — ochiq.
"""

from __future__ import annotations

from rest_framework import permissions

SAFE_METHODS = permissions.SAFE_METHODS


class HasTenantMembership(permissions.BasePermission):
    """Foydalanuvchi joriy tashkilotning faol a'zosi bo'lishi shart."""

    message = 'Siz bu tashkilotning a\'zosi emassiz.'

    def has_permission(self, request, view):
        user = request.user

        if not user or not user.is_authenticated:
            return False

        tenant_id = getattr(request, 'tenant_id', None)

        if tenant_id is None:
            return False

        membership = user.membership_for(tenant_id)

        if membership is None:
            return False

        # A'zolikni view'ga uzatamiz — takroriy so'rov qilinmasin
        request.membership = membership

        return True


class IsTenantMemberOrReadOnly(HasTenantMembership):
    """O'qish — har a'zoga; yozish — faqat yozish huquqi bor rollarga."""

    message = 'Bu amalni bajarish uchun huquqingiz yo\'q.'

    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False

        if request.method in SAFE_METHODS:
            return True

        return request.membership.can_write


class IsTenantAdminOrReadOnly(HasTenantMembership):
    """O'qish — har a'zoga; yozish — faqat egasi va menejerga.

    Tashkilot sozlamalari uchun: o'lchov birliklari, kategoriyalar,
    hujjat shablonlari. Bularni omborchi yoki sotuvchi o'zgartirmasligi
    kerak — noto'g'ri birlik ta'rifi butun qoldiqni buzadi.
    """

    message = 'Bu sozlamani faqat tashkilot egasi yoki menejeri o\'zgartira oladi.'

    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False

        if request.method in SAFE_METHODS:
            return True

        return request.membership.is_admin
