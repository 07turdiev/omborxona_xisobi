"""Ruxsatlar. Ikki rol bor: administrator va kassir."""

from rest_framework.permissions import SAFE_METHODS, BasePermission


class IsAdmin(BasePermission):
    """Faqat administrator (yoki Django superuser)."""

    message = 'Bu bo‘lim faqat administrator uchun.'

    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and user.is_admin)


class IsAdminOrReadOnly(BasePermission):
    """O'qish — har bir xodimga, o'zgartirish — faqat administratorga.

    Kassir tovar va narxni ko'radi, lekin o'zgartira olmaydi.
    """

    message = 'O‘zgartirish uchun administrator huquqi kerak.'

    def has_permission(self, request, view):
        user = request.user

        if not (user and user.is_authenticated):
            return False

        return request.method in SAFE_METHODS or user.is_admin
