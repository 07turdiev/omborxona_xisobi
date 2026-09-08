"""Atributlarni yig'ish, normalizatsiya qilish va tekshirish.

Bu modulda InvenTree loyihasidan (MIT) olingan mantiq bor.
Manba: InvenTree 1.6.0 dev — common/models.py:2949-2985
Litsenziya va to'liq atribut: repo ildizidagi NOTICE faylida.

Ikki asosiy vazifa:

1. **Jonli meros** — mahsulotning kategoriyasi va uning barcha ajdodlari
   bo'ylab atribut ta'riflarini yig'ish. Chuqurroq kategoriya ustun.
2. **Ikki tomonlama saqlash** — har qiymat `{"raw": ..., "num": ...}`
   juftligi sifatida. `raw` foydalanuvchi kiritgani, `num` bazaviy SI
   birlikka keltirilgan son. Busiz `"10 mm"` va `"1 sm"` turli qiymat
   bo'lib qoladi va filtrlash ishlamaydi.

`num` **satr sifatida** saqlanadi: JSON `float` ni `Decimal` ga
aylantirsa aniqlik yo'qoladi (loyihaning 6-arxitektura qarori).
"""

from __future__ import annotations

from decimal import Decimal

from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from apps.catalog.models import AttributeDefinition, Category, Variant
from apps.units.conversion import to_base_units


def definitions_for(category: Category) -> list[AttributeDefinition]:
    """Kategoriya uchun amal qiladigan atribut ta'riflari.

    Kategoriya va uning barcha ajdodlaridagi ta'riflar yig'iladi.
    Bir kalit bir necha darajada uchrasa, **eng chuqur kategoriya
    ustun** bo'ladi — masalan `Qurilish → Sement → Portlandsement`
    zanjirida `Portlandsement` darajasidagi ta'rif yuqoridagini bosadi.

    Bu ustuvorlik qoidasi InvenTree dan olingan
    (`part/models.py:2358`, `order_by('-category__level')`), lekin
    u yerda ta'riflar mahsulot yaratilganda **bir marta nusxalanadi**.
    Bizda esa har o'qishda hisoblanadi, ya'ni kategoriyaga keyin
    qo'shilgan atribut mavjud mahsulotlarda ham darhol paydo bo'ladi.
    """
    if not category or not category.path:
        return []

    # Bitta so'rov: ajdodlar `ltree` ning `@>` operatori bilan topiladi
    query = (
        AttributeDefinition.objects.filter(
            category__path__ancestor_of=category.path
        )
        .select_related('category')
        .order_by('category__path', 'position', 'name')
    )

    by_key: dict[str, AttributeDefinition] = {}

    # `category__path` bo'yicha tartiblangani uchun chuqurroq ta'rif
    # keyinroq keladi va yuzakisini almashtiradi.
    for definition in query:
        by_key[definition.key] = definition

    return sorted(by_key.values(), key=lambda d: (d.position, d.name))


def normalize_value(definition: AttributeDefinition, raw) -> dict:
    """Bitta qiymatni `{"raw": ..., "num": ...}` juftligiga aylantiradi.

    `num` faqat son atributlarda to'ldiriladi; matn va tanlov
    atributlarida `None` bo'ladi — bu xato emas.
    """
    if raw is None:
        return {'raw': None, 'num': None}

    if definition.value_type == AttributeDefinition.ValueType.BOOLEAN:
        value = raw if isinstance(raw, bool) else str(raw).strip().lower() in {
            '1', 'true', 'ha', 'yes', 'on'
        }
        return {'raw': value, 'num': '1' if value else '0'}

    text = str(raw).strip()

    if not text:
        return {'raw': None, 'num': None}

    if definition.value_type != AttributeDefinition.ValueType.NUMBER:
        return {'raw': text, 'num': None}

    magnitude = to_base_units(text, definition.unit or None)

    if magnitude is None:
        raise ValidationError(
            _('"%(value)s" — %(name)s uchun son sifatida tushunilmadi')
            % {'value': text, 'name': definition.name}
        )

    # `Decimal` ni satr sifatida saqlaymiz: JSON float aniqlikni yo'qotadi
    return {'raw': text, 'num': str(magnitude)}


def build_attributes(category: Category, values: dict) -> dict:
    """Foydalanuvchi kiritgan qiymatlardan JSONB tarkibini quradi.

    Ta'rifda yo'q kalitlar **jimgina tashlanadi** — aks holda interfeys
    kategoriya almashtirganda eski atributlarni sudrab yurardi.
    """
    definitions = {d.key: d for d in definitions_for(category)}
    result: dict = {}
    errors: dict = {}

    for definition in definitions.values():
        raw = values.get(definition.key, definition.default_value or None)

        try:
            entry = normalize_value(definition, raw)
        except ValidationError as exc:
            errors[definition.key] = exc.messages
            continue

        if entry['raw'] is None:
            if definition.is_required:
                errors[definition.key] = [
                    _('%(name)s to\'ldirilishi shart') % {'name': definition.name}
                ]
            continue

        if definition.value_type == AttributeDefinition.ValueType.CHOICE:
            if entry['raw'] not in (definition.choices or []):
                errors[definition.key] = [
                    _('"%(value)s" ruxsat etilgan qiymatlar orasida yo\'q')
                    % {'value': entry['raw']}
                ]
                continue

        result[definition.key] = entry

    if errors:
        raise ValidationError(errors)

    return result


def validate_uniqueness(variant: Variant, category: Category, attributes: dict) -> None:
    """Unikallik sharti qo'yilgan atributlarni tekshiradi.

    Manba g'oyasi: InvenTree common/models.py:2949-2985 (MIT).

    Qoida o'sha yerdan: birlik berilgan bo'lsa **normalizatsiyalangan
    son** bo'yicha, aks holda registrga sezgir bo'lmagan matn bo'yicha
    taqqoslanadi. Ya'ni `"1000 mm"` va `"1 m"` dublikat deb topiladi,
    `"Oq"` va `"oq"` ham.

    Farq: InvenTree EAV jadvalida `data_numeric` ustuni bo'yicha so'rov
    qiladi, bizda esa JSONB kaliti bo'yicha.
    """
    definitions = {
        d.key: d
        for d in definitions_for(category)
        if d.uniqueness == AttributeDefinition.Uniqueness.TENANT
    }

    if not definitions:
        return

    errors: dict = {}

    for key, definition in definitions.items():
        entry = attributes.get(key)

        if not entry or entry.get('raw') is None:
            continue

        query = Variant.objects.all()

        if variant.pk:
            query = query.exclude(pk=variant.pk)

        if entry.get('num') is not None:
            # Sonli taqqoslash: turli birlikda yozilgan bir xil qiymat
            # ham dublikat sifatida topilishi kerak
            target = Decimal(entry['num'])
            duplicate = any(
                other.get(key, {}).get('num') is not None
                and Decimal(other[key]['num']) == target
                for other in query.values_list('attributes', flat=True)
            )
        else:
            target_text = str(entry['raw']).casefold()
            duplicate = any(
                str((other.get(key) or {}).get('raw', '')).casefold() == target_text
                for other in query.values_list('attributes', flat=True)
            )

        if duplicate:
            errors[key] = [
                _('%(name)s qiymati takrorlanmasligi kerak') % {'name': definition.name}
            ]

    if errors:
        raise ValidationError(errors)
