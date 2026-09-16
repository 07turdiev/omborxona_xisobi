from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError
from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.dates import today_bounds
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


def full_sales():
    return Sale.objects.select_related('cashier').prefetch_related(*SALE_RELATIONS)


def full_returns():
    return SaleReturn.objects.select_related('sale').prefetch_related(
        'lines__sale_line__variant__product',
        'lines__sale_line__variant__size',
        'lines__sale_line__variant__color',
    )


def receipt_number(value: str) -> str:
    """Chek raqami yoki chekdagi raqamli kod.

    Chekka faqat raqam bosiladi ('2026000001'): skaner kodni klaviatura
    orqali yozadi va 'SOT-' harflari klaviatura tiliga bog'liq bo'lib
    qolardi. Shuning uchun raqamli kod ham, to'liq raqam ham qabul
    qilinadi.
    """
    if value.isdigit() and len(value) == 10:
        return f'SOT-{value[:4]}-{value[4:]}'

    return value


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

    # Haqiqiy tanlov `get_queryset` da; bu — sxema generatori uchun
    queryset = Sale.objects.none()
    serializer_class = SaleSerializer

    def get_queryset(self):
        queryset = full_sales()
        params = self.request.query_params
        number = (params.get('number') or '').strip()

        if number:
            # Qaytarish uchun: kassir istalgan chekni raqami (yoki chekdagi
            # shtrix-kod) bo'yicha topa oladi — aks holda kechagi chekni
            # qaytarib bo'lmasdi.
            return queryset.filter(number__iexact=receipt_number(number))

        if not self.request.user.is_admin:
            # Ro'yxatda kassir faqat o'zining bugungi cheklarini ko'radi
            start, _end = today_bounds()
            queryset = queryset.filter(cashier=self.request.user, created_at__gte=start)

        if status_filter := params.get('status'):
            queryset = queryset.filter(status=status_filter)

        if date_from := params.get('date_from'):
            queryset = queryset.filter(created_at__date__gte=date_from)

        if date_to := params.get('date_to'):
            queryset = queryset.filter(created_at__date__lte=date_to)

        return queryset

    def create(self, request, *args, **kwargs):
        """Chekni yozadi: qatorlar, jurnal va qoldiq bitta tranzaksiyada.

        `request_key` berilgan bo'lsa, o'sha kalit bilan yozilgan chek
        allaqachon bor-yo'qligi tekshiriladi: tugma ikki marta bosilsa
        ikkinchi chek yaratilmaydi.
        """
        form = SaleCreateSerializer(data=request.data)
        form.is_valid(raise_exception=True)

        data = dict(form.validated_data)
        request_key = data.pop('request_key', None)

        if request_key:
            existing = full_sales().filter(request_key=request_key).first()

            if existing is not None:
                return Response(self.get_serializer(existing).data, status=200)

        try:
            sale = services.create_sale(user=request.user, request_key=request_key, **data)
        except DjangoValidationError as exc:
            return Response({'detail': exc.messages}, status=400)
        except IntegrityError:
            # Ikki so'rov bir vaqtda kelgan: birinchisi yozdi, bu — takror
            existing = full_sales().get(request_key=request_key)

            return Response(self.get_serializer(existing).data, status=200)

        return Response(
            self.get_serializer(full_sales().get(pk=sale.pk)).data, status=201
        )

    @action(detail=True, methods=['post'], permission_classes=[IsAdmin])
    def void(self, request, pk=None):
        """Chekni bekor qilish — administrator, faqat o'sha kuni."""
        sale = self.get_object()

        try:
            services.void_sale(sale, user=request.user)
        except DjangoValidationError as exc:
            return Response({'detail': exc.messages}, status=400)

        return Response(self.get_serializer(full_sales().get(pk=sale.pk)).data)


class SaleReturnViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    viewsets.GenericViewSet,
):
    """Qaytarishlar. Kassir ro'yxatda o'zining bugungilarini ko'radi."""

    queryset = SaleReturn.objects.none()
    serializer_class = SaleReturnSerializer

    def get_queryset(self):
        queryset = full_returns()

        if not self.request.user.is_admin:
            start, _end = today_bounds()
            queryset = queryset.filter(created_by=self.request.user, created_at__gte=start)

        if sale := self.request.query_params.get('sale'):
            queryset = queryset.filter(sale_id=sale)

        return queryset

    def create(self, request, *args, **kwargs):
        form = SaleReturnCreateSerializer(data=request.data)
        form.is_valid(raise_exception=True)

        data = form.validated_data
        request_key = data.get('request_key')

        if request_key:
            existing = full_returns().filter(request_key=request_key).first()

            if existing is not None:
                return Response(self.get_serializer(existing).data, status=200)

        try:
            sale_return = services.create_return(
                sale=data['sale'],
                items=data['items'],
                refund_method=data['refund_method'],
                user=request.user,
                request_key=request_key,
            )
        except DjangoValidationError as exc:
            return Response({'detail': exc.messages}, status=400)
        except IntegrityError:
            existing = full_returns().get(request_key=request_key)

            return Response(self.get_serializer(existing).data, status=200)

        return Response(
            self.get_serializer(full_returns().get(pk=sale_return.pk)).data, status=201
        )


class ExchangeView(APIView):
    """Almashtirish: qaytarish + yangi sotuv, farqi bilan.

    Kassir bitta sonni ko'radi: `difference` musbat bo'lsa mijozdan
    olinadi, manfiy bo'lsa mijozga qaytariladi.
    """

    serializer_class = ExchangeSerializer

    def post(self, request):
        form = ExchangeSerializer(data=request.data)
        form.is_valid(raise_exception=True)

        data = form.validated_data
        request_key = data.get('request_key')
        context = {'request': request}

        if request_key:
            existing_sale = full_sales().filter(request_key=request_key).first()
            existing_return = full_returns().filter(request_key=request_key).first()

            if existing_sale is not None and existing_return is not None:
                return Response(self._payload(existing_return, existing_sale, context), status=200)

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
                request_key=request_key,
            )
        except DjangoValidationError as exc:
            return Response({'detail': exc.messages}, status=400)
        except IntegrityError:
            existing_sale = full_sales().get(request_key=request_key)
            existing_return = full_returns().get(request_key=request_key)

            return Response(self._payload(existing_return, existing_sale, context), status=200)

        return Response(
            self._payload(result['sale_return'], result['sale'], context), status=201
        )

    @staticmethod
    def _payload(sale_return, sale, context) -> dict:
        return {
            'sale_return': SaleReturnSerializer(sale_return, context=context).data,
            'sale': SaleSerializer(sale, context=context).data,
            'difference': str(sale.total - sale_return.total),
        }
