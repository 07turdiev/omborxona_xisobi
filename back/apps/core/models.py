"""Barcha ilovalar uchun umumiy abstrakt modellar."""

from __future__ import annotations

from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.tenancy import get_current_tenant_id


class TimeStampedModel(models.Model):
    """Yaratilgan va o'zgartirilgan vaqtni saqlaydigan abstrakt model."""

    created_at = models.DateTimeField(_('Yaratilgan'), auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(_('O\'zgartirilgan'), auto_now=True)

    class Meta:
        abstract = True


class TenantOwnedQuerySet(models.QuerySet):
    """Tenantga tegishli modellar uchun queryset.

    Filtrlashning asosiy himoyasi — PostgreSQL RLS, ya'ni bu yerda
    `tenant_id` bo'yicha filtr **takrorlanmaydi**. Sabab: ikki qatlamda
    filtrlash yolg'on xotirjamlik beradi — kimdir ORM filtrini unutsa,
    RLS baribir ushlaydi; lekin ORM filtriga ishonib RLS ni o'chirib
    qo'yish falokat bo'ladi. Bitta himoya bo'lgani ma'qul, va u
    bazada bo'lsin.

    Bu yerda faqat qulaylik metodlari bor.
    """

    def for_current_tenant(self):
        """Aniqlik uchun joriy tenant bo'yicha ochiq filtr.

        RLS allaqachon filtrlagani uchun bu ortiqcha, lekin testlarda va
        RLS o'chirilgan holatda (masalan boshqaruv buyruqlarida) foydali.
        """
        tenant_id = get_current_tenant_id()

        if tenant_id is None:
            return self.none()

        return self.filter(tenant_id=tenant_id)


class TenantOwnedModel(TimeStampedModel):
    """Tenantga tegishli har qanday model uchun asos.

    `tenant_id` ustuni RLS policy'si uchun majburiy. Modelni shu klassdan
    meros qilib olish `apps.core.checks` tekshiruvini ham yoqadi: agar
    jadval uchun RLS policy migratsiyasi yozilmagan bo'lsa,
    `manage.py check` xato beradi.
    """

    tenant = models.ForeignKey(
        'tenants.Tenant',
        on_delete=models.CASCADE,
        related_name='+',
        verbose_name=_('Tashkilot'),
        db_index=True,
    )

    objects = TenantOwnedQuerySet.as_manager()

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        """Yangi yozuvda tenant ko'rsatilmagan bo'lsa, kontekstdan oladi."""
        if self.tenant_id is None:
            self.tenant_id = get_current_tenant_id()

        super().save(*args, **kwargs)
