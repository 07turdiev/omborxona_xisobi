"""O'lchov birliklari uchun serializerlar."""

from __future__ import annotations

from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from apps.units.models import CustomUnit
from apps.units.registry import BASE_UNIT_DEFINITIONS


class CustomUnitSerializer(serializers.ModelSerializer):
    """Tashkilotning o'z o'lchov birligi."""

    definition_string = serializers.CharField(read_only=True)

    class Meta:
        model = CustomUnit
        fields = (
            'id', 'name', 'symbol', 'definition',
            'definition_string', 'description', 'created_at',
        )
        read_only_fields = ('id', 'definition_string', 'created_at')

    def validate(self, attrs):
        """Ta'rifni `pint` bilan tekshiradi.

        Model `clean()` ni chaqiramiz, chunki tekshiruv `pint` registriga
        murojaat qiladi va uni serializer ichida takrorlash ma'nosiz.
        """
        instance = CustomUnit(**{**self._current_values(), **attrs})
        instance.tenant_id = self.context['request'].tenant_id

        try:
            instance.clean()
        except DjangoValidationError as exc:
            raise serializers.ValidationError(
                exc.message_dict if hasattr(exc, 'message_dict') else exc.messages
            )

        return attrs

    def _current_values(self) -> dict:
        """Tahrirlashda o'zgartirilmagan maydonlar mavjud yozuvdan olinadi."""
        if self.instance is None:
            return {}

        return {
            field: getattr(self.instance, field)
            for field in ('name', 'symbol', 'definition')
        }


class BaseUnitSerializer(serializers.Serializer):
    """Tizimning standart birliklari — faqat o'qish uchun."""

    definition = serializers.CharField()

    @staticmethod
    def all_definitions() -> list[dict]:
        return [{'definition': item} for item in BASE_UNIT_DEFINITIONS]
