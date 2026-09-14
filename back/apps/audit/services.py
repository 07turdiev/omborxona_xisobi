"""Tarixga yozish."""

from __future__ import annotations

import datetime
import uuid
from decimal import Decimal
from typing import Any

from apps.audit.models import AuditEvent

#: Tahrir farqida ko'rsatilmaydigan maydonlar — texnik yoki har safar o'zgaradi
SKIP_FIELDS = frozenset({'id', 'tenant', 'created_at', 'updated_at'})


def _plain(value: Any) -> Any:
    """JSON'ga yoziladigan ko'rinish. Pul `str` bo'lib qoladi, `float` emas."""
    if value is None or isinstance(value, (bool, int, str)):
        return value

    if isinstance(value, Decimal):
        return str(value)

    if isinstance(value, (datetime.date, datetime.datetime)):
        return value.isoformat()

    if isinstance(value, uuid.UUID):
        return str(value)

    if isinstance(value, (list, dict)):
        return value

    return str(value)


def snapshot(instance) -> dict[str, Any]:
    """Obyektning oddiy maydonlari. Tashqi kalit — ID sifatida."""
    return {
        field.name: _plain(field.value_from_object(instance))
        for field in instance._meta.concrete_fields
        if field.name not in SKIP_FIELDS
    }


def diff(before: dict[str, Any], after: dict[str, Any]) -> dict[str, list]:
    """Faqat o'zgargan maydonlar: `{"maydon": [eski, yangi]}`."""
    return {
        key: [before.get(key), value]
        for key, value in after.items()
        if before.get(key) != value
    }


def record(
    action: str,
    object_type: str,
    *,
    request=None,
    user=None,
    obj=None,
    object_id: str | None = None,
    object_repr: str | None = None,
    warehouse=None,
    warehouse_id: int | None = None,
    warehouse_name: str = '',
    details: str = '',
    changes: dict | None = None,
) -> AuditEvent:
    """Bitta amalni tarixga yozadi.

    Chaqiruvchining tranzaksiyasi ichida yoziladi: agar amalning o'zi
    bekor bo'lsa (xato, rollback), tarix yozuvi ham qolmaydi — bo'lmagan
    amal tarixda turmasligi kerak. Teskarisi ham to'g'ri: tarixga yozib
    bo'lmasa, amal ham bajarilmaydi.

    Tashkilot joriy kontekstdan olinadi (`TenantOwnedModel.save`).
    """
    if user is None and request is not None:
        user = getattr(request, 'user', None)

    if user is not None and not getattr(user, 'is_authenticated', False):
        user = None

    if obj is not None:
        if object_id is None:
            object_id = str(obj.pk) if obj.pk is not None else ''

        if object_repr is None:
            object_repr = str(obj)

    if warehouse is not None:
        warehouse_id = warehouse.pk
        warehouse_name = warehouse.name

    return AuditEvent.objects.create(
        action=action,
        object_type=object_type,
        object_id=(object_id or '')[:64],
        object_repr=(object_repr or '')[:250],
        warehouse_id=warehouse_id,
        warehouse_name=(warehouse_name or '')[:150],
        user=user,
        user_name=((user.get_full_name() or user.username) if user else '')[:150],
        details=(details or '')[:500],
        changes=changes or {},
    )
