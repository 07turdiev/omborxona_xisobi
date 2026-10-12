from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework.exceptions import ValidationError
from rest_framework.generics import RetrieveUpdateAPIView
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.logo import build_receipt_logo
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


class ShopLogoView(APIView):
    """Chek logotipi: yuklash va olib tashlash.

    Sozlamalarning qolgani JSON bilan saqlanadi, logotip esa fayl bo'lib
    keladi — shuning uchun alohida manzil. Ikkalasi ham yangilangan
    sozlamalarni qaytaradi.
    """

    permission_classes = [IsAdmin]
    parser_classes = [MultiPartParser]

    def post(self, request):
        upload = request.FILES.get('logo')

        if upload is None:
            raise ValidationError({'logo': ['Rasm tanlanmagan.']})

        try:
            logo = build_receipt_logo(upload)
        except DjangoValidationError as error:
            raise ValidationError({'logo': error.messages}) from error

        return self._save(logo)

    def delete(self, request):
        return self._save(None)

    def _save(self, logo):
        settings = ShopSettings.load()
        settings.receipt_logo = logo
        settings.save()

        return Response(ShopSettingsSerializer(settings).data)
