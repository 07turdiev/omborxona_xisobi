"""Bo'lim ruxsatlari va moliyaviy maydonlarni yashirish.

Ruxsat ikki narsani belgilaydi:

1. **Qaysi bo'limlar ochiq** — sotuv, kirim, qarzdorlar, hisobotlar va
   hokazo. Ruxsat bo'lmasa, bo'lim API'si 403 qaytaradi.
2. **Qaysi moliyaviy ma'lumot ko'rinadi** — kirim narxi va foyda. Kassir
   sotuv qila oladi, lekin tovar qanchaga olinganini va do'kon qancha
   foyda ko'rganini bilmasligi kerak.

Rol — bu standart ruxsatlar to'plami. Tashkilot egasi xodimga alohida
ruxsat qo'shishi yoki olib tashlashi mumkin (`Membership.permissions`).
Ikkita qat'iy qoida bor:

- **Egasi har doim barcha ruxsatlarga ega.** Aks holda tashkilot
  boshqaruvsiz qolishi mumkin edi.
- **Kuzatuvchi hech narsani o'zgartira olmaydi**, qanday ruxsat berilmasin.
  Ruxsat kuzatuvchiga faqat nimani ko'rishini belgilaydi.

Moliyaviy maydonlar **API javobida** tozalanadi, interfeysda yashirilmaydi:
brauzerdagi "yashirin" ustun tarmoq javobida ochiq turadi va uni
istalgan xodim ko'ra oladi.

Ruxsatlar ro'yxati yangi StoreFlow versiyasidagi `role_permissions`
jadvaliga moslashtirilgan (`new/unisergr_storeflow.sql`), bizdagi
qo'shimcha bo'lim — omborlararo ko'chirish.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Any, Iterable


class Perm(StrEnum):
    """Ruxsat kodlari. Qiymatlar bazada va API'da shu ko'rinishda saqlanadi."""

    DASHBOARD = 'dashboard'
    WAREHOUSES = 'warehouses'
    STOCK = 'stock'
    IMPORTS = 'imports'
    SALES = 'sales'
    TRANSFERS = 'transfers'
    DEBTORS = 'debtors'
    PRODUCTS = 'products'
    CATEGORIES = 'categories'
    COUNTERPARTIES = 'counterparties'
    REPORTS = 'reports'
    HISTORY = 'history'
    PRINT_REPORTS = 'print_reports'
    SETTINGS = 'settings'
    USERS = 'users'
    VIEW_PURCHASE_PRICE = 'view_purchase_price'
    VIEW_PROFIT = 'view_profit'


ALL_PERMISSIONS: frozenset[str] = frozenset(Perm)


#: Interfeys uchun katalog: kod, nomi, guruh. Tartib — formadagi tartib.
PERMISSION_CATALOG: list[dict[str, str]] = [
    {'value': Perm.DASHBOARD, 'label': 'Boshqaruv paneli', 'group': 'sections'},
    {'value': Perm.WAREHOUSES, 'label': 'Omborlar', 'group': 'sections'},
    {'value': Perm.STOCK, 'label': 'Qoldiqlar', 'group': 'sections'},
    {'value': Perm.IMPORTS, 'label': 'Kirim', 'group': 'sections'},
    {'value': Perm.SALES, 'label': 'Sotuv', 'group': 'sections'},
    {'value': Perm.TRANSFERS, 'label': 'Ko‘chirish', 'group': 'sections'},
    {'value': Perm.DEBTORS, 'label': 'Qarzdorlar', 'group': 'sections'},
    {'value': Perm.PRODUCTS, 'label': 'Mahsulotlar', 'group': 'sections'},
    {'value': Perm.CATEGORIES, 'label': 'Kategoriyalar', 'group': 'sections'},
    {'value': Perm.COUNTERPARTIES, 'label': 'Kontragentlar', 'group': 'sections'},
    {'value': Perm.REPORTS, 'label': 'Hisobotlar', 'group': 'sections'},
    {'value': Perm.HISTORY, 'label': 'Tarix', 'group': 'sections'},
    {'value': Perm.PRINT_REPORTS, 'label': 'Chop etish va Excel', 'group': 'actions'},
    {'value': Perm.SETTINGS, 'label': 'Sozlamalar', 'group': 'admin'},
    {'value': Perm.USERS, 'label': 'Xodimlar', 'group': 'admin'},
    {'value': Perm.VIEW_PURCHASE_PRICE, 'label': 'Kirim narxini ko‘rish', 'group': 'finance'},
    {'value': Perm.VIEW_PROFIT, 'label': 'Tannarx va foydani ko‘rish', 'group': 'finance'},
]

PERMISSION_GROUPS: dict[str, str] = {
    'sections': 'Bo‘limlar',
    'actions': 'Amallar',
    'finance': 'Moliyaviy ma’lumot',
    'admin': 'Boshqaruv',
}


#: Rollarning standart ruxsatlari.
#:
#: Yangi versiyadagi matritsadan olingan. Ikki farq bor:
#: - `manager` bizda sozlamalar va xodimlarni ham boshqaradi — tizim
#:   birinchi kundan shunday ishlagan va mavjud menejerlarning huquqi
#:   jimgina qisqarib qolmasligi kerak;
#: - `salesperson` yangi versiyadagi `cashier` ga mos.
ROLE_DEFAULTS: dict[str, frozenset[str]] = {
    'owner': ALL_PERMISSIONS,
    'manager': ALL_PERMISSIONS,
    'storekeeper': frozenset({
        Perm.DASHBOARD, Perm.WAREHOUSES, Perm.STOCK, Perm.IMPORTS,
        Perm.TRANSFERS, Perm.PRODUCTS, Perm.CATEGORIES, Perm.COUNTERPARTIES,
        Perm.HISTORY, Perm.PRINT_REPORTS, Perm.VIEW_PURCHASE_PRICE,
    }),
    'salesperson': frozenset({
        Perm.DASHBOARD, Perm.STOCK, Perm.SALES, Perm.DEBTORS,
        Perm.COUNTERPARTIES, Perm.HISTORY, Perm.PRINT_REPORTS,
    }),
    'accountant': frozenset({
        Perm.DASHBOARD, Perm.WAREHOUSES, Perm.STOCK, Perm.IMPORTS, Perm.SALES,
        Perm.DEBTORS, Perm.COUNTERPARTIES, Perm.REPORTS, Perm.HISTORY,
        Perm.PRINT_REPORTS, Perm.VIEW_PURCHASE_PRICE, Perm.VIEW_PROFIT,
    }),
    'viewer': frozenset({
        Perm.DASHBOARD, Perm.WAREHOUSES, Perm.STOCK, Perm.PRODUCTS,
        Perm.CATEGORIES, Perm.COUNTERPARTIES, Perm.REPORTS, Perm.HISTORY,
        Perm.PRINT_REPORTS,
    }),
}


def clean_permissions(values: Iterable[Any]) -> list[str]:
    """Noma'lum kodlarni tashlab, tartiblangan ro'yxat qaytaradi."""
    return sorted({str(value) for value in values} & ALL_PERMISSIONS)


# ---------------------------------------------------------------------
# Moliyaviy maydonlarni yashirish
# ---------------------------------------------------------------------

#: `view_profit` bo'lmasa yashiriladi: tannarx va undan chiqadigan hamma narsa.
PROFIT_KEYS: frozenset[str] = frozenset({
    'cost', 'total_cost', 'line_cost',
    'profit', 'gross_profit', 'net_profit', 'potential_profit',
    'margin_percent',
})

#: `view_purchase_price` bo'lmasa yashiriladi: tovar qanchaga olingani.
#: `cost_value` (qoldiqning tannarx qiymati) va yo'qotishlar summasi ham
#: shu yerda — ular kirim narxidan hisoblanadi va uni ochib beradi.
PURCHASE_PRICE_KEYS: frozenset[str] = frozenset({
    'purchase_price', 'purchase_value', 'purchase_amount',
    'unit_cost', 'avg_unit_cost', 'cost_value', 'loss_amount',
})


def hidden_keys(membership) -> frozenset[str]:
    """A'zo ko'ra olmaydigan maydon kalitlari."""
    hidden: set[str] = set()

    if not membership.has_perm(Perm.VIEW_PROFIT):
        hidden |= PROFIT_KEYS

    if not membership.has_perm(Perm.VIEW_PURCHASE_PRICE):
        hidden |= PURCHASE_PRICE_KEYS

    return frozenset(hidden)


def redact(data: Any, hidden: frozenset[str]) -> Any:
    """Ichma-ich lug'at va ro'yxatlarda yashirin kalitlarni `None` qiladi.

    Kalit o'chirilmaydi, `None` bo'ladi: javob shakli barqaror qoladi va
    interfeys "—" ko'rsatadi. O'chirilsa, frontend `undefined` ni `0` deb
    hisoblab, "foyda: 0" ko'rsatib qo'yishi mumkin edi — bu yolg'on raqam.
    """
    if not hidden:
        return data

    if isinstance(data, dict):
        return {
            key: (None if key in hidden else redact(value, hidden))
            for key, value in data.items()
        }

    if isinstance(data, list):
        return [redact(item, hidden) for item in data]

    return data


def visible_columns(columns, membership) -> list:
    """Eksport ustunlaridan yashirinlarini olib tashlaydi.

    Excel faylida bo'sh ustun qoldirish emas, ustunning o'zini chiqarmaslik
    kerak — aks holda "Foyda" sarlavhali bo'sh ustun xato kabi ko'rinadi.
    """
    hidden = hidden_keys(membership)

    return [column for column in columns if column.key not in hidden]


def visible_pairs(labels, membership) -> list:
    """`(kalit, nom, format)` juftliklaridan yashirinlarini olib tashlaydi."""
    hidden = hidden_keys(membership)

    return [item for item in labels if item[0] not in hidden]


class FinancialRedactionMixin:
    """ViewSet javobidan ruxsatsiz moliyaviy maydonlarni tozalaydi.

    `finalize_response` ga ulanadi, ya'ni ro'yxat, bitta obyekt va
    `@action` javoblari — hammasi bitta joyda tozalanadi. Yangi endpoint
    qo'shganda uni unutib qoldirish imkoni kamroq.

    Excel eksportlari `HttpResponse` qaytaradi va bu yerdan o'tmaydi —
    ular `visible_columns()` bilan alohida tozalanadi.
    """

    def finalize_response(self, request, response, *args, **kwargs):
        response = super().finalize_response(request, response, *args, **kwargs)

        membership = getattr(request, 'membership', None)
        data = getattr(response, 'data', None)

        if membership is not None and data is not None:
            hidden = hidden_keys(membership)

            if hidden:
                response.data = redact(data, hidden)

        return response
