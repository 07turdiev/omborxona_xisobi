"""Qarzga sotuv va qarz to'lovlari.

Yangi StoreFlow versiyasidagi "Должники" bo'limi (`new/debts.php`)
bizning arxitekturaga moslashtirilgan. Asosiy farqlar:

1. **Qisman to'lov.** Yangi versiyada "Погасить" butun qoldiqni bir
   martada yopadi. Real savdoda mijoz bugun bir qismini, keyingi hafta
   qolganini to'laydi — shuning uchun har to'lov alohida `DebtPayment`.
2. **Ko'p qatorli sotuv.** Yangi versiyada bitta sotuv = bitta mahsulot,
   ya'ni qarz ham bitta mahsulotga bog'langan. Bizda qarz sotuv hujjatiga
   bog'lanadi, hujjatda esa istalgancha qator.
3. **To'lovlar o'zgartirilmaydi.** Qabul qilingan pul yozuvini keyin
   o'zgartirib bo'lsa, kassadagi kamomadni yashirish mumkin bo'lardi.
   Baza triggeri buni to'xtatadi (migratsiya 0002).
"""

from __future__ import annotations

from decimal import Decimal

from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.core.fields import MoneyField
from apps.core.models import TenantOwnedModel

ZERO = Decimal('0')


class Debt(TenantOwnedModel):
    """Qarzga qilingan sotuv bo'yicha mijozning qarzi."""

    class Status(models.TextChoices):
        ACTIVE = 'active', _('Faol')
        PAID = 'paid', _('To‘langan')
        CANCELLED = 'cancelled', _('Bekor qilingan')

    #: Filtr qiymati — bazada saqlanmaydi. "Muddati o'tgan" holat vaqtga
    #: bog'liq: bugun faol bo'lgan qarz ertaga muddati o'tgan bo'ladi, va
    #: buni har kuni bazada yangilab turish ma'nosiz.
    OVERDUE = 'overdue'

    number = models.CharField(_('Raqami'), max_length=40)

    document = models.OneToOneField(
        'documents.Document',
        on_delete=models.PROTECT,
        related_name='debt',
        verbose_name=_('Sotuv hujjati'),
    )

    warehouse = models.ForeignKey(
        'warehouse.Warehouse',
        on_delete=models.PROTECT,
        related_name='+',
        verbose_name=_('Ombor'),
    )

    partner = models.ForeignKey(
        'partners.Partner',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='debts',
        verbose_name=_('Kontragent'),
    )

    #: Mijoz ma'lumoti **nusxa sifatida**: kontragent keyin o'zgartirilsa
    #: ham, qarz kimga berilgani o'sha kungi holatda qoladi.
    customer_name = models.CharField(_('Mijoz'), max_length=200)
    customer_phone = models.CharField(_('Telefon'), max_length=30, blank=True)
    customer_document = models.CharField(_('Hujjat'), max_length=60, blank=True)

    issued_date = models.DateField(_('Qarz sanasi'))
    due_date = models.DateField(_('To‘lov muddati'))

    #: Ustamasiz summa (chegirma hisobga olingan)
    base_amount = MoneyField(_('Asosiy summa'))
    markup_percent = models.DecimalField(
        _('Ustama, %'), max_digits=6, decimal_places=2, default=0
    )
    #: Jami qarz = hujjat summasi (ustama bilan)
    amount = MoneyField(_('Qarz summasi'))
    paid_amount = MoneyField(_('To‘langan'), default=0)
    currency = models.CharField(_('Valyuta'), max_length=3, default='UZS')

    status = models.CharField(
        _('Holati'), max_length=20, choices=Status.choices, default=Status.ACTIVE
    )
    paid_at = models.DateTimeField(_('To‘liq yopilgan'), null=True, blank=True)

    note = models.TextField(_('Izoh'), blank=True)

    class Meta:
        verbose_name = _('Qarz')
        verbose_name_plural = _('Qarzlar')
        ordering = ['due_date', 'id']
        constraints = [
            models.UniqueConstraint(fields=['tenant', 'number'], name='unique_tenant_debt_number'),
        ]
        indexes = [
            models.Index(fields=['tenant', 'status', 'due_date']),
            models.Index(fields=['tenant', 'partner']),
        ]

    def __str__(self):
        return f'{self.number} — {self.customer_name}'

    @property
    def remaining(self) -> Decimal:
        return self.amount - self.paid_amount

    @property
    def markup_amount(self) -> Decimal:
        return self.amount - self.base_amount

    @property
    def is_overdue(self) -> bool:
        return self.status == self.Status.ACTIVE and self.due_date < timezone.localdate()

    @property
    def overdue_days(self) -> int:
        if not self.is_overdue:
            return 0

        return (timezone.localdate() - self.due_date).days

    @property
    def display_status(self) -> str:
        """Interfeys uchun holat: muddati o'tgan faol qarz alohida."""
        return self.OVERDUE if self.is_overdue else self.status

    @property
    def customer_type(self) -> str:
        """`counterparty` — ro'yxatdagi kontragent, `retail` — chakana mijoz."""
        return 'counterparty' if self.partner_id else 'retail'


class DebtPayment(TenantOwnedModel):
    """Qarz bo'yicha qabul qilingan to'lov. O'zgartirilmaydi va o'chirilmaydi."""

    class Method(models.TextChoices):
        CASH = 'cash', _('Naqd')
        CARD = 'card', _('Karta')
        TRANSFER = 'transfer', _('O‘tkazma')

    debt = models.ForeignKey(
        Debt, on_delete=models.PROTECT, related_name='payments', verbose_name=_('Qarz')
    )

    amount = MoneyField(_('Summa'))

    method = models.CharField(
        _('To‘lov usuli'), max_length=20, choices=Method.choices, default=Method.CASH
    )

    paid_at = models.DateTimeField(_('To‘langan vaqt'), default=timezone.now)

    note = models.CharField(_('Izoh'), max_length=250, blank=True)

    #: Takroriy yuborishdan himoya. Tugma ikki marta bosilsa yoki tarmoq
    #: uzilib so'rov qayta yuborilsa, pul ikki marta yozilmasligi kerak.
    request_key = models.CharField(_('So‘rov kaliti'), max_length=64, blank=True)

    #: `DO_NOTHING` va cheklovsiz: xodim o'chirilsa to'lov yozuvi o'zgarmaydi
    #: (o'zgartirishni trigger baribir taqiqlaydi), ismi esa nusxada qoladi.
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.DO_NOTHING,
        db_constraint=False,
        null=True,
        blank=True,
        related_name='+',
        verbose_name=_('Qabul qildi'),
    )
    created_by_name = models.CharField(_('Qabul qildi'), max_length=150, blank=True)

    class Meta:
        verbose_name = _('Qarz to‘lovi')
        verbose_name_plural = _('Qarz to‘lovlari')
        ordering = ['paid_at', 'id']
        constraints = [
            models.UniqueConstraint(
                fields=['tenant', 'request_key'],
                condition=~models.Q(request_key=''),
                name='unique_debt_payment_request',
            ),
        ]

    def __str__(self):
        return f'{self.debt.number}: {self.amount}'

    def save(self, *args, **kwargs):
        if self.pk is not None:
            raise RuntimeError('Qabul qilingan to‘lovni o‘zgartirib bo‘lmaydi')

        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise RuntimeError('Qabul qilingan to‘lovni o‘chirib bo‘lmaydi')
