from rest_framework.generics import RetrieveUpdateAPIView
from rest_framework.permissions import IsAuthenticated

from apps.core.models import ShopSettings
from apps.core.permissions import IsAdmin
from apps.core.serializers import ShopSettingsSerializer


class ShopSettingsView(RetrieveUpdateAPIView):
    """Do'kon sozlamalari — bitta yozuv.

    Kassir ham o'qiydi: chekda do'kon nomi, kassada esa ruxsat etilgan
    eng katta chegirma kerak. O'zgartirish — administratorga.
    """

    serializer_class = ShopSettingsSerializer

    def get_permissions(self):
        if self.request.method in ('PUT', 'PATCH'):
            return [IsAdmin()]

        return [IsAuthenticated()]

    def get_object(self):
        return ShopSettings.load()
