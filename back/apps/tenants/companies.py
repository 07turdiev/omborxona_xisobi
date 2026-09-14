"""Kompaniyalar — tizim superadmini tashkilotlarni ochadi va boshqaradi.

Yangi StoreFlow versiyasidagi "Компании" bo'limi (`new/directory.php`).
Bizda kompaniya — bu `Tenant`: har biri PostgreSQL RLS bilan boshqalardan
ajratilgan. Shuning uchun:

- tashkilotni **o'chirish yo'q**, faqat faolsizlantirish. Qoldiq, tarix va
  to'lov jurnallari o'chirishni baza darajasida taqiqlaydi — va to'g'ri
  qiladi: yopilgan do'konning hisob-kitobi ham saqlanishi kerak;
- omborlar soni har tashkilot **o'z konteksti ichida** sanaladi — RLS
  boshqa yo'l bilan uni ko'rsatmaydi;
- superadminning amallari o'sha tashkilotning **o'z tarixiga** yoziladi:
  do'kon egasi o'z kompaniyasi rekvizitlarini kim o'zgartirganini ko'radi.
"""

from __future__ import annotations

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.db.models import Q
from django.utils.text import slugify
from rest_framework import mixins, serializers, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.audit import services as audit
from apps.audit.models import AuditEvent
from apps.core.permissions import IsSuperuser
from apps.core.tenancy import tenant_context
from apps.tenants.models import Membership, Tenant
from apps.tenants.serializers import TenantSettingsSerializer

User = get_user_model()

#: Asosiy valyuta nomlari — yangi tashkilotda valyuta yozuvi yaratiladi
CURRENCY_NAMES = {'UZS': 'O‘zbek so‘mi', 'USD': 'AQSh dollari', 'EUR': 'Yevro', 'RUB': 'Rossiya rubli'}


def warehouse_count(tenant: Tenant) -> int:
    """Tashkilot omborlari soni — o'z RLS konteksti ichida."""
    from apps.warehouse.models import Warehouse

    with tenant_context(tenant.id):
        return Warehouse.objects.count()


