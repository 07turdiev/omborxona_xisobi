"""Tarix API si — faqat o'qish."""

from __future__ import annotations

from django.db.models import Q
from rest_framework import mixins, serializers, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.audit.models import AuditEvent
from apps.core.access import FinancialRedactionMixin, Perm
from apps.core.permissions import SectionPermission
from apps.tenants.models import Membership


class AuditEventSerializer(serializers.ModelSerializer):
    action_display = serializers.CharField(source='get_action_display', read_only=True)
    object_type_display = serializers.CharField(read_only=True)

    class Meta:
        model = AuditEvent
        fields = (
            'id', 'created_at', 'action', 'action_display',
            'object_type', 'object_type_display', 'object_id', 'object_repr',
            'warehouse_id', 'warehouse_name', 'user', 'user_name',
            'details', 'changes',
        )
        read_only_fields = fields


class AuditEventViewSet(
    FinancialRedactionMixin, mixins.ListModelMixin, viewsets.GenericViewSet
):
    """Amallar tarixi.

    **Kim nimani ko'radi:** tashkilot egasi va menejer — barcha xodimlarning
    amallarini, qolganlar — faqat o'zinikini. Kassir hamkasbining sotuvini
    kim tahrirlaganini ko'rmasligi kerak, egasi esa aynan shuni ko'rishi
    kerak.

    Tahrir farqidagi moliyaviy maydonlar (masalan `purchase_price`) ruxsatsiz
    xodimga tozalanib ko'rsatiladi — `FinancialRedactionMixin` ichma-ich
    lug'atlarni ham tozalaydi.
    """

    serializer_class = AuditEventSerializer
    permission_classes = [SectionPermission]
    section_permissions = {'read': {Perm.HISTORY}}
    queryset = AuditEvent.objects.none()

    #: To'liq tarixni ko'radigan rollar
    FULL_VIEW_ROLES = frozenset({Membership.Role.OWNER, Membership.Role.MANAGER})

    def sees_everything(self) -> bool:
        return self.request.membership.role in self.FULL_VIEW_ROLES

    def get_queryset(self):
        queryset = AuditEvent.objects.all()

        if not self.sees_everything():
            queryset = queryset.filter(user_id=self.request.user.id)

        params = self.request.query_params

        if search := params.get('search', '').strip():
            queryset = queryset.filter(
                Q(object_repr__icontains=search)
                | Q(details__icontains=search)
                | Q(user_name__icontains=search)
            )

        if object_type := params.get('object_type', '').strip():
            queryset = queryset.filter(object_type=object_type)

        if action_value := params.get('action', '').strip():
            queryset = queryset.filter(action=action_value)

        if warehouse := params.get('warehouse', '').strip():
            queryset = queryset.filter(warehouse_id=warehouse)

        # Boshqa xodim bo'yicha filtr faqat to'liq ko'ruvchiga ma'noli
        if (user := params.get('user', '').strip()) and self.sees_everything():
            queryset = queryset.filter(user_id=user)

        if object_id := params.get('object_id', '').strip():
            queryset = queryset.filter(object_id=object_id)

        if date_from := params.get('date_from', '').strip():
            queryset = queryset.filter(created_at__date__gte=date_from)

        if date_to := params.get('date_to', '').strip():
            queryset = queryset.filter(created_at__date__lte=date_to)

        return queryset.order_by('-created_at', '-id')

    @action(detail=False, methods=['get'])
    def meta(self, request):
        """Filtrlar va sahifa sarlavhasi uchun: ko'rinish doirasi va ro'yxatlar."""
        return Response({
            'scope': 'all' if self.sees_everything() else 'own',
            'object_types': [
                {'value': value, 'label': label}
                for value, label in AuditEvent.OBJECT_TYPES.items()
            ],
            'actions': [
                {'value': value, 'label': str(label)}
                for value, label in AuditEvent.Action.choices
            ],
        })
