from collections import defaultdict

from django.apps import apps
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


#: Jurnaldagi `document_type` → hujjat modeli.
#: Hisobdan chiqarishning raqami yo'q, shuning uchun u bu ro'yxatda emas.
DOCUMENT_MODELS = {
    'purchase': 'purchases.Purchase',
    'sale': 'sales.Sale',
    'salereturn': 'sales.SaleReturn',
    'stockcount': 'inventory.StockCount',
}


def document_numbers(movements) -> dict:
    """Sahifadagi yozuvlar hujjatlarining raqamlari.

    Har hujjat turi uchun bitta so'rov — yozuv boshiga alohida so'rov
    bo'lsa, 25 qatorli sahifa 25 ta qo'shimcha so'rov qilardi.
    """
    wanted = defaultdict(set)

    for movement in movements:
        if movement.document_type in DOCUMENT_MODELS and movement.document_id:
            wanted[movement.document_type].add(movement.document_id)

    documents = {}

    for document_type, ids in wanted.items():
        model = apps.get_model(DOCUMENT_MODELS[document_type])
        fields = ['pk', 'number']

        if document_type == 'salereturn':
            fields.append('sale__number')

        for row in model.objects.filter(pk__in=ids).values(*fields):
            documents[(document_type, row['pk'])] = {
                'number': row['number'],
                'sale_number': row.get('sale__number'),
            }

    return documents


class StockMovementViewSet(mixins.ListModelMixin, viewsets.GenericViewSet):
    """Ombor jurnali — o'zgartirilmaydi, faqat o'qiladi."""

    serializer_class = StockMovementSerializer
    permission_classes = [IsAdmin]

    def list(self, request, *args, **kwargs):
        page = self.paginate_queryset(self.filter_queryset(self.get_queryset()))

        context = {**self.get_serializer_context(), 'documents': document_numbers(page)}
        serializer = self.get_serializer(page, many=True, context=context)

        return self.get_paginated_response(serializer.data)

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
