"""Tashkilot sozlamalari va a'zoliklar."""

from __future__ import annotations

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from rest_framework import serializers

from apps.tenants.models import Membership, Tenant

User = get_user_model()


class TenantSettingsSerializer(serializers.ModelSerializer):
    """Tashkilot sozlamalari.

    `slug` o'zgartirilmaydi: u hisobotlarda va tashqi havolalarda
    ishlatiladi, o'zgarsa eski havolalar buziladi.
    """

    business_type_display = serializers.CharField(
        source='get_business_type_display', read_only=True
    )
    member_count = serializers.SerializerMethodField()

    class Meta:
        model = Tenant
        fields = (
            'id', 'name', 'slug', 'business_type', 'business_type_display',
            'base_currency', 'inn', 'phone', 'address',
            'purchase_prefix', 'sale_prefix', 'transfer_prefix',
            'expiry_warning_days', 'is_active', 'member_count',
        )
        read_only_fields = (
            'id', 'slug', 'business_type_display', 'is_active', 'member_count',
        )

    def get_member_count(self, obj) -> int:
        return obj.memberships.filter(is_active=True).count()

    def validate_base_currency(self, value: str) -> str:
        value = (value or '').strip().upper()

        if len(value) != 3:
            raise serializers.ValidationError(
                'Valyuta kodi uch harfdan iborat bo\'lishi kerak (UZS, USD).'
            )

        return value

    def _clean_prefix(self, value: str) -> str:
        value = (value or '').strip().upper()

        if not value:
            raise serializers.ValidationError('Prefiks bo\'sh bo\'lishi mumkin emas.')

        if not value.replace('-', '').isalnum():
            raise serializers.ValidationError(
                'Prefiks faqat harf, raqam va chiziqchadan iborat bo\'lishi kerak.'
            )

        return value

    def validate_purchase_prefix(self, value):
        return self._clean_prefix(value)

    def validate_sale_prefix(self, value):
        return self._clean_prefix(value)

    def validate_transfer_prefix(self, value):
        return self._clean_prefix(value)


class MembershipSerializer(serializers.ModelSerializer):
    """Tashkilot xodimi."""

    username = serializers.CharField(source='user.username', read_only=True)
    full_name = serializers.SerializerMethodField()
    email = serializers.EmailField(source='user.email', read_only=True)
    phone = serializers.CharField(source='user.phone', read_only=True)
    role_display = serializers.CharField(source='get_role_display', read_only=True)
    can_write = serializers.BooleanField(read_only=True)
    is_admin = serializers.BooleanField(read_only=True)
    warehouse_count = serializers.SerializerMethodField()

    class Meta:
        model = Membership
        fields = (
            'id', 'user', 'username', 'full_name', 'email', 'phone',
            'role', 'role_display', 'is_active',
            'can_write', 'is_admin', 'warehouse_count', 'created_at',
        )
        read_only_fields = (
            'id', 'user', 'username', 'full_name', 'email', 'phone',
            'role_display', 'can_write', 'is_admin', 'warehouse_count', 'created_at',
        )

    def get_full_name(self, obj) -> str:
        return obj.user.get_full_name() or obj.user.username

    def get_warehouse_count(self, obj) -> int:
        """Nechta omborga cheklangan. Nol — hammasi ochiq."""
        from apps.warehouse.models import WarehouseAccess

        return WarehouseAccess.objects.filter(user_id=obj.user_id).count()


class MembershipCreateSerializer(serializers.Serializer):
    """Yangi xodim qo'shish.

    Ikki holat:

    - `username` mavjud foydalanuvchiga tegishli bo'lsa — unga shu
      tashkilotda a'zolik beriladi (bir odam bir necha do'konda ishlashi
      mumkin);
    - aks holda yangi foydalanuvchi yaratiladi.

    Parol faqat yangi foydalanuvchi uchun so'raladi — mavjud
    foydalanuvchining parolini boshqa tashkilot admini o'zgartira
    olmasligi kerak.
    """

    username = serializers.CharField(max_length=150)
    password = serializers.CharField(write_only=True, required=False, allow_blank=True)
    first_name = serializers.CharField(required=False, allow_blank=True)
    last_name = serializers.CharField(required=False, allow_blank=True)
    email = serializers.EmailField(required=False, allow_blank=True)
    phone = serializers.CharField(required=False, allow_blank=True)
    role = serializers.ChoiceField(
        choices=Membership.Role.choices, default=Membership.Role.VIEWER
    )

    def validate(self, attrs):
        username = attrs['username'].strip()
        existing = User.objects.filter(username=username).first()

        tenant_id = self.context['request'].tenant_id

        if existing and Membership.objects.filter(
            tenant_id=tenant_id, user=existing
        ).exists():
            raise serializers.ValidationError({
                'username': 'Bu foydalanuvchi allaqachon tashkilot a\'zosi.'
            })

        if existing is None:
            password = (attrs.get('password') or '').strip()

            if not password:
                raise serializers.ValidationError({
                    'password': 'Yangi foydalanuvchi uchun parol kerak.'
                })

            try:
                validate_password(password)
            except DjangoValidationError as exc:
                raise serializers.ValidationError({'password': exc.messages})

        attrs['username'] = username
        attrs['_existing'] = existing

        return attrs

    @transaction.atomic
    def create(self, validated_data):
        existing = validated_data.pop('_existing')
        password = validated_data.pop('password', '')
        role = validated_data.pop('role')
        tenant_id = self.context['request'].tenant_id

        if existing is None:
            user = User.objects.create_user(
                username=validated_data['username'],
                password=password,
                first_name=validated_data.get('first_name', ''),
                last_name=validated_data.get('last_name', ''),
                email=validated_data.get('email', ''),
                phone=validated_data.get('phone', ''),
            )
        else:
            user = existing

        return Membership.objects.create(
            tenant_id=tenant_id, user=user, role=role
        )


class MembershipUpdateSerializer(serializers.ModelSerializer):
    """Rol va faollikni o'zgartirish.

    Foydalanuvchining ismi va paroli bu yerdan o'zgartirilmaydi — u
    boshqa tashkilotlarda ham ishlashi mumkin.
    """

    class Meta:
        model = Membership
        fields = ('role', 'is_active')
