"""Ombor serializerlari."""

from __future__ import annotations

from rest_framework import serializers

from apps.warehouse.models import Warehouse, WarehouseAccess


class WarehouseSerializer(serializers.ModelSerializer):
    """Ombor — ro'yxat va tahrirlash uchun."""

    goods_type_display = serializers.CharField(
        source='get_goods_type_display', read_only=True
    )
    purpose_display = serializers.CharField(
        source='get_purpose_display', read_only=True
    )
    is_sellable = serializers.BooleanField(read_only=True)

    class Meta:
        model = Warehouse
        fields = (
            'id', 'code', 'name',
            'goods_type', 'goods_type_display',
            'purpose', 'purpose_display', 'is_sellable',
            'manager', 'phone', 'address',
            'area', 'capacity', 'temperature', 'notes',
            'is_active', 'created_at',
        )
        read_only_fields = ('id', 'created_at')

    def validate_code(self, value):
        """Kod bo'sh joysiz va katta harfda saqlanadi."""
        value = (value or '').strip().upper().replace(' ', '-')

        if not value:
            raise serializers.ValidationError('Kod kiritilishi shart.')

        # Tenant ichida unikallik: RLS queryset'ni allaqachon shu
        # tashkilot bilan cheklaydi, shuning uchun qo'shimcha filtr shart emas.
        query = Warehouse.objects.filter(code=value)

        if self.instance is not None:
            query = query.exclude(pk=self.instance.pk)

        if query.exists():
            raise serializers.ValidationError('Bu kod band.')

        return value


class WarehouseAccessSerializer(serializers.ModelSerializer):
    """Foydalanuvchining omborga kirish huquqi."""

    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    warehouse_name = serializers.CharField(source='warehouse.name', read_only=True)
    level_display = serializers.CharField(source='get_level_display', read_only=True)

    class Meta:
        model = WarehouseAccess
        fields = (
            'id', 'warehouse', 'warehouse_name',
            'user', 'user_name', 'level', 'level_display',
        )
        read_only_fields = ('id',)
