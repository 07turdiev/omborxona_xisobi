from rest_framework.routers import DefaultRouter

from apps.partners.api import PartnerViewSet

app_name = 'partners'

router = DefaultRouter()
router.register('partners', PartnerViewSet, basename='partner')

urlpatterns = router.urls
