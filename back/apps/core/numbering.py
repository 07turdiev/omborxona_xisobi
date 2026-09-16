"""Hujjat raqamlari: `KIR-2026-000001`.

Raqam har yili qaytadan boshlanadi. Ikki xodim bir vaqtda hujjat
yaratganda bir xil raqam chiqmasligi uchun raqam berish tranzaksiya
davomida qulflanadi (`pg_advisory_xact_lock`) — shu tur va shu yil uchun
navbat hosil bo'ladi, boshqa hujjatlar kutmaydi.
"""

from django.db import connection
from django.db.models import Max
from django.utils import timezone


def next_number(prefix: str, queryset, on_date=None) -> str:
    """Keyingi bo'sh raqamni qaytaradi. Tranzaksiya ichida chaqiriladi."""
    on_date = on_date or timezone.localdate()
    start = f'{prefix}-{on_date.year}-'

    with connection.cursor() as cursor:
        cursor.execute('SELECT pg_advisory_xact_lock(hashtext(%s))', [start])

    last = queryset.filter(number__startswith=start).aggregate(last=Max('number'))['last']
    counter = int(last.rsplit('-', 1)[1]) + 1 if last else 1

    return f'{start}{counter:06d}'
