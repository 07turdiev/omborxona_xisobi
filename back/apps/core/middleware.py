"""Har so'rov uchun tenant kontekstini o'rnatuvchi middleware."""

from __future__ import annotations

import uuid

from django.db import transaction
from django.utils.functional import SimpleLazyObject

from apps.core.tenancy import (
    apply_tenant_to_connection,
    reset_current_tenant_id,
    set_current_tenant_id,
)

# So'rovda tenantni ochiq ko'rsatish uchun sarlavha. Foydalanuvchi bir
# nechta tashkilotga a'zo bo'lganda kerak; ko'rsatilmasa birinchi faol
# a'zolik olinadi.
TENANT_HEADER = 'HTTP_X_TENANT_ID'


class TenantMiddleware:
    """Foydalanuvchining tenantini aniqlab, so'rovni shu kontekstda bajaradi.

    So'rov `transaction.atomic()` ichida bajariladi, chunki tenant bazaga
    `SET LOCAL` orqali beriladi va u tranzaksiya bilan chegaralangan.
    Bu bir vaqtda ikki foydani beradi:

    - ulanish pulida qayta ishlatilgan ulanishga begona tenant qiymati
      yopishib qolmaydi;
    - bitta so'rov ichidagi barcha yozuvlar atomar bo'ladi.

    **Fail-closed:** tenant aniqlanmasa (autentifikatsiyasiz so'rov,
    a'zoligi yo'q foydalanuvchi, noto'g'ri `X-Tenant-Id`) kontekst `None`
    bo'lib qoladi va RLS hech qanday qator qaytarmaydi. Bu 403 tekshiruvidan
    kuchliroq himoya, chunki u endpointni yozgan dasturchining
    e'tiboriga bog'liq emas.

    **Nega JWT shu yerda dekodlanadi:** SimpleJWT autentifikatsiyasi odatda
    DRF view ichida (`perform_authentication`) ishlaydi, ya'ni middleware
    bosqichida `request.user` anonim bo'ladi. Bizga esa tenant **birinchi
    SQL so'rovidan oldin** kerak, aks holda RLS bo'sh natija qaytaradi.
    Shuning uchun token shu yerda o'qiladi. DRF keyin uni yana bir marta
    tekshiradi — bu takroriy ish, lekin u yagona ishonch manbai bo'lib
    qoladi (bu yerdagi natija view'ga o'tkazilmaydi).
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        tenant_id = self._resolve_tenant_id(request)

        request.tenant_id = tenant_id
        token = set_current_tenant_id(tenant_id)

        try:
            with transaction.atomic():
                apply_tenant_to_connection(tenant_id)
                return self.get_response(request)
        finally:
            reset_current_tenant_id(token)

    # -- ichki yordamchilar --------------------------------------------

    def _resolve_user(self, request):
        """So'rov egasini aniqlaydi: avval JWT, keyin sessiya."""
        from rest_framework_simplejwt.authentication import JWTAuthentication
        from rest_framework_simplejwt.exceptions import (
            AuthenticationFailed,
            InvalidToken,
        )

        try:
            result = JWTAuthentication().authenticate(request)
        except (AuthenticationFailed, InvalidToken):
            # Yaroqsiz token — foydalanuvchi aniqlanmadi. Xatoni bu yerda
            # ko'tarmaymiz: javob kodini DRF bersin, biz faqat tenantni
            # `None` qoldiramiz.
            return None

        if result is not None:
            return result[0]

        # JWT yo'q — sessiya autentifikatsiyasi (admin paneli) bo'lishi mumkin.
        user = getattr(request, 'user', None)

        if isinstance(user, SimpleLazyObject):
            user = user._wrapped if user._wrapped is not None else user

        if user is not None and getattr(user, 'is_authenticated', False):
            return user

        return None

    def _resolve_tenant_id(self, request) -> uuid.UUID | None:
        """So'rovdan tenant ID sini aniqlaydi.

        Tartib:
        1. `X-Tenant-Id` sarlavhasi — foydalanuvchi shu tashkilotga faol
           a'zo bo'lsagina qabul qilinadi.
        2. Aks holda foydalanuvchining eng eski faol a'zoligi.

        `Membership` va `Tenant` jadvallarida RLS yo'q (ular tenant
        konteksti hali o'rnatilmagan paytda o'qiladi), shuning uchun bu
        so'rov ishlaydi. Ularning izolyatsiyasi `user` bo'yicha filtrga
        tayanadi — apps/tenants/models.py dagi izohga qarang.
        """
        user = self._resolve_user(request)

        if user is None:
            return None

        from apps.tenants.models import Membership

        memberships = Membership.objects.filter(
            user=user, is_active=True, tenant__is_active=True
        )

        requested = request.META.get(TENANT_HEADER)

        if requested:
            try:
                requested_id = uuid.UUID(requested)
            except ValueError:
                return None

            # So'ralgan tashkilotga a'zolik yo'q bo'lsa hech narsa bermaymiz.
            if memberships.filter(tenant_id=requested_id).exists():
                return requested_id

            return None

        return (
            memberships.order_by('created_at')
            .values_list('tenant_id', flat=True)
            .first()
        )
