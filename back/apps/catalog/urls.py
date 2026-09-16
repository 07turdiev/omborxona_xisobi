from rest_framework.routers import DefaultRouter

from apps.catalog.api import (
    CategoryViewSet,
    ColorViewSet,
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
router.register('variants', VariantViewSet, basename='variant')

urlpatterns = router.urls
