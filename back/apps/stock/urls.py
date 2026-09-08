from rest_framework.routers import DefaultRouter

from apps.stock.api import BatchViewSet, StockBalanceViewSet, StockMovementViewSet

app_name = 'stock'

router = DefaultRouter()
router.register('stock', StockBalanceViewSet, basename='stock')
router.register('stock-movements', StockMovementViewSet, basename='stock-movement')
router.register('batches', BatchViewSet, basename='batch')

urlpatterns = router.urls
