"""Valyuta va kurs serializerlari."""

from __future__ import annotations

from rest_framework import serializers

from apps.pricing.models import Currency, ExchangeRate


class CurrencySerializer(serializers.ModelSerializer):
    class Meta:
        model = Currency
        fields = ('id', 'code', 'name', 'symbol', 'is_base', 'is_active')
        read_only_fields = ('id',)

    def validate_code(self, value: str) -> str:
        return (value or '').strip().upper()


class ExchangeRateSerializer(serializers.ModelSerializer):
    currency_code = serializers.CharField(source='currency.code', read_only=True)

    class Meta:
        model = ExchangeRate
        fields = ('id', 'currency', 'currency_code', 'rate', 'valid_from', 'source')
        read_only_fields = ('id', 'currency_code')

    def validate(self, attrs):
        currency = attrs.get('currency') or getattr(self.instance, 'currency', None)

        if currency and currency.is_base:
            raise serializers.ValidationError({
                'currency': 'Asosiy valyuta uchun kurs kerak emas — u har doim 1.'
            })

        return attrs
