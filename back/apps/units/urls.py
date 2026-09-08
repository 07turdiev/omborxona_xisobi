from rest_framework.routers import DefaultRouter

from apps.units.api import ConversionViewSet, CustomUnitViewSet

app_name = 'units'

router = DefaultRouter()
router.register('units', CustomUnitViewSet, basename='unit')
router.register('units-convert', ConversionViewSet, basename='unit-convert')

urlpatterns = router.urls
