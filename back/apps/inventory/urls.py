from django.urls import path
from rest_framework.routers import DefaultRouter

from apps.inventory.api import (
    CabinetView,
    LocationViewSet,
    PlaceView,
    ShelfRunViewSet,
    StockCountViewSet,
    StockMovementViewSet,
    TransferViewSet,
    WriteOffViewSet,
)

app_name = 'inventory'

router = DefaultRouter()
router.register('locations', LocationViewSet, basename='location')
router.register('shelf-runs', ShelfRunViewSet, basename='shelf-run')
router.register('movements', StockMovementViewSet, basename='movement')
router.register('transfers', TransferViewSet, basename='transfer')
router.register('stock-counts', StockCountViewSet, basename='stock-count')
router.register('write-offs', WriteOffViewSet, basename='write-off')

urlpatterns = router.urls + [
    path('storage/cabinet/', CabinetView.as_view(), name='cabinet'),
    path('storage/place/', PlaceView.as_view(), name='place'),
]
