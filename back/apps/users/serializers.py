"""Foydalanuvchi serializerlari."""

from __future__ import annotations

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

User = get_user_model()


class MembershipBriefSerializer(serializers.Serializer):
    """Foydalanuvchining bitta tashkilotdagi a'zoligi (qisqa ko'rinish)."""

    tenant_id = serializers.UUIDField(source='tenant.id')
    tenant_name = serializers.CharField(source='tenant.name')
    tenant_slug = serializers.CharField(source='tenant.slug')
    role = serializers.CharField()
    role_display = serializers.CharField(source='get_role_display')
    #: Rol ma'lumot kiritishga ruxsat beradimi (kuzatuvchi — yo'q)
    can_write = serializers.BooleanField(read_only=True)

    #: Amaldagi ruxsatlar — interfeys menyu va ustunlarni shunga qarab
    #: ko'rsatadi. Himoya baribir serverda: bu faqat qulaylik uchun.
    permissions = serializers.SerializerMethodField()

    def get_permissions(self, obj) -> list[str]:
        return sorted(obj.effective_permissions)


class UserSerializer(serializers.ModelSerializer):
    """Joriy foydalanuvchi va uning tashkilotlari.

    `current_tenant` — shu so'rov qaysi tashkilot nomidan bajarilgani
    (`TenantMiddleware` aniqlagan). Interfeys sidebar'da shu nomni
    ko'rsatadi va rolga qarab tugmalarni yashiradi.
    """

    full_name = serializers.SerializerMethodField()
    memberships = serializers.SerializerMethodField()
    current_tenant = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            'id', 'username', 'email', 'first_name', 'last_name',
            'full_name', 'phone', 'is_superuser',
            'memberships', 'current_tenant',
        )
        read_only_fields = ('id', 'is_superuser', 'memberships', 'current_tenant')

    def get_full_name(self, obj) -> str:
        return obj.get_full_name() or obj.username

    @extend_schema_field(MembershipBriefSerializer(many=True))
    def get_memberships(self, obj):
        query = obj.memberships.filter(
            is_active=True, tenant__is_active=True
        ).select_related('tenant')

        return MembershipBriefSerializer(query, many=True).data

    @extend_schema_field(MembershipBriefSerializer(allow_null=True))
    def get_current_tenant(self, obj):
        request = self.context.get('request')
        tenant_id = getattr(request, 'tenant_id', None)

        if tenant_id is None:
            return None

        membership = obj.membership_for(tenant_id)

        if membership is None:
            return None

        return MembershipBriefSerializer(membership).data


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])
    password2 = serializers.CharField(write_only=True, label='Parolni tasdiqlash')

    class Meta:
        model = User
        fields = (
            'id', 'username', 'email', 'first_name', 'last_name',
            'phone', 'password', 'password2',
        )

    def validate(self, attrs):
        if attrs['password'] != attrs.pop('password2'):
            raise serializers.ValidationError({'password2': 'Parollar mos kelmadi.'})
        return attrs

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)
