from rest_framework.routers import DefaultRouter

from apps.expenses.api import ExpenseViewSet

app_name = 'expenses'

router = DefaultRouter()
router.register('expenses', ExpenseViewSet, basename='expense')

urlpatterns = router.urls
