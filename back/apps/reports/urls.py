from rest_framework.routers import DefaultRouter

from apps.reports.api import ReportViewSet

app_name = 'reports'

router = DefaultRouter()
router.register('reports', ReportViewSet, basename='report')

urlpatterns = router.urls
