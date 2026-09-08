"""Kontragent serializerlari."""

from __future__ import annotations

from rest_framework import serializers

from apps.partners.models import Partner


class PartnerSerializer(serializers.ModelSerializer):
    role_display = serializers.CharField(read_only=True)

    class Meta:
        model = Partner
        fields = (
            'id', 'name', 'is_supplier', 'is_customer', 'role_display',
            'inn', 'phone', 'email', 'contact', 'address', 'bank',
            'note', 'is_active', 'created_at',
        )
        read_only_fields = ('id', 'role_display', 'created_at')

    def validate(self, attrs):
        instance = self.instance
        supplier = attrs.get('is_supplier', getattr(instance, 'is_supplier', False))
        customer = attrs.get('is_customer', getattr(instance, 'is_customer', False))

        if not supplier and not customer:
            raise serializers.ValidationError({
                'is_supplier': 'Kamida bittasi belgilanishi kerak: '
                               'yetkazib beruvchi yoki mijoz.'
            })

        return attrs
