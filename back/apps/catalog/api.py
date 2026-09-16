from django.db.models import Count, F, Q
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.response import Response

from apps.catalog.models import Category, Color, Product, Size, Variant
from apps.catalog.serializers import (
    CategorySerializer,
    ColorSerializer,
    ProductSerializer,
    SizeSerializer,
    VariantSerializer,
)
from apps.core.permissions import IsAdminOrReadOnly


class CategoryViewSet(viewsets.ModelViewSet):
    serializer_class = CategorySerializer
    permission_classes = [IsAdminOrReadOnly]
    pagination_class = None

    def get_queryset(self):
        return Category.objects.annotate(product_count=Count('products'))


class SizeViewSet(viewsets.ModelViewSet):
    queryset = Size.objects.all()
    serializer_class = SizeSerializer
    permission_classes = [IsAdminOrReadOnly]
    pagination_class = None


class ColorViewSet(viewsets.ModelViewSet):
    queryset = Color.objects.all()
    serializer_class = ColorSerializer
    permission_classes = [IsAdminOrReadOnly]
    pagination_class = None


class ProductViewSet(viewsets.ModelViewSet):
    """Mahsulotlar. Kassir ko'radi, administrator o'zgartiradi."""

    serializer_class = ProductSerializer
    permission_classes = [IsAdminOrReadOnly]

    def get_queryset(self):
        queryset = Product.objects.select_related('category').prefetch_related(
            'variants__size', 'variants__color', 'variants__product'
        )

        params = self.request.query_params

        if search := params.get('search'):
            queryset = queryset.filter(
                Q(name__icontains=search)
                | Q(brand__icontains=search)
                | Q(variants__sku__icontains=search)
                | Q(variants__barcode=search)
            ).distinct()

        if category := params.get('category'):
            queryset = queryset.filter(category_id=category)

        if params.get('active') == 'true':
            queryset = queryset.filter(is_active=True)

        return queryset


class VariantViewSet(viewsets.ModelViewSet):
    """Variantlar: narx, minimal qoldiq va faollik shu yerda o'zgaradi.

    Yaratish faqat mahsulot orqali (matritsa), o'chirish yo'q: qoldiq va
    sotuv tarixi bog'langan variantni o'chirib bo'lmaydi — u
    faolsizlantiriladi.
    """

    serializer_class = VariantSerializer
    permission_classes = [IsAdminOrReadOnly]
    http_method_names = ['get', 'patch', 'head', 'options']

    def get_queryset(self):
        queryset = Variant.objects.select_related(
            'product', 'product__category', 'size', 'color'
        )

        params = self.request.query_params

        if search := params.get('search'):
            queryset = queryset.filter(
                Q(product__name__icontains=search)
                | Q(sku__icontains=search)
                | Q(barcode=search)
            )

        if category := params.get('category'):
            queryset = queryset.filter(product__category_id=category)

        if params.get('low_stock') == 'true':
            # Faqat minimal qoldiq belgilangan variantlar
            queryset = queryset.filter(min_stock__gt=0, stock_quantity__lte=F('min_stock'))

        if params.get('active') == 'true':
            queryset = queryset.filter(is_active=True)

        return queryset

    @action(detail=False, url_path='by-barcode')
    def by_barcode(self, request):
        """Skaner uchun: kod bo'yicha variantni topadi."""
        code = (request.query_params.get('code') or '').strip()

        if not code:
            raise ValidationError({'code': 'Shtrix-kod ko‘rsatilmagan.'})

        variant = (
            Variant.objects.select_related('product', 'size', 'color')
            .filter(barcode=code)
            .first()
        )

        if variant is None:
            raise NotFound('Bu shtrix-kod bo‘yicha tovar topilmadi.')

        return Response(self.get_serializer(variant).data)
