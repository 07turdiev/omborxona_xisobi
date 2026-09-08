"""Kontragent API si."""

from __future__ import annotations

from django.db.models import Q
from rest_framework import viewsets

from apps.core.permissions import IsTenantMemberOrReadOnly
from apps.partners.models import Partner
from apps.partners.serializers import PartnerSerializer


class PartnerViewSet(viewsets.ModelViewSet):
    serializer_class = PartnerSerializer
    permission_classes = [IsTenantMemberOrReadOnly]

    def get_queryset(self):
        queryset = Partner.objects.all()
        params = self.request.query_params

        if search := params.get('search', '').strip():
            queryset = queryset.filter(
                Q(name__icontains=search)
                | Q(inn__icontains=search)
                | Q(phone__icontains=search)
                | Q(contact__icontains=search)
            )

        role = params.get('role', '').strip()

        if role == 'supplier':
            queryset = queryset.filter(is_supplier=True)
        elif role == 'customer':
            queryset = queryset.filter(is_customer=True)

        if (active := params.get('is_active', '').strip()) in {'true', 'false'}:
            queryset = queryset.filter(is_active=active == 'true')

        return queryset
