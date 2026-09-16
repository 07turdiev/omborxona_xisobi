"""Kassirdan yashiriladigan maydonlar.

Kassir tannarx, foyda va ta'minotchi ma'lumotini ko'rmaydi. Interfeysda
yashirish yetarli emas — maydon javobning o'zida bo'lmasligi kerak,
shuning uchun tozalash serializer darajasida.
"""


class HideFromCashierMixin:
    """`admin_only_fields` ro'yxatidagi maydonlarni kassirga chiqarmaydi."""

    admin_only_fields: tuple[str, ...] = ()

    def to_representation(self, instance):
        data = super().to_representation(instance)
        user = getattr(self.context.get('request'), 'user', None)

        if user is not None and not getattr(user, 'is_admin', False):
            for field in self.admin_only_fields:
                data.pop(field, None)

        return data
