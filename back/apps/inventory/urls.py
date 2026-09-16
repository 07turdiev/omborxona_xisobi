from rest_framework.routers import DefaultRouter

from apps.inventory.api import StockCountViewSet, StockMovementViewSet, WriteOffViewSet

app_name = 'inventory'

router = DefaultRouter()
router.register('movements', StockMovementViewSet, basename='movement')
router.register('stock-counts', StockCountViewSet, basename='stock-count')
router.register('write-offs', WriteOffViewSet, basename='write-off')

urlpatterns = router.urls
