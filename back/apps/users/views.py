from django.contrib.auth import get_user_model
from rest_framework import generics, permissions

from .serializers import RegisterSerializer, UserSerializer

User = get_user_model()


class RegisterView(generics.CreateAPIView):
    """Yangi foydalanuvchi ro'yxatdan o'tkazish."""

    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]


class MeView(generics.RetrieveUpdateAPIView):
    """Joriy foydalanuvchi ma'lumotlari."""

    serializer_class = UserSerializer

    def get_object(self):
        return self.request.user
