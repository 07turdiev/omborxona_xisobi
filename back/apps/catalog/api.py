from django.db.models import Count, Exists, OuterRef, Q, Subquery, Sum
from django.db.models.functions import Coalesce
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.response import Response

from apps.catalog.models import (
    LOW_STOCK,
    Category,
    Color,
    Product,
    ProductImage,
    Size,
    Variant,
)
from apps.catalog.serializers import (
    CatalogProductListSerializer,
    CatalogProductSerializer,
    CategorySerializer,
    ColorSerializer,
    ProductImageSerializer,
    ProductSerializer,
    SizeSerializer,
    VariantSerializer,
)
from apps.catalog.services import add_variant, remove_product_image, reorder_images
from apps.core.permissions import IsAdmin, IsAdminOrReadOnly


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

    @action(detail=True, methods=['post'], url_path='variants')
    def add_variant(self, request, pk=None):
        """Modelga bitta variant qo'shadi: `{"size": 3, "color": 5}`.

        Kirim ekranidagi «+ O'lcham yoki rang» shu yerga murojaat qiladi:
        model ko'k M va L bo'lib, qizil XL kelsa, faqat qizil XL
        yaratiladi. To'liq matritsa mahsulot formasida qoladi.
        """
        product = self.get_object()

        size = self._lookup(Size, request.data.get('size'), 'O‘lcham')
        color = self._lookup(Color, request.data.get('color'), 'Rang')

        if size is None and color is None:
            raise ValidationError('O‘lcham yoki rang tanlang.')

        existed = product.variants.filter(size=size, color=color).exists()
        variant = add_variant(product, size=size, color=color)

        return Response(
            VariantSerializer(variant, context=self.get_serializer_context()).data,
            status=200 if existed else 201,
        )

    @staticmethod
    def _lookup(model, value, label):
        """Bo'sh qiymat — «yo'q» degani (o'lchamsiz yoki rangsiz variant)."""
        if value in (None, ''):
            return None

        found = model.objects.filter(pk=value).first()

        if found is None:
            raise NotFound(f'{label} topilmadi.')

        return found


class CatalogViewSet(viewsets.ReadOnlyModelViewSet):
    """Xodimlar uchun katalog: rasm, rang, o'lcham va qoldiq.

    Ikkala rol ham ko'radi. Tannarx faqat administrator javobida bo'ladi
    (`CatalogVariantSerializer`).
    """

    permission_classes = [IsAdminOrReadOnly]

    #: `?ordering=` qiymatlari. `-` — teskari tartib (DRF odati).
    #: Ikkinchi maydon sahifalash barqaror bo'lishi uchun.
    ORDERING = {
        'newest': ('-created_at', '-id'),
        'name': ('name', 'id'),
        '-name': ('-name', '-id'),
        'stock': ('total_stock', 'name'),
        '-stock': ('-total_stock', 'name'),
    }

    def get_serializer_class(self):
        if self.action == 'list':
            return CatalogProductListSerializer

        return CatalogProductSerializer

    def get_queryset(self):
        # Qoldiq alohida so'rovda hisoblanadi. `Sum('variants__...')` bo'lsa,
        # qidiruv yoki filtr variantlarga yana JOIN qo'shganda qatorlar
        # ko'payadi va yig'indi variantlar soniga ko'paytirilib chiqadi.
        # Filtrlar ham shu sababli JOIN emas, `Exists` bilan yozilgan.
        variants = Variant.objects.filter(product=OuterRef('pk'))

        stock = variants.values('product').annotate(total=Sum('stock_quantity')).values('total')

        queryset = (
            Product.objects.select_related('category')
            .prefetch_related('images__color', 'variants__size', 'variants__color')
            .annotate(total_stock=Coalesce(Subquery(stock), 0))
        )

        params = self.request.query_params

        # Nomi, brendi, artikuli yoki shtrix-kodi — mahsulotlar sahifasi
        # birlashtirilgan, qoldiq sahifasidagi SKU qidiruvi ham shu yerda
        if search := params.get('search', '').strip():
            queryset = queryset.filter(
                Exists(variants.filter(Q(barcode=search) | Q(sku__icontains=search)))
                | Q(name__icontains=search)
                | Q(brand__icontains=search)
            )

        if category := params.get('category'):
            queryset = queryset.filter(category_id=category)

        if params.get('in_stock') == 'true':
            queryset = queryset.filter(total_stock__gt=0)

        if params.get('low_stock') == 'true':
            queryset = queryset.filter(Exists(variants.filter(LOW_STOCK)))

        if params.get('active') != 'false':
            queryset = queryset.filter(is_active=True)

        ordering = self.ORDERING.get(params.get('ordering', ''), self.ORDERING['newest'])

        return queryset.order_by(*ordering)


class ProductImageViewSet(viewsets.ModelViewSet):
    """Mahsulot rasmlari — yuklash, tartiblash, asosiysini tanlash.

    Faqat administrator: rasm katalogning ko'rinishini belgilaydi.
    """

    serializer_class = ProductImageSerializer
    permission_classes = [IsAdmin]
    pagination_class = None

    def get_queryset(self):
        queryset = ProductImage.objects.select_related('color')

        if product := self.request.query_params.get('product'):
            queryset = queryset.filter(product_id=product)

        return queryset

    def perform_destroy(self, instance):
        remove_product_image(instance)

    @action(detail=False, methods=['post'])
    def reorder(self, request):
        """Rasmlar tartibi: `{"product": 1, "images": [12, 10, 11]}`."""
        product_id = request.data.get('product')
        image_ids = request.data.get('images')

        if not product_id or not isinstance(image_ids, list):
            raise ValidationError('Mahsulot va rasmlar ro‘yxati kerak.')

        product = Product.objects.filter(pk=product_id).first()

        if product is None:
            raise NotFound('Mahsulot topilmadi.')

        reorder_images(product, image_ids)

        return Response(
            ProductImageSerializer(
                product.images.all(), many=True, context={'request': request}
            ).data
        )


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
            queryset = queryset.filter(LOW_STOCK)

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
