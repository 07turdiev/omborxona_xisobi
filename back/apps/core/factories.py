"""Testlar uchun kichik yordamchilar: xodim, mahsulot va kirim."""

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.catalog.models import Category, Color, Product, Size
from apps.catalog.services import sync_variant_matrix
from apps.core.numbering import next_number
from apps.inventory.models import Location
from apps.inventory.services import create_transfer
from apps.purchases.models import Purchase, PurchaseLine
from apps.purchases.services import confirm as confirm_purchase

User = get_user_model()

PASSWORD = 'Kuchli-Parol-2026'


def create_user(username: str, role: str) -> User:
    return User.objects.create_user(username=username, password=PASSWORD, role=role)


def create_admin(username: str = 'admin') -> User:
    return create_user(username, User.Role.ADMIN)


def create_cashier(username: str = 'kassir') -> User:
    return create_user(username, User.Role.CASHIER)


def api_client(user) -> APIClient:
    """JWT bilan tayyor mijoz."""
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f'Bearer {RefreshToken.for_user(user).access_token}')

    return client


def create_product(
    *,
    name: str = 'Ko‘ylak',
    price: str = '250000',
    sizes: tuple[str, ...] = (),
    colors: tuple[str, ...] = (),
    category: Category | None = None,
) -> Product:
    """Mahsulot va uning o'lcham × rang variantlari."""
    category = category or Category.objects.get_or_create(name='Ko‘ylaklar')[0]

    product = Product.objects.create(
        category=category, name=name, sale_price=Decimal(price)
    )

    size_objects = [
        Size.objects.get_or_create(name=size, defaults={'position': index})[0]
        for index, size in enumerate(sizes)
    ]
    color_objects = [
        Color.objects.get_or_create(name=color, defaults={'hex_code': '#808080'})[0]
        for color in colors
    ]

    sync_variant_matrix(
        product,
        [size.pk for size in size_objects],
        [color.pk for color in color_objects],
    )

    return product


@transaction.atomic
def receive_stock(variant, quantity: int, unit_cost, *, user=None, supplier=None, date=None, location=None):
    """Tasdiqlangan kirim orqali tovar kiritadi.

    Kirim doim **omborga** tushadi. Testlarning ko‘pchiligi sotuvni
    sinaydi, shuning uchun standart holatda tovar darhol **zalga**
    ko‘chiriladi — do‘konda javonga chiqarilgandek. Ombordagi
    qoldiq kerak bo‘lsa: location=Location.warehouse().
    """
    date = date or timezone.localdate()

    purchase = Purchase.objects.create(
        number=next_number('KIR', Purchase.objects, date),
        date=date,
        location=Location.warehouse(),
        supplier=supplier,
        created_by=user,
    )

    PurchaseLine.objects.create(
        purchase=purchase,
        variant=variant,
        quantity=quantity,
        unit_cost=Decimal(unit_cost),
    )

    confirmed = confirm_purchase(purchase, user=user)

    target = location or Location.shop()

    if target.kind != Location.Kind.WAREHOUSE:
        create_transfer(
            source=Location.warehouse(),
            target=target,
            lines=[{'variant': variant, 'quantity': quantity}],
            user=user,
            date=date,
        )

    return confirmed
