"""Mahalliy kun chegaralari.

Vaqt bazada UTC da saqlanadi, do'kon esa Toshkent vaqtida ishlaydi.
Soat 23:30 dagi chek o'sha kunning hisobotiga tushishi uchun kun
chegarasi mahalliy vaqtdan olinadi va UTC ga o'giriladi.
"""

from datetime import datetime, time, timedelta

from django.utils import timezone


def local_bounds(date_from, date_to):
    """[boshlanish, tugash) — mahalliy kunlar UTC vaqtiga o'girilgan."""
    tz = timezone.get_current_timezone()

    start = datetime.combine(date_from, time.min, tzinfo=tz)
    end = datetime.combine(date_to + timedelta(days=1), time.min, tzinfo=tz)

    return start, end


def today_bounds():
    """Bugungi mahalliy kun chegaralari."""
    today = timezone.localdate()

    return local_bounds(today, today)
