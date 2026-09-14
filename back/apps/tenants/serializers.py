"""Tashkilot sozlamalari va a'zoliklar."""

from __future__ import annotations

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from rest_framework import serializers

from apps.core.access import ALL_PERMISSIONS, ROLE_DEFAULTS, clean_permissions
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
            'purchase_prefix', 'sale_prefix', 'transfer_prefix', 'debt_prefix',
            'debt_default_days', 'credit_markup_default',
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

    def validate_debt_prefix(self, value):
        return self._clean_prefix(value)

    def validate_debt_default_days(self, value):
        if value < 1:
            raise serializers.ValidationError('Muddat kamida 1 kun bo‘lishi kerak.')

        return value

    def validate_credit_markup_default(self, value):
        if value < 0 or value > 1000:
            raise serializers.ValidationError('Ustama 0 dan 1000 % gacha bo‘lishi kerak.')

        return value


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

    #: Amaldagi ruxsatlar (rol standarti yoki alohida sozlangan ro'yxat)
    permissions = serializers.SerializerMethodField()
    uses_role_defaults = serializers.BooleanField(read_only=True)

    class Meta:
        model = Membership
        fields = (
            'id', 'user', 'username', 'full_name', 'email', 'phone',
            'role', 'role_display', 'is_active',
            'can_write', 'is_admin', 'permissions', 'uses_role_defaults',
            'warehouse_count', 'created_at',
        )
        read_only_fields = (
            'id', 'user', 'username', 'full_name', 'email', 'phone',
            'role_display', 'can_write', 'is_admin', 'permissions',
            'uses_role_defaults', 'warehouse_count', 'created_at',
        )

    def get_permissions(self, obj) -> list[str]:
        return sorted(obj.effective_permissions)

    def get_full_name(self, obj) -> str:
        return obj.user.get_full_name() or obj.user.username

    def get_warehouse_count(self, obj) -> int:
        """Nechta omborga cheklangan. Nol — hammasi ochiq."""
        from apps.warehouse.models import WarehouseAccess

        return WarehouseAccess.objects.filter(user_id=obj.user_id).count()


def normalize_permissions(value, role: str):
    """Ruxsatlar ro'yxatini tekshiradi.

    Noma'lum kod — xato (jimgina tashlab yuborilsa, admin "berdim" deb
    o'ylab qolardi). Ro'yxat rolning standartiga teng bo'lsa `None`
    qaytadi: shunda keyin rol o'zgarganda ruxsatlar ham u bilan birga
    o'zgaradi.
    """
    if value is None:
        return None

    unknown = {str(item) for item in value} - ALL_PERMISSIONS

    if unknown:
        raise serializers.ValidationError({
            'permissions': 'Noma’lum ruxsat: ' + ', '.join(sorted(unknown))
        })

    cleaned = clean_permissions(value)

    if frozenset(cleaned) == ROLE_DEFAULTS.get(role, frozenset()):
        return None

    return cleaned


def check_access_change(actor: Membership, *, target, role: str, permissions) -> None:
    """Xodim huquqini o'zgartirish qoidalari.

    1. **O'z huquqini hech kim o'zgartira olmaydi** — na rol, na ruxsat,
       na faollik. Aks holda menejer o'zini ega qilib qo'yardi, yagona ega
       esa o'zini adashib kuzatuvchiga tushirib, tashkilotni egasiz
       qoldirardi.
    2. **Egasini faqat ega** o'zgartiradi va ega rolini faqat ega beradi.
    3. **O'zida yo'q ruxsatni bera olmaydi.** "Xodimlar" ruxsati bor, lekin
       foydani ko'rmaydigan kishi boshqaga foydani ko'rish huquqini bera
       olmasligi kerak — aks holda u o'z yordamchisi orqali ko'rardi.
    """
    owner = Membership.Role.OWNER

    if target is not None and target.user_id == actor.user_id:
        raise serializers.ValidationError({
            'detail': 'O‘z rolingiz, ruxsatlaringiz va holatingizni o‘zgartira olmaysiz.'
        })

    if actor.role == owner:
        return

    if target is not None and target.role == owner:
        raise serializers.ValidationError({
            'detail': 'Tashkilot egasini faqat egasi o‘zgartira oladi.'
        })

    if role == owner:
        raise serializers.ValidationError({
            'role': 'Ega rolini faqat tashkilot egasi bera oladi.'
        })

    resulting = (
        frozenset(permissions)
        if permissions is not None
        else ROLE_DEFAULTS.get(role, frozenset())
    )

    extra = resulting - actor.effective_permissions

    if extra:
        raise serializers.ValidationError({
            'permissions': 'O‘zingizda yo‘q ruxsatni bera olmaysiz: '
            + ', '.join(sorted(extra))
        })


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

    #: Berilmasa yoki `null` — rolning standart ruxsatlari
    permissions = serializers.ListField(
        child=serializers.CharField(), required=False, allow_null=True
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

        permissions = normalize_permissions(attrs.get('permissions'), attrs['role'])
        check_access_change(
            self.context['request'].membership,
            target=None, role=attrs['role'], permissions=permissions,
        )
        attrs['permissions'] = permissions

        attrs['username'] = username
        attrs['_existing'] = existing

        return attrs

    @transaction.atomic
    def create(self, validated_data):
        existing = validated_data.pop('_existing')
        password = validated_data.pop('password', '')
        role = validated_data.pop('role')
        permissions = validated_data.pop('permissions', None)
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
            tenant_id=tenant_id, user=user, role=role, permissions=permissions
        )


class MembershipUpdateSerializer(serializers.ModelSerializer):
    """Rol, faollik va ruxsatlarni o'zgartirish.

    Foydalanuvchining ismi va paroli bu yerdan o'zgartirilmaydi — u
    boshqa tashkilotlarda ham ishlashi mumkin.

    `permissions: null` yuborilsa — rolning standart ruxsatlariga qaytadi.
    """

    permissions = serializers.ListField(
        child=serializers.CharField(), required=False, allow_null=True
    )

    class Meta:
        model = Membership
        fields = ('role', 'is_active', 'permissions')

    def validate(self, attrs):
        target = self.instance
        role = attrs.get('role', target.role)

        if 'permissions' in attrs:
            permissions = normalize_permissions(attrs['permissions'], role)
        else:
            permissions = target.permissions

        check_access_change(
            self.context['request'].membership,
            target=target, role=role, permissions=permissions,
        )

        if 'permissions' in attrs:
            attrs['permissions'] = permissions

        return attrs
