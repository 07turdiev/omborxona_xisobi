from rest_framework.routers import DefaultRouter

from apps.pricing.api import CurrencyViewSet, ExchangeRateViewSet

app_name = 'pricing'

router = DefaultRouter()
router.register('currencies', CurrencyViewSet, basename='currency')
router.register('exchange-rates', ExchangeRateViewSet, basename='exchange-rate')

urlpatterns = router.urls
