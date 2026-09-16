from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.sales.api import ExchangeView, SaleReturnViewSet, SaleViewSet

app_name = 'sales'

router = DefaultRouter()
router.register('sales', SaleViewSet, basename='sale')
router.register('returns', SaleReturnViewSet, basename='return')

urlpatterns = [
    path('exchanges/', ExchangeView.as_view(), name='exchange'),
    path('', include(router.urls)),
]
