"""Hujjat API si."""

from __future__ import annotations

from decimal import Decimal

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import Count, Q, Sum
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.core.permissions import IsTenantMemberOrReadOnly
from apps.documents import services
from apps.documents.models import Document
from apps.documents.serializers import DocumentSerializer
from apps.warehouse.models import WarehouseAccess


class DocumentViewSet(viewsets.ModelViewSet):
    """Kirim va sotuv hujjatlari.

    Tasdiqlash va bekor qilish alohida amallar: ular qoldiqqa ta'sir
    qiladi va oddiy `PATCH` bilan aralashtirib yuborilmasligi kerak.
    """

    serializer_class = DocumentSerializer
    permission_classes = [IsTenantMemberOrReadOnly]

    def get_queryset(self):
        queryset = (
            Document.objects.select_related('warehouse', 'partner')
            .prefetch_related('lines__variant__product')
        )

        allowed = WarehouseAccess.visible_to(self.request.user)
        queryset = queryset.filter(warehouse__in=allowed)

        params = self.request.query_params

        if kind := params.get('kind', '').strip():
            queryset = queryset.filter(kind=kind)

        if status_value := params.get('status', '').strip():
            queryset = queryset.filter(status=status_value)

        if warehouse := params.get('warehouse', '').strip():
            queryset = queryset.filter(warehouse_id=warehouse)

        if partner := params.get('partner', '').strip():
            queryset = queryset.filter(partner_id=partner)

        if search := params.get('search', '').strip():
            queryset = queryset.filter(
                Q(number__icontains=search)
                | Q(external_number__icontains=search)
                | Q(partner__name__icontains=search)
            )

        if date_from := params.get('date_from', '').strip():
            queryset = queryset.filter(date__gte=date_from)

        if date_to := params.get('date_to', '').strip():
            queryset = queryset.filter(date__lte=date_to)

        return queryset

    @action(detail=True, methods=['post'])
    def confirm(self, request, pk=None):
        """Hujjatni tasdiqlaydi va qoldiqqa yozadi."""
        document = self.get_object()

        try:
            services.confirm(document, user=request.user)
        except DjangoValidationError as exc:
            return Response({'detail': exc.messages}, status=400)

        return Response(self.get_serializer(self._reload(document)).data)

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """Hujjatni bekor qiladi — teskari yozuvlar bilan."""
        document = self.get_object()

        try:
            services.cancel(
                document, user=request.user, note=request.data.get('note', '')
            )
        except DjangoValidationError as exc:
            return Response({'detail': exc.messages}, status=400)

        return Response(self.get_serializer(self._reload(document)).data)

    def _reload(self, document):
        """Obyektni bazadan qayta o'qiydi.

        `get_object()` `prefetch_related` bilan keladi; amal bajarilgach
        keshdagi qatorlar eskirgan bo'ladi va javobda eski summalar
        ko'rinadi.
        """
        return self.get_queryset().get(pk=document.pk)

    @action(detail=False, methods=['get'])
    def summary(self, request):
        """Davr bo'yicha jamlanma — dizayndagi hisobot kartalari uchun."""
        queryset = self.filter_queryset(self.get_queryset()).filter(
            status=Document.Status.CONFIRMED
        )

        def totals(kind):
            rows = queryset.filter(kind=kind).aggregate(
                count=Count('id'),
                amount=Sum('total_amount'),
                cost=Sum('total_cost'),
            )
            amount = rows['amount'] or Decimal('0')
            cost = rows['cost'] or Decimal('0')

            return {
                'count': rows['count'],
                'amount': amount,
                'cost': cost,
                'profit': amount - cost,
            }

        purchases = totals(Document.Kind.PURCHASE)
        sales = totals(Document.Kind.SALE)

        return Response({
            'purchases': purchases,
            'sales': sales,
            # Foyda faqat sotuvda ma'noga ega: kirimda tannarx nol
            'profit': sales['profit'],
            'margin_percent': (
                round(float(sales['profit'] / sales['amount'] * 100), 1)
                if sales['amount']
                else 0.0
            ),
        })
