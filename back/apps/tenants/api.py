"""Tashkilot sozlamalari va xodimlar API si."""

from __future__ import annotations

from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.core.permissions import HasTenantMembership, IsTenantAdminOrReadOnly
from apps.tenants.models import Membership, Tenant
from apps.tenants.serializers import (
    MembershipCreateSerializer,
    MembershipSerializer,
    MembershipUpdateSerializer,
    TenantSettingsSerializer,
)


class TenantSettingsViewSet(
    mixins.RetrieveModelMixin, mixins.UpdateModelMixin, viewsets.GenericViewSet
):
    """Joriy tashkilot sozlamalari.

    Yagona obyekt bilan ishlaydi — foydalanuvchi faqat o'zi kirgan
    tashkilotning sozlamasini ko'radi va o'zgartiradi. `pk` kerak emas.
    """

    serializer_class = TenantSettingsSerializer
    permission_classes = [IsTenantAdminOrReadOnly]

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

        serializer = self.get_serializer(
            tenant, data=request.data, partial=request.method == 'PATCH'
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(serializer.data)


class MembershipViewSet(viewsets.ModelViewSet):
    """Tashkilot xodimlari.

    Ko'rish — barcha a'zolarga, o'zgartirish — faqat egasi va menejerga.
    """

    permission_classes = [IsTenantAdminOrReadOnly]

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

        return Response(MembershipSerializer(membership).data, status=201)

    def perform_destroy(self, instance):
        """A'zolikni o'chiradi, foydalanuvchini emas.

        Foydalanuvchi boshqa tashkilotlarda ishlayotgan bo'lishi mumkin,
        shuning uchun uning hisobiga tegilmaydi.
        """
        instance.delete()

    @action(detail=False, methods=['get'])
    def roles(self, request):
        """Rollar ro'yxati va ularning huquqlari — forma uchun."""
        return Response([
            {
                'value': value,
                'label': str(label),
                'can_write': value in Membership.WRITE_ROLES,
                'is_admin': value in Membership.ADMIN_ROLES,
            }
            for value, label in Membership.Role.choices
        ])


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
