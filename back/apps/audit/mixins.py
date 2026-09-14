"""ViewSet'lar uchun tarixga avtomatik yozish."""

from __future__ import annotations

from apps.audit import services
from apps.audit.models import AuditEvent

Action = AuditEvent.Action


class AuditMixin:
    """Yaratish, tahrirlash va o'chirishni tarixga yozadi.

    ViewSet `audit_object_type` e'lon qiladi (`AuditEvent.OBJECT_TYPES`
    kalitlaridan). Tasdiqlash, jo'natish kabi maxsus amallar `@action`
    ichida `self.audit(...)` bilan alohida yoziladi.

    **Diqqat:** ViewSet `perform_create` / `perform_update` /
    `perform_destroy` ni o'zi e'lon qilsa, ichida `super()` ni chaqirishi
    kerak — aks holda bu mixin chetlab o'tiladi va amal tarixga tushmaydi.
    """

    audit_object_type: str = ''

    def get_audit_object_type(self, instance) -> str:
        return self.audit_object_type

    def get_audit_warehouse(self, instance):
        """Amal qaysi omborga tegishli. Standart — obyektning `warehouse` maydoni."""
        from apps.warehouse.models import Warehouse

        if isinstance(instance, Warehouse):
            return instance

        value = getattr(instance, 'warehouse', None)

        return value if isinstance(value, Warehouse) else None

    def audit(self, action: str, instance=None, **kwargs):
        """Amalni joriy so'rov nomidan yozadi."""
        if 'object_type' not in kwargs:
            kwargs['object_type'] = self.get_audit_object_type(instance)

        if instance is not None and 'warehouse' not in kwargs and 'warehouse_id' not in kwargs:
            kwargs['warehouse'] = self.get_audit_warehouse(instance)

        object_type = kwargs.pop('object_type')

        return services.record(
            action, object_type, request=self.request, obj=instance, **kwargs
        )

    def perform_create(self, serializer):
        super().perform_create(serializer)
        self.audit(Action.CREATE, serializer.instance)

    def perform_update(self, serializer):
        before = services.snapshot(serializer.instance)

        super().perform_update(serializer)

        changes = services.diff(before, services.snapshot(serializer.instance))

        # Hech narsa o'zgarmagan saqlash tarixni shovqin bilan to'ldirmasin
        if changes:
            self.audit(Action.UPDATE, serializer.instance, changes=changes)

    def perform_destroy(self, instance):
        # O'chirilgandan keyin `pk` None bo'ladi va bog'liq obyektlar
        # o'qilmay qoladi — kerakli hamma narsa oldindan olinadi
        object_type = self.get_audit_object_type(instance)
        warehouse = self.get_audit_warehouse(instance)
        object_id = str(instance.pk)
        object_repr = str(instance)
        warehouse_id = warehouse.pk if warehouse else None
        warehouse_name = warehouse.name if warehouse else ''

        super().perform_destroy(instance)

        services.record(
            Action.DELETE,
            object_type,
            request=self.request,
            object_id=object_id,
            object_repr=object_repr,
            warehouse_id=warehouse_id,
            warehouse_name=warehouse_name,
        )
