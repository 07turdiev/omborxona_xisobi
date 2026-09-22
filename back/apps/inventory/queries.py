"""Qoldiq bo'yicha so'rov bo'laklari.

Nega alohida modul: «tugayapti» degan qoida katalogda ham, hisobotda
ham, boshqaruv panelida ham bir xil bo'lishi kerak. Qoida esa ikki
joyli qoldiqdan keyin murakkablashdi — u endi **savdo zalidagi**
qoldiqqa qaraydi: omborda yuz dona tursa ham, javon bo'sh bo'lsa
tovarni sotib bo'lmaydi.
"""

from django.db.models import F, OuterRef, Q, QuerySet, Subquery, Sum
from django.db.models.functions import Coalesce

from apps.inventory.models import Location, VariantStock


def shop_stock_subquery(outer: str = 'pk'):
    """Variantning savdo zalidagi qoldig'i — `Variant` so'rovi uchun.

    `outer` — tashqi so'rovdagi variant kaliti. Ichma-ich so'rovlarda
    (masalan `Exists(variants.filter(...))`) u eng yaqin tashqi
    so'rovga, ya'ni variantlar so'roviga ishora qiladi.
    """
    rows = (
        VariantStock.objects.filter(
            variant=OuterRef(outer), location__kind=Location.Kind.SHOP
        )
        .values('variant')
        .annotate(total=Sum('quantity'))
        .values('total')[:1]
    )

    return Coalesce(Subquery(rows), 0)


#: Zalda tugayotgan variant. `with_shop_stock()` dan keyin ishlatiladi.
LOW_STOCK = Q(min_stock__gt=0, shop_stock__lte=F('min_stock'))


def with_shop_stock(queryset: QuerySet) -> QuerySet:
    """Variant so'roviga `shop_stock` maydonini qo'shadi."""
    return queryset.annotate(shop_stock=shop_stock_subquery())


def low_stock_variants(queryset: QuerySet) -> QuerySet:
    """Zalda tugayotgan variantlar."""
    return with_shop_stock(queryset).filter(LOW_STOCK)
