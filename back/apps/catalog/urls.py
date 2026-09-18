from rest_framework.routers import DefaultRouter

from apps.catalog.api import (
    CatalogViewSet,
    CategoryViewSet,
    ColorViewSet,
    ProductImageViewSet,
    ProductViewSet,
    SizeViewSet,
    VariantViewSet,
)

app_name = 'catalog'

router = DefaultRouter()
router.register('categories', CategoryViewSet, basename='category')
router.register('sizes', SizeViewSet, basename='size')
router.register('colors', ColorViewSet, basename='color')
router.register('products', ProductViewSet, basename='product')
router.register('product-images', ProductImageViewSet, basename='product-image')
router.register('catalog', CatalogViewSet, basename='catalog')
router.register('variants', VariantViewSet, basename='variant')

urlpatterns = router.urls
