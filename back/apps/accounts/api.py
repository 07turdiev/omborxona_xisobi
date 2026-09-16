from django.contrib.auth import get_user_model
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.generics import RetrieveAPIView
from rest_framework.response import Response

from apps.accounts.serializers import (
    SetPasswordSerializer,
    UserCreateSerializer,
    UserSerializer,
)
from apps.core.permissions import IsAdmin

User = get_user_model()


class MeView(RetrieveAPIView):
    """Joriy xodim — interfeys roli shu javobdan biladi."""

    serializer_class = UserSerializer

    def get_object(self):
        return self.request.user


class UserViewSet(viewsets.ModelViewSet):
    """Xodimlar. Faqat administrator uchun.

    O'chirish yo'q: xodim sotuvlar va hujjatlarda qoladi, shuning uchun
    faqat faolsizlantiriladi (`is_active`).
    """

    queryset = User.objects.all()
    permission_classes = [IsAdmin]
    http_method_names = ['get', 'post', 'patch', 'head', 'options']

    def get_serializer_class(self):
        return UserCreateSerializer if self.action == 'create' else UserSerializer

    @action(detail=True, methods=['post'], url_path='set-password')
    def set_password(self, request, pk=None):
        """Parolni almashtirish."""
        user = self.get_object()
        serializer = SetPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user.set_password(serializer.validated_data['password'])
        user.save(update_fields=['password'])

        return Response({'detail': 'Parol yangilandi.'})
