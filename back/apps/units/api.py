"""O'lchov birliklari API si."""

from __future__ import annotations

from drf_spectacular.utils import extend_schema
from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.core.access import Perm
from apps.core.permissions import SectionPermission
from apps.units.conversion import convert_to_unit
from apps.units.models import CustomUnit
from apps.units.serializers import BaseUnitSerializer, CustomUnitSerializer


class CustomUnitViewSet(viewsets.ModelViewSet):
    """Tashkilotning o'z o'lchov birliklari.

    Queryset `tenant_id` bo'yicha ochiq filtrlanmaydi — buni PostgreSQL
    RLS bajaradi. Ikki qatlamda filtrlash yolg'on xotirjamlik berardi:
    kimdir ORM filtrini unutsa RLS baribir ushlaydi, lekin ORM filtriga
    ishonib RLS ni o'chirib qo'yish falokat bo'lardi.
    """

    serializer_class = CustomUnitSerializer
    permission_classes = [SectionPermission]
    section_permissions = {'write': {Perm.SETTINGS}}
    queryset = CustomUnit.objects.all()

    @extend_schema(responses=BaseUnitSerializer(many=True))
    @action(detail=False, methods=['get'], url_path='base')
    def base_units(self, request):
        """Tizimning standart birliklari (o'zgartirib bo'lmaydi)."""
        return Response(BaseUnitSerializer.all_definitions())


class ConversionViewSet(viewsets.ViewSet):
    """Qiymatni birlikka keltirish — frontend formalari uchun."""

    permission_classes = [SectionPermission]

    @extend_schema(
        parameters=[],
        responses={200: None},
        description='Masalan: ?value=12 mm&unit=m -> {"result": "0.012"}',
    )
    def list(self, request):
        """Berilgan qiymatni berilgan birlikka keltiradi."""
        from django.core.exceptions import ValidationError

        value = request.query_params.get('value', '')
        unit = request.query_params.get('unit', '')

        try:
            result = convert_to_unit(value, unit or None)
        except ValidationError as exc:
            return Response({'detail': exc.messages[0]}, status=400)

        # Decimal satr sifatida qaytariladi: JSON float ga aylantirsa
        # aniqlik yo'qoladi (loyihaning 6-arxitektura qarori).
        return Response({'value': value, 'unit': unit, 'result': str(result)})
