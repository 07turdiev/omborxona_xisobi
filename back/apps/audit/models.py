"""Amallar tarixi — kim, qachon, nimani qildi.

Qoldiq jurnali (`stock_movements`) faqat tovar harakatini yozadi. Bu
jurnal esa **odamlarning amallarini** yozadi: sotuvni kim tahrirladi,
kirimni kim bekor qildi, mahsulot narxini kim o'zgartirdi, xodimga kim
ruxsat berdi. Do'kon egasi uchun eng ko'p kerak bo'ladigan savol —
"bu qanday bo'lib qoldi?" — shu yerda javob topadi.

Yozuvlar **o'zgartirilmaydi va o'chirilmaydi** (baza triggeri bilan,
migratsiya 0002). O'zgartirib bo'ladigan jurnal jurnal emas: xodim
o'z izini tozalab qo'ya olardi.

Foydalanuvchi va ombor nomi yozuv paytida **nusxa sifatida** saqlanadi,
tashqi kalit cheklovisiz. Sabab ikki xil:

1. Xodim yoki ombor keyin o'chirilsa ham, tarix "kim" va "qayerda"
   degan savolga javob berishda davom etishi kerak.
2. Tashqi kalit `SET NULL` bilan bo'lsa, o'chirish jurnal yozuvini
   o'zgartirishga urinardi va append-only trigger uni bloklardi —
   ya'ni xodimni o'chirib bo'lmay qolardi.
"""

from __future__ import annotations

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from apps.core.models import TenantOwnedModel


class AuditEvent(TenantOwnedModel):
    """Bitta amal."""

    class Action(models.TextChoices):
        CREATE = 'create', _('Qo‘shildi')
        UPDATE = 'update', _('O‘zgartirildi')
        DELETE = 'delete', _('O‘chirildi')
        CONFIRM = 'confirm', _('Tasdiqlandi')
        CANCEL = 'cancel', _('Bekor qilindi')
        SEND = 'send', _('Jo‘natildi')
        RECEIVE = 'receive', _('Qabul qilindi')
        ADJUST = 'adjust', _('Qo‘lda tuzatildi')
        STOCKTAKE = 'stocktake', _('Inventarizatsiya')
        PAYMENT = 'payment', _('To‘lov qabul qilindi')
        SYNC = 'sync', _('Sinxronlandi')
        IMPORT = 'import', _('Import qilindi')

    #: Obyekt turlari va ularning nomi. Model maydonida `choices` emas —
    #: yangi bo'lim qo'shilganda migratsiya talab qilmasin.
    OBJECT_TYPES: dict[str, str] = {
        'purchase': 'Kirim',
        'sale': 'Sotuv',
        'return_in': 'Mijozdan qaytish',
        'return_out': 'Yetkazuvchiga qaytarish',
        'transfer': 'Ko‘chirish',
        'debt': 'Qarz',
        'stock': 'Qoldiq',
        'batch': 'Partiya',
        'product': 'Mahsulot',
        'variant': 'Variant',
        'product_unit': 'O‘ram birligi',
        'barcode': 'Shtrix-kod',
        'category': 'Kategoriya',
        'attribute': 'Atribut',
        'warehouse': 'Ombor',
        'warehouse_access': 'Ombor huquqi',
        'partner': 'Kontragent',
        'member': 'Xodim',
        'settings': 'Sozlamalar',
        'company': 'Kompaniya',
        'currency': 'Valyuta',
        'exchange_rate': 'Valyuta kursi',
        'unit': 'O‘lchov birligi',
    }

    action = models.CharField(_('Amal'), max_length=20, choices=Action.choices)

    object_type = models.CharField(_('Obyekt turi'), max_length=40)

    object_id = models.CharField(_('Obyekt ID'), max_length=64, blank=True)

    #: Obyektning yozuv paytidagi nomi: hujjat raqami, mahsulot nomi va h.k.
    object_repr = models.CharField(_('Obyekt'), max_length=250, blank=True)

    #: Ombor — ID va nom nusxasi, tashqi kalitsiz (modul izohiga qarang)
    warehouse_id = models.PositiveBigIntegerField(_('Ombor ID'), null=True, blank=True)
    warehouse_name = models.CharField(_('Ombor'), max_length=150, blank=True)

    #: Kim bajardi. `db_constraint=False` va `DO_NOTHING`: xodim o'chirilsa
    #: yozuv o'zgarmaydi, ism esa `user_name` da qoladi.
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.DO_NOTHING,
        db_constraint=False,
        null=True,
        blank=True,
        related_name='+',
        verbose_name=_('Foydalanuvchi'),
    )
    user_name = models.CharField(_('Foydalanuvchi'), max_length=150, blank=True)

    details = models.CharField(_('Tafsilot'), max_length=500, blank=True)

    #: Tahrirda nima o'zgargani: `{"maydon": [eski, yangi]}`
    changes = models.JSONField(_('O‘zgarishlar'), default=dict, blank=True)

    class Meta:
        verbose_name = _('Amal')
        verbose_name_plural = _('Amallar tarixi')
        ordering = ['-created_at', '-id']
        indexes = [
            models.Index(fields=['tenant', '-created_at']),
            models.Index(fields=['tenant', 'user', '-created_at']),
            models.Index(fields=['tenant', 'object_type', 'object_id']),
        ]

    def __str__(self):
        return f'{self.get_action_display()}: {self.object_repr}'

    @property
    def object_type_display(self) -> str:
        return self.OBJECT_TYPES.get(self.object_type, self.object_type)

    def save(self, *args, **kwargs):
        """Faqat yangi yozuv. Mavjud yozuvni saqlashga urinish — dasturchi xatosi.

        Baza triggeri ham buni to'xtatadi; bu yerda xato aniqroq va
        so'rov bazaga yetmasdan ushlanadi.
        """
        if self.pk is not None:
            raise RuntimeError('Tarix yozuvini o‘zgartirib bo‘lmaydi')

        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise RuntimeError('Tarix yozuvini o‘chirib bo‘lmaydi')
