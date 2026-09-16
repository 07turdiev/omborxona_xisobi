from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.permissions import IsAdmin
from apps.sales import services
from apps.sales.models import Sale, SaleReturn
from apps.sales.serializers import (
    ExchangeSerializer,
    SaleCreateSerializer,
    SaleReturnCreateSerializer,
    SaleReturnSerializer,
    SaleSerializer,
)

SALE_RELATIONS = (
    'lines__variant__product',
    'lines__variant__size',
    'lines__variant__color',
    'lines__return_lines',
)


class SaleViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    viewsets.GenericViewSet,
):
    """Kassa: sotuv yaratish va cheklarni ko'rish.

    Kassir ham ishlaydi, lekin javobda tannarx va foyda bo'lmaydi
    (`HideFromCashierMixin`).
    """

    serializer_class = SaleSerializer

    def get_queryset(self):
        queryset = Sale.objects.select_related('cashier').prefetch_related(*SALE_RELATIONS)
        params = self.request.query_params

        if number := params.get('number'):
            queryset = queryset.filter(number__iexact=number.strip())

        if status_filter := params.get('status'):
            queryset = queryset.filter(status=status_filter)

        if date_from := params.get('date_from'):
            queryset = queryset.filter(created_at__date__gte=date_from)

        if date_to := params.get('date_to'):
            queryset = queryset.filter(created_at__date__lte=date_to)

        return queryset

    def create(self, request, *args, **kwargs):
        """Chekni yozadi: qatorlar, jurnal va qoldiq bitta tranzaksiyada."""
        form = SaleCreateSerializer(data=request.data)
        form.is_valid(raise_exception=True)

        try:
            sale = services.create_sale(user=request.user, **form.validated_data)
        except DjangoValidationError as exc:
            return Response({'detail': exc.messages}, status=400)

        return Response(self.get_serializer(self._reload(sale)).data, status=201)

    @action(detail=True, methods=['post'], permission_classes=[IsAdmin])
    def void(self, request, pk=None):
        """Chekni bekor qilish — administrator, faqat o'sha kuni."""
        sale = self.get_object()

        try:
            services.void_sale(sale, user=request.user)
        except DjangoValidationError as exc:
            return Response({'detail': exc.messages}, status=400)

        return Response(self.get_serializer(self._reload(sale)).data)

    def _reload(self, sale):
        return self.get_queryset().get(pk=sale.pk)


class SaleReturnViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    viewsets.GenericViewSet,
):
    """Qaytarishlar."""

    serializer_class = SaleReturnSerializer

    def get_queryset(self):
        queryset = SaleReturn.objects.select_related('sale').prefetch_related(
            'lines__sale_line__variant__product',
            'lines__sale_line__variant__size',
            'lines__sale_line__variant__color',
        )

        if sale := self.request.query_params.get('sale'):
            queryset = queryset.filter(sale_id=sale)

        return queryset

    def create(self, request, *args, **kwargs):
        form = SaleReturnCreateSerializer(data=request.data)
        form.is_valid(raise_exception=True)

        try:
            sale_return = services.create_return(
                sale=form.validated_data['sale'],
                items=form.validated_data['items'],
                refund_method=form.validated_data['refund_method'],
                user=request.user,
            )
        except DjangoValidationError as exc:
            return Response({'detail': exc.messages}, status=400)

        return Response(
            self.get_serializer(self.get_queryset().get(pk=sale_return.pk)).data, status=201
        )


class ExchangeView(APIView):
    """Almashtirish: qaytarish + yangi sotuv, farqi bilan."""

    def post(self, request):
        form = ExchangeSerializer(data=request.data)
        form.is_valid(raise_exception=True)

        data = form.validated_data

        try:
            result = services.exchange(
                user=request.user,
                sale=data['sale'],
                return_items=data['items'],
                lines=data['lines'],
                refund_method=data['refund_method'],
                cash_amount=data['cash_amount'],
                card_amount=data['card_amount'],
                discount_amount=data.get('discount_amount'),
                discount_percent=data.get('discount_percent'),
            )
        except DjangoValidationError as exc:
            return Response({'detail': exc.messages}, status=400)

        context = {'request': request}

        return Response(
            {
                'sale_return': SaleReturnSerializer(result['sale_return'], context=context).data,
                'sale': SaleSerializer(result['sale'], context=context).data,
                'difference': str(result['difference']),
            },
            status=201,
        )
