"""Tashkilot sozlamalari va xodimlar API si."""

from __future__ import annotations

from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response

from apps.audit import services as audit_services
from apps.audit.mixins import Action, AuditMixin
from apps.core.access import PERMISSION_CATALOG, PERMISSION_GROUPS, ROLE_DEFAULTS, Perm
from apps.core.permissions import HasTenantMembership, SectionPermission
from apps.tenants.models import Membership, Tenant
from apps.tenants.serializers import (
    MembershipCreateSerializer,
    MembershipSerializer,
    MembershipUpdateSerializer,
    TenantSettingsSerializer,
)


class TenantSettingsViewSet(
    AuditMixin,
    mixins.RetrieveModelMixin, mixins.UpdateModelMixin, viewsets.GenericViewSet
):
    """Joriy tashkilot sozlamalari.

    Yagona obyekt bilan ishlaydi — foydalanuvchi faqat o'zi kirgan
    tashkilotning sozlamasini ko'radi va o'zgartiradi. `pk` kerak emas.
    """

    serializer_class = TenantSettingsSerializer
    audit_object_type = 'settings'
    permission_classes = [SectionPermission]
    section_permissions = {'write': {Perm.SETTINGS}}
    queryset = Tenant.objects.none()

    def get_queryset(self):
        return Tenant.objects.filter(pk=self.request.tenant_id)

    def get_object(self):
        return Tenant.objects.get(pk=self.request.tenant_id)

    @action(detail=False, methods=['get', 'patch', 'put'], url_path='current')
    def current(self, request):
        """Joriy tashkilot sozlamalari."""
        tenant = self.get_object()

        if request.method == 'GET':
            return Response(self.get_serializer(tenant).data)

        before = audit_services.snapshot(tenant)

        serializer = self.get_serializer(
            tenant, data=request.data, partial=request.method == 'PATCH'
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        if changes := audit_services.diff(before, audit_services.snapshot(tenant)):
            self.audit(Action.UPDATE, tenant, changes=changes)

        return Response(serializer.data)


class MembershipViewSet(AuditMixin, viewsets.ModelViewSet):
    """Tashkilot xodimlari.

    Ko'rish — barcha a'zolarga, o'zgartirish — faqat egasi va menejerga.
    """

    audit_object_type = 'member'
    permission_classes = [SectionPermission]
    section_permissions = {'write': {Perm.USERS}}
    queryset = Membership.objects.none()

    def get_queryset(self):
        queryset = (
            Membership.objects.filter(tenant_id=self.request.tenant_id)
            .select_related('user')
            .order_by('user__username')
        )

        params = self.request.query_params

        if role := params.get('role', '').strip():
            queryset = queryset.filter(role=role)

        if (active := params.get('is_active', '').strip()) in {'true', 'false'}:
            queryset = queryset.filter(is_active=active == 'true')

        if search := params.get('search', '').strip():
            from django.db.models import Q

            queryset = queryset.filter(
                Q(user__username__icontains=search)
                | Q(user__first_name__icontains=search)
                | Q(user__last_name__icontains=search)
            )

        return queryset

    def get_serializer_class(self):
        if self.action == 'create':
            return MembershipCreateSerializer

        if self.action in {'update', 'partial_update'}:
            return MembershipUpdateSerializer

        return MembershipSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        membership = serializer.save()

        self.audit(Action.CREATE, membership, details=membership.get_role_display())

        return Response(MembershipSerializer(membership).data, status=201)

    def perform_destroy(self, instance):
        """A'zolikni o'chiradi, foydalanuvchini emas.

        Foydalanuvchi boshqa tashkilotlarda ishlayotgan bo'lishi mumkin,
        shuning uchun uning hisobiga tegilmaydi.
        """
        actor = self.request.membership

        if instance.user_id == actor.user_id:
            raise PermissionDenied('O‘zingizni tashkilotdan chiqara olmaysiz.')

        if (
            instance.role == Membership.Role.OWNER
            and actor.role != Membership.Role.OWNER
        ):
            raise PermissionDenied('Tashkilot egasini faqat egasi chiqara oladi.')

        super().perform_destroy(instance)

    @action(detail=False, methods=['get'])
    def roles(self, request):
        """Rollar ro'yxati va ularning huquqlari — forma uchun."""
        return Response([
            {
                'value': value,
                'label': str(label),
                'can_write': value in Membership.WRITE_ROLES,
                'is_admin': value in Membership.ADMIN_ROLES,
                'default_permissions': sorted(ROLE_DEFAULTS.get(value, frozenset())),
            }
            for value, label in Membership.Role.choices
        ])

    @action(detail=False, methods=['get'], url_path='permissions')
    def permission_catalog(self, request):
        """Ruxsatlar katalogi — xodim formasidagi katakchalar uchun."""
        return Response({'groups': PERMISSION_GROUPS, 'items': PERMISSION_CATALOG})


class MyMembershipsViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    """Joriy foydalanuvchining barcha a'zoliklari — tashkilot almashtirish uchun."""

    serializer_class = MembershipSerializer
    permission_classes = [HasTenantMembership]
    pagination_class = None

    def get_queryset(self):
        return (
            Membership.objects.filter(
                user=self.request.user, is_active=True, tenant__is_active=True
            )
            .select_related('user', 'tenant')
            .order_by('tenant__name')
        )