class CompanySerializer(TenantSettingsSerializer):
    """Kompaniya: rekvizitlar, holat va (yaratishda) egasi."""

    warehouse_count = serializers.SerializerMethodField()
    owner = serializers.SerializerMethodField()

    #: Faqat yaratishda. Login mavjud bo'lsa — o'sha foydalanuvchi ega bo'ladi
    owner_username = serializers.CharField(write_only=True, required=False)
    owner_password = serializers.CharField(write_only=True, required=False, allow_blank=True)
    owner_first_name = serializers.CharField(write_only=True, required=False, allow_blank=True)
    owner_last_name = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta(TenantSettingsSerializer.Meta):
        fields = TenantSettingsSerializer.Meta.fields + (
            'warehouse_count', 'owner', 'created_at',
            'owner_username', 'owner_password', 'owner_first_name', 'owner_last_name',
        )
        read_only_fields = (
            'id', 'business_type_display', 'legal_form_display',
            'member_count', 'warehouse_count', 'owner', 'created_at',
        )
        extra_kwargs = {'slug': {'required': False}}

    def get_warehouse_count(self, obj) -> int:
        return warehouse_count(obj)

    def get_owner(self, obj) -> dict | None:
        membership = (
            obj.memberships.filter(role=Membership.Role.OWNER, is_active=True)
            .select_related('user')
            .order_by('created_at')
            .first()
        )

        if membership is None:
            return None

        return {
            'username': membership.user.username,
            'full_name': membership.user.get_full_name() or membership.user.username,
        }

    def validate_slug(self, value):
        value = slugify(value or '')

        duplicate = Tenant.objects.filter(slug=value)

        if self.instance is not None:
            duplicate = duplicate.exclude(pk=self.instance.pk)

        if value and duplicate.exists():
            raise serializers.ValidationError('Bu qisqa nom band.')

        return value

    def validate(self, attrs):
        attrs = super().validate(attrs)

        if self.instance is not None:
            # Egasi yaratishda beriladi; keyin — xodimlar bo'limidan
            for field in ('owner_username', 'owner_password', 'owner_first_name', 'owner_last_name'):
                attrs.pop(field, None)

            return attrs

        username = (attrs.get('owner_username') or '').strip()

        if not username:
            raise serializers.ValidationError({'owner_username': 'Kompaniya egasining loginini kiriting.'})

        if not User.objects.filter(username=username).exists():
            password = attrs.get('owner_password') or ''

            if not password:
                raise serializers.ValidationError({
                    'owner_password': 'Yangi foydalanuvchi uchun parol kerak.'
                })

            try:
                validate_password(password)
            except DjangoValidationError as exc:
                raise serializers.ValidationError({'owner_password': exc.messages})

        if not attrs.get('slug'):
            base = slugify(attrs.get('code') or attrs.get('name') or '') or 'kompaniya'
            slug, counter = base, 2

            while Tenant.objects.filter(slug=slug).exists():
                slug = f'{base}-{counter}'
                counter += 1

            attrs['slug'] = slug

        attrs['owner_username'] = username

        return attrs

    @transaction.atomic
    def create(self, validated_data):
        from apps.pricing.models import Currency

        username = validated_data.pop('owner_username')
        password = validated_data.pop('owner_password', '')
        first_name = validated_data.pop('owner_first_name', '')
        last_name = validated_data.pop('owner_last_name', '')

        tenant = Tenant.objects.create(**validated_data)

        user = User.objects.filter(username=username).first()

        if user is None:
            user = User.objects.create_user(
                username=username, password=password,
                first_name=first_name, last_name=last_name,
            )

        Membership.objects.create(tenant=tenant, user=user, role=Membership.Role.OWNER)

        # Asosiy valyuta yozuvi: kurslar va narxlar shunga tayanadi
        with tenant_context(tenant.id):
            Currency.objects.get_or_create(
                tenant=tenant,
                code=tenant.base_currency,
                defaults={
                    'name': CURRENCY_NAMES.get(tenant.base_currency, tenant.base_currency),
                    'is_base': True,
                },
            )

        return tenant


class CompanyViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = CompanySerializer
    permission_classes = [IsSuperuser]
    queryset = Tenant.objects.none()

    def get_queryset(self):
        # `Tenant` jadvalida RLS yo'q — superadmin hammasini ko'radi
        queryset = Tenant.objects.all().order_by('name')
        params = self.request.query_params

        if search := params.get('search', '').strip():
            queryset = queryset.filter(
                Q(name__icontains=search)
                | Q(short_name__icontains=search)
                | Q(code__icontains=search)
                | Q(inn__icontains=search)
                | Q(slug__icontains=search)
            )

        if (active := params.get('is_active', '').strip()) in {'true', 'false'}:
            queryset = queryset.filter(is_active=active == 'true')

        return queryset

    def _record(self, action_name: str, tenant: Tenant, **kwargs) -> None:
        """Amalni o'sha tashkilotning o'z tarixiga yozadi."""
        with tenant_context(tenant.id):
            audit.record(
                action_name, 'company', request=self.request, obj=tenant, **kwargs
            )

    def perform_create(self, serializer):
        tenant = serializer.save()
        self._record(AuditEvent.Action.CREATE, tenant)

    def perform_update(self, serializer):
        before = audit.snapshot(serializer.instance)
        tenant = serializer.save()
        changes = audit.diff(before, audit.snapshot(tenant))

        if changes:
            self._record(AuditEvent.Action.UPDATE, tenant, changes=changes)

    @action(detail=False, methods=['get'])
    def summary(self, request):
        """To'rtta ko'rsatkich: kompaniyalar, faollari, omborlar, foydalanuvchilar."""
        tenants = list(Tenant.objects.all())

        return Response({
            'total': len(tenants),
            'active': sum(1 for tenant in tenants if tenant.is_active),
            'warehouses': sum(warehouse_count(tenant) for tenant in tenants),
            'users': Membership.objects.filter(is_active=True)
            .values('user')
            .distinct()
            .count(),
        })
