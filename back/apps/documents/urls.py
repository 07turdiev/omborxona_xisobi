from rest_framework.routers import DefaultRouter

from apps.documents.api import DocumentViewSet
from apps.documents.transfer_api import TransferViewSet

app_name = 'documents'

router = DefaultRouter()
router.register('documents', DocumentViewSet, basename='document')
router.register('transfers', TransferViewSet, basename='transfer')

urlpatterns = router.urls
