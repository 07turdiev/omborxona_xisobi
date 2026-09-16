from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.core.permissions import IsAdmin
from apps.inventory import services
from apps.inventory.models import StockCount, StockMovement, WriteOff
from apps.inventory.serializers import (
    StockCountSerializer,
    StockMovementSerializer,
    WriteOffSerializer,
)


class StockMovementViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    """Ombor jurnali — o'zgartirilmaydi, faqat o'qiladi."""

    serializer_class = StockMovementSerializer
    permission_classes = [IsAdmin]

    def get_queryset(self):
        queryset = StockMovement.objects.select_related(
            'variant', 'variant__product', 'variant__size', 'variant__color', 'user'
        )

        params = self.request.query_params

        if variant := params.get('variant'):
            queryset = queryset.filter(variant_id=variant)

        if reason := params.get('reason'):
            queryset = queryset.filter(reason=reason)

        return queryset


class StockCountViewSet(viewsets.ModelViewSet):
    """Inventarizatsiya: qoralama tuziladi, keyin tasdiqlanadi."""

    serializer_class = StockCountSerializer
    permission_classes = [IsAdmin]
    http_method_names = ['get', 'post', 'patch', 'delete', 'head', 'options']

    def get_queryset(self):
        return StockCount.objects.select_related('category').prefetch_related(
            'lines__variant__product', 'lines__variant__size', 'lines__variant__color'
        )

    def perform_destroy(self, instance):
        if instance.status != StockCount.Status.DRAFT:
            raise DjangoValidationError('Tasdiqlangan inventarizatsiyani o‘chirib bo‘lmaydi')

        instance.delete()

    @action(detail=True, methods=['post'])
    def confirm(self, request, pk=None):
        """Farqlarni jurnalga yozadi va qoldiqni tenglashtiradi."""
        stock_count = self.get_object()

        try:
            services.confirm_stock_count(stock_count, user=request.user)
        except DjangoValidationError as exc:
            return Response({'detail': exc.messages}, status=400)

        return Response(self.get_serializer(self.get_object()).data)


class WriteOffViewSet(
    mixins.ListModelMixin, mixins.CreateModelMixin, viewsets.GenericViewSet
):
    """Hisobdan chiqarish. O'chirish yo'q: yozuv tarixda qoladi."""

    serializer_class = WriteOffSerializer
    permission_classes = [IsAdmin]

    def get_queryset(self):
        return WriteOff.objects.select_related(
            'variant', 'variant__product', 'variant__size', 'variant__color'
        )

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            write_off = services.create_write_off(
                variant=serializer.validated_data['variant'],
                quantity=serializer.validated_data['quantity'],
                reason=serializer.validated_data['reason'],
                user=request.user,
            )
        except DjangoValidationError as exc:
            return Response({'detail': exc.messages}, status=400)

        return Response(self.get_serializer(write_off).data, status=201)
