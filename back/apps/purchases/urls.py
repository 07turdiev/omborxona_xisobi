from rest_framework.routers import DefaultRouter

from apps.purchases.api import PurchaseViewSet, SupplierPaymentViewSet, SupplierViewSet

app_name = 'purchases'

router = DefaultRouter()
router.register('suppliers', SupplierViewSet, basename='supplier')
router.register('supplier-payments', SupplierPaymentViewSet, basename='supplier-payment')
router.register('purchases', PurchaseViewSet, basename='purchase')

urlpatterns = router.urls
