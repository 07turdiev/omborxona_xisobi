from rest_framework.routers import DefaultRouter

from apps.audit.api import AuditEventViewSet

app_name = 'audit'

router = DefaultRouter()
router.register('history', AuditEventViewSet, basename='history')

urlpatterns = router.urls
