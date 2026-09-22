from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.core.permissions import IsAdmin
from apps.purchases import services
from apps.purchases.models import Purchase, Supplier, SupplierPayment
from apps.purchases.serializers import (
    PurchaseSerializer,
    SupplierPaymentSerializer,
    SupplierSerializer,
)


class SupplierViewSet(viewsets.ModelViewSet):
    """Ta'minotchilar — faqat administrator uchun."""

    queryset = Supplier.objects.all()
    serializer_class = SupplierSerializer
    permission_classes = [IsAdmin]
    http_method_names = ['get', 'post', 'patch', 'head', 'options']


class SupplierPaymentViewSet(viewsets.ModelViewSet):
    serializer_class = SupplierPaymentSerializer
    permission_classes = [IsAdmin]
    http_method_names = ['get', 'post', 'head', 'options']

    def get_queryset(self):
        queryset = SupplierPayment.objects.select_related('supplier')

        if supplier := self.request.query_params.get('supplier'):
            queryset = queryset.filter(supplier_id=supplier)

        return queryset

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


class PurchaseViewSet(viewsets.ModelViewSet):
    """Kirim hujjatlari: qoralama → tasdiqlangan (yoki bekor qilingan)."""

    serializer_class = PurchaseSerializer
    permission_classes = [IsAdmin]

    def get_queryset(self):
        queryset = Purchase.objects.select_related(
            'supplier', 'created_by', 'location'
        ).prefetch_related(
            'lines__variant__product', 'lines__variant__size', 'lines__variant__color'
        )

        params = self.request.query_params

        if status_filter := params.get('status'):
            queryset = queryset.filter(status=status_filter)

        if supplier := params.get('supplier'):
            queryset = queryset.filter(supplier_id=supplier)

        if date_from := params.get('date_from'):
            queryset = queryset.filter(date__gte=date_from)

        if date_to := params.get('date_to'):
            queryset = queryset.filter(date__lte=date_to)

        return queryset

    def perform_destroy(self, instance):
        if not instance.is_editable:
            raise DjangoValidationError('Tasdiqlangan kirimni o‘chirib bo‘lmaydi')

        instance.delete()

    @action(detail=True, methods=['post'])
    def confirm(self, request, pk=None):
        """Tovarni omborga kiritadi."""
        purchase = self.get_object()

        try:
            services.confirm(purchase, user=request.user)
        except DjangoValidationError as exc:
            return Response({'detail': exc.messages}, status=400)

        return Response(self.get_serializer(self.get_object()).data)

    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """Tasdiqlangan kirimni teskari yozuvlar bilan bekor qiladi."""
        purchase = self.get_object()

        try:
            services.cancel(purchase, user=request.user)
        except DjangoValidationError as exc:
            return Response({'detail': exc.messages}, status=400)

        return Response(self.get_serializer(self.get_object()).data)
