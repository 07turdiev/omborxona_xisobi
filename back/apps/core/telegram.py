"""Boshliqqa Telegram orqali bildirishnoma.

Do'kon egasi kun bo'yi do'konda turmaydi, lekin pul va qoldiq
o'zgarganini bilishi kerak. Bot shu uchun: har sotuv, har qabul,
bekor qilish, qaytarish, hisobdan chiqarish va narx o'zgarishi
telefoniga tushadi.

**Bildirishnoma hech qachon ishni to'xtatmaydi.** Telegram ishlamay
qolsa yoki internet uzilsa, sotuv baribir yakunlanadi: xabar alohida
oqimda yuboriladi va xatosi faqat jurnalga yoziladi. Kassir buni
sezmaydi ham.

Sozlash:

    TELEGRAM_BOT_TOKEN=...    @BotFather bergan token
    TELEGRAM_CHAT_IDS=...,... kimlarga yuboriladi (vergul bilan)

Ikkalasi `.env` da. Token yo'q bo'lsa modul jim turadi — ishlab
chiqish kompyuterida va testlarda hech narsa yuborilmaydi.
"""

import json
import logging
import threading
import urllib.error
import urllib.request

from django.conf import settings
from django.db import transaction

logger = logging.getLogger(__name__)

API = 'https://api.telegram.org/bot{token}/sendMessage'

#: Javobni uzoq kutmaymiz: xabar kechikkanidan ko'ra tushmagani yaxshi
TIMEOUT = 10


def chats() -> list[str]:
    """Xabar boradigan Telegram hisoblari.

    Sozlamada vergul bilan yoziladi: do'konda bir necha rahbar bor va
    har biri o'z telefonida ko'radi.
    """
    raw = getattr(settings, 'TELEGRAM_CHAT_IDS', '') or ''

    return [chat.strip() for chat in raw.split(',') if chat.strip()]


def configured() -> bool:
    return bool(getattr(settings, 'TELEGRAM_BOT_TOKEN', '')) and bool(chats())


def _send(text: str) -> None:
    """Xabarni hamma qabul qiluvchiga yuboradi. Xatolik yutiladi.

    Bittasiga yetib bormasa (hisob bloklagan, chat o'chirilgan),
    qolganlari baribir oladi — shuning uchun har biri alohida
    uriniladi.
    """
    for chat in chats():
        payload = json.dumps(
            {
                'chat_id': chat,
                'text': text,
                'parse_mode': 'HTML',
                'disable_web_page_preview': True,
            }
        ).encode()

        request = urllib.request.Request(
            API.format(token=settings.TELEGRAM_BOT_TOKEN),
            data=payload,
            headers={'Content-Type': 'application/json'},
        )

        try:
            with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
                if response.status != 200:
                    logger.warning('Telegram javobi (%s): %s', chat, response.status)
        except (urllib.error.URLError, TimeoutError, OSError) as error:
            # Internet uzilgani sotuvni to'xtatmasligi kerak
            logger.warning('Telegramga yuborilmadi (%s): %s', chat, error)


def _dispatch(text: str) -> None:
    """Yuborishni alohida oqimga beradi.

    Kassir Telegramning javobini kutib o'tirmaydi: sotuv allaqachon
    bazaga yozilgan, xabar esa fonda ketadi.
    """
    threading.Thread(target=_send, args=(text,), daemon=True).start()


def notify(text: str) -> None:
    """Bildirishnomani navbatga qo'yadi.

    Tranzaksiya yakunlangandan keyin yuboriladi: aks holda keyin
    bekor bo'lgan sotuv haqida xabar ketib qolardi.
    """
    if not configured():
        return

    transaction.on_commit(lambda: _dispatch(text))


def money(value) -> str:
    """`1234567.00` -> `1 234 567`. Chekdagi kabi uchtadan ajratilgan."""
    return f'{int(round(float(value))):,}'.replace(',', ' ')


def who(user) -> str:
    if user is None:
        return 'noma’lum'

    return user.get_full_name() or user.username
