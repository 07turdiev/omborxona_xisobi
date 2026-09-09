from rest_framework.routers import DefaultRouter

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

urlpatterns = router.urls
