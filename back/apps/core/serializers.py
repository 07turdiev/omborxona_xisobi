from rest_framework import serializers

from apps.core.models import ShopSettings


class ShopSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = ShopSettings
        fields = (
            'shop_name',
            'label_width_mm',
            'label_height_mm',
            'receipt_width_mm',
            'receipt_page_height_mm',
            'max_discount_percent',
            'price_rounding_step',
        )

    def validate_max_discount_percent(self, value):
        if value < 0 or value > 100:
            raise serializers.ValidationError('Chegirma 0 dan 100 % gacha bo‘lishi kerak.')

        return value

    def validate_price_rounding_step(self, value):
        if value < 1:
            raise serializers.ValidationError('Yaxlitlash qadami kamida 1 so‘m bo‘lishi kerak.')

        return value

    def validate_receipt_width_mm(self, value):
        # Keng tarqalgan lentalar: 58 va 80 mm
        if value < 50 or value > 120:
            raise serializers.ValidationError('Chek eni 50 dan 120 mm gacha bo‘lishi kerak.')

        return value

    def validate_receipt_page_height_mm(self, value):
        if value < 40 or value > 300:
            raise serializers.ValidationError(
                'Chek sahifasining bo‘yi 40 dan 300 mm gacha bo‘lishi kerak.'
            )

        return value
