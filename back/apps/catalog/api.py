"""Katalog API si."""

from __future__ import annotations

from django.db.models import Count, Q
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.catalog import attributes as attr_service
from apps.catalog.models import (
    AttributeDefinition,
    Barcode,
    Category,
    Product,
    ProductUnit,
    Variant,
)
from apps.catalog.serializers import (
    AttributeDefinitionSerializer,
    BarcodeSerializer,
    CategorySerializer,
    ProductSerializer,
    ProductUnitSerializer,
    VariantSerializer,
)
from apps.core.access import FinancialRedactionMixin, Perm
from apps.core.permissions import SectionPermission


class CategoryViewSet(viewsets.ModelViewSet):
    """Kategoriya daraxti.

    Queryset `tenant_id` bo'yicha ochiq filtrlanmaydi — buni RLS bajaradi.
    """

    serializer_class = CategorySerializer
    permission_classes = [SectionPermission]
    section_permissions = {'write': {Perm.CATEGORIES}}
    pagination_class = None  # daraxt to'liq kerak

    def get_queryset(self):
        queryset = Category.objects.annotate(product_count=Count('products'))

        params = self.request.query_params

        if search := params.get('search', '').strip():
            queryset = queryset.filter(name__icontains=search)

        if parent := params.get('parent', '').strip():
            queryset = queryset.filter(parent_id=parent)

        return queryset.order_by('path')

    @action(detail=True, methods=['get'])
    def attributes(self, request, pk=None):
        """Shu kategoriyada amal qiladigan atributlar (meros bilan).

        Interfeys mahsulot formasini shu ro'yxatga qarab quradi:
        kategoriya almashtirilsa, maydonlar ham almashadi.
        """
        category = self.get_object()
        definitions = attr_service.definitions_for(category)

        return Response(AttributeDefinitionSerializer(definitions, many=True).data)


class AttributeDefinitionViewSet(viewsets.ModelViewSet):
    serializer_class = AttributeDefinitionSerializer
    permission_classes = [SectionPermission]
    section_permissions = {'write': {Perm.CATEGORIES}}

    def get_queryset(self):
        queryset = AttributeDefinition.objects.select_related('category')

        if category := self.request.query_params.get('category', '').strip():
            queryset = queryset.filter(category_id=category)

        return queryset


class ProductViewSet(FinancialRedactionMixin, viewsets.ModelViewSet):
    serializer_class = ProductSerializer
    permission_classes = [SectionPermission]
    section_permissions = {'write': {Perm.PRODUCTS}}

    def get_queryset(self):
        queryset = (
            Product.objects.select_related('category')
            .prefetch_related('variants__units', 'variants__barcodes')
        )

        params = self.request.query_params

        if search := params.get('search', '').strip():
            queryset = queryset.filter(
                Q(name__icontains=search)
                | Q(brand__icontains=search)
                | Q(model__icontains=search)
                | Q(variants__sku__icontains=search)
            ).distinct()

        if category := params.get('category', '').strip():
            # Kategoriya bo'yicha filtrda ostki kategoriyalar ham kiradi —
            # "Qurilish" tanlansa "Sement" ham ko'rinsin.
            node = Category.objects.filter(pk=category).first()

            if node and node.path:
                queryset = queryset.filter(category__path__descendant_of=node.path)
            else:
                queryset = queryset.none()

        if (active := params.get('is_active', '').strip()) in {'true', 'false'}:
            queryset = queryset.filter(is_active=active == 'true')

        return queryset


class VariantViewSet(FinancialRedactionMixin, viewsets.ModelViewSet):
    serializer_class = VariantSerializer
    permission_classes = [SectionPermission]
    section_permissions = {'write': {Perm.PRODUCTS}}

    def get_queryset(self):
        queryset = (
            Variant.objects.select_related('product', 'product__category')
            .prefetch_related('units', 'barcodes')
        )

        params = self.request.query_params

        if product := params.get('product', '').strip():
            queryset = queryset.filter(product_id=product)

        if search := params.get('search', '').strip():
            queryset = queryset.filter(
                Q(sku__icontains=search) | Q(product__name__icontains=search)
            )

        return queryset

    @action(detail=False, methods=['get'], url_path='by-barcode')
    def by_barcode(self, request):
        """Shtrix-kod bo'yicha variant topadi — kassa uchun.

        Qidiruv normalizatsiyalangan kalit bo'yicha ketadi, ya'ni
        skaner qo'shgan bo'shliq yoki registr farqi xalaqit bermaydi.
        """
        code = request.query_params.get('code', '')
        normalized = Barcode.normalize(code)

        if not normalized:
            return Response({'detail': 'Kod korsatilmagan.'}, status=400)

        barcode = (
            Barcode.objects.filter(code_normalized=normalized)
            .select_related('variant__product')
            .first()
        )

        if barcode is None:
            return Response({'detail': 'Bunday kod topilmadi.'}, status=404)

        return Response(VariantSerializer(barcode.variant).data)


class ProductUnitViewSet(viewsets.ModelViewSet):
    """O'ram birliklari: «1 qop = 50 kg»."""

    serializer_class = ProductUnitSerializer
    permission_classes = [SectionPermission]
    section_permissions = {'write': {Perm.PRODUCTS}}

    def get_queryset(self):
        queryset = ProductUnit.objects.select_related('variant')

        if variant := self.request.query_params.get('variant', '').strip():
            queryset = queryset.filter(variant_id=variant)

        return queryset


class BarcodeViewSet(viewsets.ModelViewSet):
    serializer_class = BarcodeSerializer
    permission_classes = [SectionPermission]
    section_permissions = {'write': {Perm.PRODUCTS}}

    def get_queryset(self):
        queryset = Barcode.objects.select_related('variant')

        if variant := self.request.query_params.get('variant', '').strip():
            queryset = queryset.filter(variant_id=variant)

        return queryset
