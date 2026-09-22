from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers
from rest_framework.validators import UniqueValidator

from apps.catalog.models import Category, Color, Product, ProductImage, Size, Variant
from apps.catalog.services import add_product_image, set_primary_image, sync_variant_matrix
from apps.core.redaction import HideFromCashierMixin


class CategorySerializer(serializers.ModelSerializer):
    product_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = Category
        fields = ('id', 'name', 'product_count')


class SizeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Size
        fields = ('id', 'name', 'position')


class ColorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Color
        fields = ('id', 'name', 'hex_code')


class ProductImageSerializer(serializers.ModelSerializer):
    """Mahsulot rasmi. Yuklashda `image` maydoni keladi, javobda — uch o'lcham.

    `ImageField` emas, `FileField`: DRF ning o'z tekshiruvi inglizcha xabar
    beradi, bu yerda esa xabar o'zbekcha bo'lishi kerak (`images.py`).
    """

    image = serializers.FileField(write_only=True)

    class Meta:
        model = ProductImage
        fields = (
            'id', 'product', 'color', 'image', 'thumb', 'medium', 'large',
            'sort_order', 'is_primary',
        )
        read_only_fields = ('id', 'thumb', 'medium', 'large', 'sort_order')

    def create(self, validated_data):
        try:
            return add_product_image(
                validated_data['product'],
                validated_data['image'],
                color=validated_data.get('color'),
            )
        except DjangoValidationError as error:
            # Xizmat Django xatosini tashlaydi, DRF esa faqat o'zinikini
            # 400 ga aylantiradi
            raise serializers.ValidationError({'image': error.messages}) from error

    def update(self, instance, validated_data):
        make_primary = validated_data.pop('is_primary', None)

        image = super().update(instance, validated_data)

        if make_primary:
            # Bitta mahsulotda bitta asosiy rasm — baza cheklovi ham shuni
            # talab qiladi, shuning uchun eskisi xizmatda olib tashlanadi
            set_primary_image(image)

        return image


class VariantSerializer(HideFromCashierMixin, serializers.ModelSerializer):
    """Variant. Tannarxni faqat administrator ko'radi."""

    admin_only_fields = ('average_cost',)

    product_name = serializers.CharField(source='product.name', read_only=True)
    size_name = serializers.CharField(source='size.name', read_only=True, default=None)
    color_name = serializers.CharField(source='color.name', read_only=True, default=None)
    label = serializers.CharField(read_only=True)
    price = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)

    class Meta:
        model = Variant
        fields = (
            'id', 'product', 'product_name', 'size', 'size_name', 'color', 'color_name',
            'label', 'sku', 'barcode', 'sale_price', 'price', 'average_cost',
            'stock_quantity', 'min_stock', 'is_active',
        )
        read_only_fields = (
            'id', 'product', 'size', 'color', 'sku', 'average_cost', 'stock_quantity',
        )


class ProductSerializer(serializers.ModelSerializer):
    """Mahsulot va uning variantlari.

    `size_ids` va `color_ids` — matritsa uchun: har bir yetishmayotgan
    o'lcham × rang juftligiga variant yaratiladi.
    """

    category_name = serializers.CharField(source='category.name', read_only=True)
    variants = VariantSerializer(many=True, read_only=True)
    images = ProductImageSerializer(many=True, read_only=True)

    #: Bo'sh yuborilsa nomdan yasaladi (`Product.save`). Maydon ochiq
    #: e'lon qilinganda DRF o'zining takrorlanmaslik tekshiruvini
    #: qo'shmaydi — usiz takroriy slug 400 emas, 500 bilan tugardi.
    slug = serializers.SlugField(
        required=False,
        allow_blank=True,
        validators=[UniqueValidator(queryset=Product.objects.all())],
    )

    size_ids = serializers.ListField(
        child=serializers.IntegerField(), write_only=True, required=False
    )
    color_ids = serializers.ListField(
        child=serializers.IntegerField(), write_only=True, required=False
    )

    class Meta:
        model = Product
        fields = (
            'id', 'category', 'category_name', 'name', 'slug', 'brand', 'description',
            'material', 'care', 'sale_price', 'is_active', 'images', 'variants',
            'size_ids', 'color_ids',
        )
        read_only_fields = (
            'id', 'category_name', 'variants', 'images',
        )

    def create(self, validated_data):
        sizes = validated_data.pop('size_ids', [])
        colors = validated_data.pop('color_ids', [])

        product = super().create(validated_data)
        sync_variant_matrix(product, sizes, colors)

        return product

    def update(self, instance, validated_data):
        sizes = validated_data.pop('size_ids', None)
        colors = validated_data.pop('color_ids', None)

        product = super().update(instance, validated_data)

        if sizes is not None or colors is not None:
            sync_variant_matrix(product, sizes or [], colors or [])

        return product


# --- Katalog --------------------------------------------------------------
#
# Bular yuqoridagi administrator serializerlaridan **ataylab alohida**.
# Katalog — ko'rsatish uchun: tarkib, ranglar, rasmlar. Administrator
# serializeri esa tahrirlash uchun va unda matritsa kabi ichki
# maydonlar bor. Keyinchalik onlayn do'kon uchun ommaviy (autentifikatsiyasiz)
# serializer qo'shilsa, u shu yerdagilardan nusxa oladi va tahrirlash
# serializeriga umuman tegmaydi.


class CatalogImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = ('id', 'color', 'thumb', 'medium', 'large', 'is_primary', 'sort_order')


class CatalogVariantSerializer(HideFromCashierMixin, serializers.ModelSerializer):
    """Katalogdagi variant: qoldiq va narx. Tannarx — faqat administratorga."""

    admin_only_fields = ('average_cost',)

    size_name = serializers.CharField(source='size.name', read_only=True, default=None)
    color_name = serializers.CharField(source='color.name', read_only=True, default=None)
    price = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)

    class Meta:
        model = Variant
        fields = (
            'id', 'size', 'size_name', 'color', 'color_name', 'barcode',
            'price', 'average_cost', 'stock_quantity', 'is_active',
        )


class CatalogProductListSerializer(HideFromCashierMixin, serializers.ModelSerializer):
    """Ro'yxatdagi karta: rasm, nom, narx va umumiy qoldiq.

    Bu yerda rasmlar va variantlar to'liq berilmaydi — yigirma beshta
    mahsulotni ochishda ular javobni keraksiz kattalashtiradi.
    """

    category_name = serializers.CharField(source='category.name', read_only=True)
    total_stock = serializers.IntegerField(read_only=True)
    size_stock = serializers.SerializerMethodField()
    color_count = serializers.SerializerMethodField()
    primary_image = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = (
            'id', 'name', 'slug', 'category', 'category_name', 'brand',
            'sale_price', 'total_stock', 'size_stock', 'color_count',
            'primary_image',
        )

    def get_size_stock(self, product):
        """Har o'lcham bo'yicha qoldiq, hamma ranglar yig'indisi.

        Do'kondagi eng ko'p savol — "qaysi o'lcham qoldi", shuning uchun
        kartada mahsulotni ochmasdan "S 2 · M 0 · L 5" ko'rinishi kerak.
        Qoldig'i nol o'lcham ham ro'yxatda qoladi: "M tugagan" ham javob.
        """
        totals = {}

        for variant in product.variants.all():
            if variant.size is None:
                continue

            entry = totals.setdefault(variant.size_id, {
                'size_id': variant.size_id,
                'size_name': variant.size.name,
                'position': variant.size.position,
                'quantity': 0,
            })
            entry['quantity'] += variant.stock_quantity

        return sorted(totals.values(), key=lambda entry: (entry['position'], entry['size_name']))

    def get_color_count(self, product) -> int:
        """Nechta rangda bor — kirim ekranidagi qisqa qator uchun."""
        return len({
            variant.color_id for variant in product.variants.all() if variant.color_id
        })

    def get_primary_image(self, product):
        images = list(product.images.all())
        primary = next((image for image in images if image.is_primary), None) or (
            images[0] if images else None
        )

        if primary is None:
            return None

        return CatalogImageSerializer(primary, context=self.context).data


class CatalogProductSerializer(CatalogProductListSerializer):
    """Mahsulot sahifasi: rasmlar rang bo'yicha guruhlangan."""

    variants = CatalogVariantSerializer(many=True, read_only=True)
    image_groups = serializers.SerializerMethodField()
    colors = serializers.SerializerMethodField()
    sizes = serializers.SerializerMethodField()

    class Meta(CatalogProductListSerializer.Meta):
        fields = CatalogProductListSerializer.Meta.fields + (
            'description', 'material', 'care', 'image_groups', 'colors',
            'sizes', 'variants',
        )

    def get_image_groups(self, product):
        """Rasmlar rang bo'yicha: rangsizlari birinchi guruhda."""
        groups: dict[int | None, list] = {}

        for image in product.images.all():
            groups.setdefault(image.color_id, []).append(image)

        colors = {color.pk: color for color in self._colors(product)}

        return [
            {
                'color': color_id,
                'color_name': colors[color_id].name if color_id in colors else None,
                'hex_code': colors[color_id].hex_code if color_id in colors else None,
                'images': CatalogImageSerializer(
                    images, many=True, context=self.context
                ).data,
            }
            # `None` birinchi bo'lsin: umumiy rasmlar galereya boshida turadi
            for color_id, images in sorted(groups.items(), key=lambda item: (item[0] or 0,))
        ]

    def _colors(self, product):
        seen = {}

        for variant in product.variants.all():
            if variant.color and variant.color_id not in seen:
                seen[variant.color_id] = variant.color

        for image in product.images.all():
            if image.color and image.color_id not in seen:
                seen[image.color_id] = image.color

        return sorted(seen.values(), key=lambda color: color.name)

    def get_colors(self, product):
        return ColorSerializer(self._colors(product), many=True).data

    def get_sizes(self, product):
        seen = {}

        for variant in product.variants.all():
            if variant.size and variant.size_id not in seen:
                seen[variant.size_id] = variant.size

        ordered = sorted(seen.values(), key=lambda size: (size.position, size.name))

        return SizeSerializer(ordered, many=True).data
