from rest_framework.routers import DefaultRouter

from apps.warehouse.api import WarehouseAccessViewSet, WarehouseViewSet

app_name = 'warehouse'

router = DefaultRouter()
router.register('warehouses', WarehouseViewSet, basename='warehouse')
router.register('warehouse-access', WarehouseAccessViewSet, basename='warehouse-access')

urlpatterns = router.urls
