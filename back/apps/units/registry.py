"""Tenant bo'yicha ajratilgan `pint` o'lchov birligi registri.

Bu modulda InvenTree loyihasidan (MIT) olingan kod bor.
Manba: InvenTree 1.6.0 dev — InvenTree/conversion.py:104-117
Litsenziya va to'liq atribut: repo ildizidagi NOTICE faylida.

**InvenTree'dan asosiy farq — va u xavfsizlik farqi.** InvenTree registrni
modul darajasidagi global o'zgaruvchida saqlaydi (`_unit_registry`).
Multi-tenant tizimda bu ma'lumot sizishiga olib keladi: A tashkilot
`qop = 50 * kg` deb ta'riflasa, ta'rif jarayon xotirasida qoladi va B
tashkilotning hisob-kitobiga tushadi. Ikki do'konning sementi turli
og'irlikda bo'lishi mumkin — natijada B ning qoldig'i **jimgina noto'g'ri**
hisoblanadi, hech qanday xato chiqmaydi. Shuning uchun bu yerda registr
tenant bo'yicha keshlanadi.

Kesh ikki qatlamli:

1. **Jarayon xotirasi** — `pint.UnitRegistry` obyekti. U pickle qilinmaydi,
   shuning uchun Redis'ga sig'maydi. LRU bilan cheklangan.
2. **Django cache (Redis)** — tenantning custom birliklaridan hisoblangan
   hash. Boshqa process birlik qo'shsa, hash o'zgaradi va bu process
   registrni qayta quradi.
"""

from __future__ import annotations

import hashlib
import logging
import threading
import uuid
from collections import OrderedDict
from decimal import Decimal

import pint
from django.core.cache import cache

logger = logging.getLogger(__name__)

# `pint` ning o'z log chiqishi shovqinli
logging.getLogger('pint').setLevel(logging.ERROR)

#: Jarayon xotirasida bir vaqtda saqlanadigan registrlar soni.
#: Bitta registr qurilishi ~0.12 s va ~2 MB xotira oladi. Tashkilotlar
#: soni ko'p bo'lsa, bu chegara oshiriladi.
MAX_CACHED_REGISTRIES = 32

#: Hash keshining amal qilish muddati (soniya). Signal invalidatsiya
#: qilgani uchun uzoq bo'lishi mumkin; TTL faqat signal yo'qolgan
#: holatga qarshi himoya.
HASH_CACHE_TTL = 3600


def _hash_cache_key(tenant_id: uuid.UUID) -> str:
    return f'units:registry-hash:{tenant_id}'


# ---------------------------------------------------------------------
# Standart birlik ta'riflari
# ---------------------------------------------------------------------

#: `pint` ga o'lchovsiz sanoq birliklarini tanishtiradi.
#: Manba: InvenTree InvenTree/conversion.py:113-117 (MIT, NOTICE ga qarang).
#: InvenTree'dan temperatura aliaslari va `R = ohm` (elektronika) olinmadi.
COUNTING_UNITS = [
    'piece = 1',
    'each = 1 = ea',
    'dozen = 12 = dz',
    'hundred = 100',
    'thousand = 1000',
]

#: O'zbek tilidagi va savdoga xos birliklar. InvenTree'da yo'q.
#:
#: Diqqat: `qop`, `palet`, `rulon` bu yerda **o'lchovsiz sanoq birliklari**.
#: "1 qop = 50 kg" konversiyasi bu yerda ta'riflanmaydi va ta'riflana
#: olmaydi ham — u mahsulotga bog'liq (sement 50 kg, gips 30 kg).
#: Uni `apps.catalog.ProductUnit` saqlaydi.
LOCAL_UNITS = [
    'dona = 1 = ea',
    'juft = 2 = jft',
    'qop = 1',
    'palet = 1',
    'rulon = 1',
    'quti = 1',
    'to_plam = 1',
    'm2 = meter ** 2',
    'm3 = meter ** 3',
    'pogonmetr = meter = pm',
]

BASE_UNIT_DEFINITIONS = COUNTING_UNITS + LOCAL_UNITS


# ---------------------------------------------------------------------
# Registr keshi
# ---------------------------------------------------------------------

