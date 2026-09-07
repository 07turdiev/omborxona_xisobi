from django.urls import include, path
from rest_framework.routers import DefaultRouter

app_name = "warehouse"

router = DefaultRouter()
# Bu yerga ViewSet'lar ro'yxatdan o'tkaziladi, masalan:
# router.register("products", ProductViewSet, basename="product")

urlpatterns = [
    path("", include(router.urls)),
]
