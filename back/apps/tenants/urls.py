from rest_framework.routers import DefaultRouter

from apps.tenants.companies import CompanyViewSet
from apps.tenants.api import (
    MembershipViewSet,
    MyMembershipsViewSet,
    TenantSettingsViewSet,
)

app_name = 'tenants'

router = DefaultRouter()
router.register('tenant', TenantSettingsViewSet, basename='tenant')
router.register('members', MembershipViewSet, basename='member')
router.register('my-memberships', MyMembershipsViewSet, basename='my-membership')
router.register('companies', CompanyViewSet, basename='company')

urlpatterns = router.urls
