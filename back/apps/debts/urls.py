from rest_framework.routers import DefaultRouter

from apps.debts.api import DebtViewSet

app_name = 'debts'

router = DefaultRouter()
router.register('debts', DebtViewSet, basename='debt')

urlpatterns = router.urls
