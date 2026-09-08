from rest_framework.routers import DefaultRouter

from apps.catalog.api import (
    AttributeDefinitionViewSet,
    BarcodeViewSet,
    CategoryViewSet,
    ProductUnitViewSet,
    ProductViewSet,
    VariantViewSet,
)

app_name = 'catalog'

router = DefaultRouter()
router.register('categories', CategoryViewSet, basename='category')
router.register('attribute-definitions', AttributeDefinitionViewSet, basename='attribute-definition')
router.register('products', ProductViewSet, basename='product')
router.register('variants', VariantViewSet, basename='variant')
router.register('product-units', ProductUnitViewSet, basename='product-unit')
router.register('barcodes', BarcodeViewSet, basename='barcode')

urlpatterns = router.urls
