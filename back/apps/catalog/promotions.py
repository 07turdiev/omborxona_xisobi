"""Aksiyalar: qaysi tovar bugun qancha arzon.

Aksiya narxni o'zgartirmaydi — narx ustidan chegirma bo'lib qo'llanadi
(`Promotion` izohi). Bu yerda bitta savolga javob beriladi: «shu
mahsulotga bugun qaysi aksiya to'g'ri keladi?». Javobni kassa ham,
yorliq ham, sotuvni yozadigan xizmat ham shu yerdan oladi — uchalasi
bir xil hisoblashi shart.
"""

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from django.utils import timezone

from apps.catalog.models import Promotion

HUNDRED = Decimal('100')
CENT = Decimal('0.01')


def today():
    return timezone.localdate()


def running(day=None):
    """Shu kuni amalda bo'lgan aksiyalar."""
    day = day or today()

    return Promotion.objects.filter(is_active=True, starts_on__lte=day, ends_on__gte=day)


def discount_of(base, percent) -> Decimal:
    """Aksiya chegirmasi: kassadagi `percentOf` bilan bir xil yaxlitlanadi."""
    return (Decimal(base) * Decimal(percent) / HUNDRED).quantize(CENT, rounding=ROUND_HALF_UP)


@dataclass(frozen=True)
class Applied:
    """Tovarga tushgan aksiya — API va sotuv uchun yetarli ma'lumot."""

    id: int
    name: str
    percent: Decimal
    ends_on: object

    def as_dict(self, price) -> dict:
        return {
            'id': self.id,
            'name': self.name,
            'percent': str(self.percent),
            'ends_on': self.ends_on.isoformat(),
            'price': str(Decimal(price) - discount_of(price, self.percent)),
        }


class PromotionIndex:
    """Bugungi aksiyalar xotirada: ro'yxatdagi har tovar uchun so'rov yubormaslik.

    Amaldagi aksiyalar odatda bir nechta, tovarlar esa yuzlab — shuning
    uchun aksiyalar bir marta o'qiladi va mos kelishi Python'da topiladi.
    """

    def __init__(self, day=None):
        self._items = []

        for promo in running(day).prefetch_related('products', 'categories'):
            self._items.append((
                Applied(promo.id, promo.name, promo.percent, promo.ends_on),
                {product.id for product in promo.products.all()},
                {category.id for category in promo.categories.all()},
            ))

    def for_product(self, product_id: int, category_id: int) -> Applied | None:
        """Mahsulotga to'g'ri keladigan eng katta aksiya."""
        best = None

        for applied, products, categories in self._items:
            if product_id in products or category_id in categories:
                if best is None or applied.percent > best.percent:
                    best = applied

        return best

    def for_variant(self, variant) -> Applied | None:
        return self.for_product(variant.product_id, variant.product.category_id)


def from_context(context: dict) -> PromotionIndex:
    """Serializer uchun: bitta so'rov ichida indeks bir marta yasaladi."""
    if 'promotions' not in context:
        context['promotions'] = PromotionIndex()

    return context['promotions']
