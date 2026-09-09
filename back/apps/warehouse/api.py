"""Ombor API si."""

from __future__ import annotations

from django.db.models import Count, Q
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.core.permissions import IsTenantMemberOrReadOnly
from apps.warehouse.models import Warehouse, WarehouseAccess
from apps.warehouse.serializers import WarehouseAccessSerializer, WarehouseSerializer


class WarehouseViewSet(viewsets.ModelViewSet):
    """Omborlar.

    Tashkilotlar orasidagi ajratish PostgreSQL RLS bilan, tashkilot
    ichidagi cheklov esa `WarehouseAccess.visible_to()` bilan qilinadi.
    Cheklov yozilmagan foydalanuvchi barcha omborlarni ko'radi.
    """

    serializer_class = WarehouseSerializer
    permission_classes = [IsTenantMemberOrReadOnly]
    queryset = Warehouse.objects.none()

    def get_queryset(self):
        queryset = Warehouse.objects.all()

        # Tashkilot ichidagi ixtiyoriy cheklov
        queryset = WarehouseAccess.visible_to(self.request.user, queryset)

        params = self.request.query_params

        if search := params.get('search', '').strip():
            queryset = queryset.filter(
                Q(name__icontains=search)
                | Q(code__icontains=search)
                | Q(address__icontains=search)
                | Q(manager__icontains=search)
            )

        if goods_type := params.get('goods_type', '').strip():
            queryset = queryset.filter(goods_type=goods_type)

        if purpose := params.get('purpose', '').strip():
            queryset = queryset.filter(purpose=purpose)

        if (active := params.get('is_active', '').strip()) in {'true', 'false'}:
            queryset = queryset.filter(is_active=active == 'true')

        return queryset

    @action(detail=False, methods=['get'])
    def summary(self, request):
        """Dashboard uchun qisqa jamlanma."""
        queryset = self.get_queryset()

        totals = queryset.aggregate(
            total=Count('id'),
            active=Count('id', filter=Q(is_active=True)),
            sellable=Count(
                'id',
                filter=Q(is_active=True, purpose__in=Warehouse.SELLABLE_PURPOSES),
            ),
        )

        by_type = list(
            queryset.values('goods_type').annotate(count=Count('id')).order_by()
        )

        return Response({**totals, 'by_goods_type': by_type})

    @action(detail=False, methods=['get'])
    def choices(self, request):
        """Formalar uchun tanlov ro'yxatlari."""
        return Response({
            'goods_types': [
                {'value': v, 'label': str(l)} for v, l in Warehouse.GoodsType.choices
            ],
            'purposes': [
                {'value': v, 'label': str(l)} for v, l in Warehouse.Purpose.choices
            ],
        })


class WarehouseAccessViewSet(viewsets.ModelViewSet):
    """Omborga kirish huquqlari (ixtiyoriy cheklov)."""

    serializer_class = WarehouseAccessSerializer
    permission_classes = [IsTenantMemberOrReadOnly]
    queryset = WarehouseAccess.objects.select_related('warehouse', 'user')
