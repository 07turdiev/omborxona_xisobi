from rest_framework import serializers

from apps.core.models import ShopSettings


class ShopSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = ShopSettings
        fields = (
            'shop_name',
            'label_width_mm',
            'label_height_mm',
            'max_discount_percent',
        )

    def validate_max_discount_percent(self, value):
        if value < 0 or value > 100:
            raise serializers.ValidationError('Chegirma 0 dan 100 % gacha bo‘lishi kerak.')

        return value