_lock = threading.Lock()
_registries: OrderedDict[uuid.UUID, tuple[str, pint.UnitRegistry]] = OrderedDict()


def compute_units_hash(tenant_id: uuid.UUID) -> str:
    """Tashkilotning custom birliklaridan barqaror hash hisoblaydi."""
    from apps.units.models import CustomUnit

    digest = hashlib.md5(usedforsecurity=False)

    definitions = (
        CustomUnit.objects.filter(tenant_id=tenant_id)
        .order_by('name')
        .values_list('name', 'definition', 'symbol')
    )

    for name, definition, symbol in definitions:
        digest.update(f'{name}={definition}={symbol}\n'.encode())

    return digest.hexdigest()


def get_units_hash(tenant_id: uuid.UUID) -> str:
    """Hashni keshdan oladi, bo'lmasa bazadan hisoblab keshga yozadi."""
    key = _hash_cache_key(tenant_id)
    value = cache.get(key)

    if value is None:
        value = compute_units_hash(tenant_id)
        cache.set(key, value, HASH_CACHE_TTL)

    return value


def invalidate_registry(tenant_id: uuid.UUID) -> None:
    """Tashkilotning registrini bekor qiladi (birlik o'zgarganda chaqiriladi).

    Hash bazadan qayta hisoblanib keshga yoziladi — shunda **boshqa
    process** ham o'zgarishni sezadi va o'z registrini qayta quradi.
    """
    cache.set(_hash_cache_key(tenant_id), compute_units_hash(tenant_id), HASH_CACHE_TTL)

    with _lock:
        _registries.pop(tenant_id, None)


def build_registry(tenant_id: uuid.UUID | None) -> pint.UnitRegistry:
    """Tashkilot uchun yangi `pint` registri quradi.

    `non_int_type=Decimal` — loyihaning 6-arxitektura qarori. InvenTree
    bu yerda standart `float` ishlatadi, natijada `convert_physical_value()`
    oxirida qiymat `float` ga aylanadi (InvenTree/conversion.py:307).
    Bizda butun zanjir `Decimal` da qoladi.
    """
    registry = pint.UnitRegistry(
        autoconvert_offset_to_baseunit=True,
        non_int_type=Decimal,
    )

    for definition in BASE_UNIT_DEFINITIONS:
        registry.define(definition)

    if tenant_id is None:
        return registry

    from apps.units.models import CustomUnit

    for unit in CustomUnit.objects.filter(tenant_id=tenant_id).order_by('name'):
        try:
            registry.define(unit.definition_string)
        except Exception:
            # Bitta buzuq ta'rif butun registrni yiqitmasligi kerak.
            # Ta'rif saqlanishdan oldin tekshiriladi (CustomUnit.clean),
            # shuning uchun bu yerga tushish — kutilmagan holat.
            logger.exception(
                'Custom birlik yuklanmadi: tenant=%s unit=%s', tenant_id, unit.name
            )

    return registry


def get_registry(tenant_id: uuid.UUID | None = None) -> pint.UnitRegistry:
    """Tashkilot uchun registrni qaytaradi (keshdan yoki yangisini qurib).

    `tenant_id` `None` bo'lsa faqat standart birliklardan iborat registr
    qaytadi — u keshlanmaydi va custom birliklarni bilmaydi. Bu holat
    migratsiyalar va boshqaruv buyruqlari uchun.
    """
    if tenant_id is None:
        return build_registry(None)

    current_hash = get_units_hash(tenant_id)

    with _lock:
        cached = _registries.get(tenant_id)

        if cached is not None and cached[0] == current_hash:
            _registries.move_to_end(tenant_id)
            return cached[1]

    # Registr qurish bazaga murojaat qiladi, shuning uchun qulf tashqarisida
    registry = build_registry(tenant_id)

    with _lock:
        _registries[tenant_id] = (current_hash, registry)
        _registries.move_to_end(tenant_id)

        while len(_registries) > MAX_CACHED_REGISTRIES:
            _registries.popitem(last=False)

    return registry


def get_current_registry() -> pint.UnitRegistry:
    """Joriy so'rov kontekstidagi tashkilot registrini qaytaradi."""
    from apps.core.tenancy import get_current_tenant_id

    return get_registry(get_current_tenant_id())
