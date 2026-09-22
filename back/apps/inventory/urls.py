from rest_framework.routers import DefaultRouter

from apps.inventory.api import (
    LocationViewSet,
    StockCountViewSet,
    StockMovementViewSet,
    TransferViewSet,
    WriteOffViewSet,
)

app_name = 'inventory'

router = DefaultRouter()
router.register('locations', LocationViewSet, basename='location')
router.register('movements', StockMovementViewSet, basename='movement')
router.register('transfers', TransferViewSet, basename='transfer')
router.register('stock-counts', StockCountViewSet, basename='stock-count')
router.register('write-offs', WriteOffViewSet, basename='write-off')

urlpatterns = router.urls
