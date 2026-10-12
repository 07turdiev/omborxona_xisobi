"""Boshliqqa Telegram orqali bildirishnoma.

Do'kon egasi kun bo'yi do'konda turmaydi, lekin pul va qoldiq
o'zgarganini bilishi kerak. Bot shu uchun: har sotuv, har qabul,
bekor qilish, qaytarish, hisobdan chiqarish va narx o'zgarishi
telefoniga tushadi. Sotuvda tovarning rasmi ham boradi — qaysi kiyim
ketganini matndan emas, ko'rinishidan bilish osonroq.

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
from io import BytesIO
from uuid import uuid4

from django.conf import settings
from django.db import transaction

logger = logging.getLogger(__name__)

API = 'https://api.telegram.org/bot{token}/{method}'

#: Javobni uzoq kutmaymiz: xabar kechikkanidan ko'ra tushmagani yaxshi.
#: Rasm yuklanishi matndan sekinroq, shuning uchun 15.
TIMEOUT = 15

#: Rasm ostidagi izohga Telegram shuncha belgi beradi
CAPTION_LIMIT = 1024


def chats() -> list[str]:
    """Xabar boradigan Telegram hisoblari.

    Sozlamada vergul bilan yoziladi: do'konda bir necha rahbar bor va
    har biri o'z telefonida ko'radi.
    """
    raw = getattr(settings, 'TELEGRAM_CHAT_IDS', '') or ''

    return [chat.strip() for chat in raw.split(',') if chat.strip()]


def configured() -> bool:
    return bool(getattr(settings, 'TELEGRAM_BOT_TOKEN', '')) and bool(chats())


def _call(request: urllib.request.Request) -> tuple[bool, str, dict]:
    """So'rovni yuboradi va javobni ochadi.

    Telegram xato sababini javob tanasida aytadi («chat not found»),
    shuning uchun u o'qib olinadi: aks holda faqat «400» ko'rinardi.
    """
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
            if response.status != 200:
                return False, f'javob {response.status}', {}

            return True, 'yuborildi', json.loads(response.read()).get('result', {})
    except urllib.error.HTTPError as error:
        try:
            detail = json.loads(error.read()).get('description', str(error))
        except (ValueError, OSError):
            detail = str(error)

        return False, detail, {}
    except (urllib.error.URLError, TimeoutError, OSError, ValueError) as error:
        return False, str(error), {}


def _json_request(method: str, payload: dict) -> urllib.request.Request:
    return urllib.request.Request(
        API.format(token=settings.TELEGRAM_BOT_TOKEN, method=method),
        data=json.dumps(payload).encode(),
        headers={'Content-Type': 'application/json'},
    )


def _photo_request(fields: dict, photo: bytes) -> urllib.request.Request:
    """Rasmni `multipart/form-data` bilan yuklaydi.

    Rasmning manzilini berib qo'ya qolmaymiz: fayllar WebP da
    saqlanadi, Telegram esa uni rasm sifatida qabul qilmaydi. Shuning
    uchun JPEG baytlari yuklanadi (`photo_bytes`).
    """
    boundary = f'----dokon{uuid4().hex}'
    body = BytesIO()

    for name, value in fields.items():
        body.write(f'--{boundary}\r\n'.encode())
        body.write(f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode())
        body.write(f'{value}\r\n'.encode())

    body.write(f'--{boundary}\r\n'.encode())
    body.write(
        b'Content-Disposition: form-data; name="photo"; filename="tovar.jpg"\r\n'
        b'Content-Type: image/jpeg\r\n\r\n'
    )
    body.write(photo)
    body.write(f'\r\n--{boundary}--\r\n'.encode())

    return urllib.request.Request(
        API.format(token=settings.TELEGRAM_BOT_TOKEN, method='sendPhoto'),
        data=body.getvalue(),
        headers={'Content-Type': f'multipart/form-data; boundary={boundary}'},
    )


def send_to(chat: str, text: str) -> tuple[bool, str]:
    """Bitta hisobga matn yuboradi.

    Eng ko'p uchraydigan xato — odam botga hali `/start` bosmagan:
    Telegram bunda «chat not found» deydi.
    """
    ok, detail, _ = _call(
        _json_request(
            'sendMessage',
            {
                'chat_id': chat,
                'text': text,
                'parse_mode': 'HTML',
                'disable_web_page_preview': True,
            },
        )
    )

    return ok, detail


def send_photo_to(
    chat: str, caption: str, photo: bytes = b'', file_id: str = ''
) -> tuple[bool, str, str]:
    """Rasmni izoh bilan yuboradi va Telegramdagi `file_id` ni qaytaradi.

    Bir xil rasm bir necha kishiga ketadi. Birinchisida fayl yuklanadi,
    qolganlariga esa `file_id` uzatiladi — Telegram uni o'zida saqlab
    qo'ygan, qayta yuklashning hojati yo'q.
    """
    caption = caption[:CAPTION_LIMIT]

    if file_id:
        request = _json_request(
            'sendPhoto',
            {'chat_id': chat, 'photo': file_id, 'caption': caption, 'parse_mode': 'HTML'},
        )
    else:
        request = _photo_request(
            {'chat_id': chat, 'caption': caption, 'parse_mode': 'HTML'}, photo
        )

    ok, detail, result = _call(request)
    sizes = result.get('photo') or []

    return ok, detail, (sizes[-1].get('file_id', '') if sizes else '')


def bot_link() -> str:
    """Botning havolasi: `https://t.me/<nom>`.

    Qabul qiluvchi botga `/start` bosmaguncha Telegram xabarni rad
    etadi, shuning uchun unga aynan qaysi botni ochish kerakligini
    aytish kerak. Nom tokendan emas, Telegramning o'zidan so'raladi.
    """
    ok, _, result = _call(_json_request('getMe', {}))
    name = result.get('username', '') if ok else ''

    return f'https://t.me/{name}' if name else ''


def photo_bytes(image) -> bytes:
    """Mahsulot rasmini Telegram qabul qiladigan ko'rinishga keltiradi.

    Fayllar WebP da saqlanadi, `sendPhoto` esa JPEG kutadi. O'rta
    o'lcham olinadi: 800 px telefonda yetarli, kattasi esa har
    xabarda behuda trafik.

    Rasm ochilmasa bo'sh qaytadi — xabar matn bilan ketaveradi.
    """
    from PIL import Image, UnidentifiedImageError

    try:
        with image.open('rb') as source:
            picture = Image.open(source)
            picture.load()

        if picture.mode != 'RGB':
            picture = picture.convert('RGB')

        buffer = BytesIO()
        picture.save(buffer, format='JPEG', quality=85)

        return buffer.getvalue()
    except (OSError, ValueError, UnidentifiedImageError) as error:
        logger.warning('Rasmni JPEG ga o‘girib bo‘lmadi: %s', error)

        return b''


def _send(text: str, photo: bytes = b'') -> None:
    """Xabarni hamma qabul qiluvchiga yuboradi. Xatolik yutiladi.

    Bittasiga yetib bormasa (hisob bloklagan, `/start` bosilmagan),
    qolganlari baribir oladi — shuning uchun har biri alohida
    uriniladi va xato faqat jurnalga yoziladi.

    Rasm ketmasa xabar matn bilan yuboriladi: suratsiz bo'lsa ham
    sotuvdan xabardor bo'lish muhimroq.
    """
    file_id = ''

    for chat in chats():
        if photo or file_id:
            ok, detail, sent = send_photo_to(
                chat, text, photo=b'' if file_id else photo, file_id=file_id
            )

            if ok:
                file_id = file_id or sent

                continue

            logger.warning('Rasm yuborilmadi (%s): %s', chat, detail)

        ok, detail = send_to(chat, text)

        if not ok:
            logger.warning('Telegramga yuborilmadi (%s): %s', chat, detail)


def _dispatch(text: str, photo: bytes = b'') -> None:
    """Yuborishni alohida oqimga beradi.

    Kassir Telegramning javobini kutib o'tirmaydi: sotuv allaqachon
    bazaga yozilgan, xabar esa fonda ketadi.
    """
    threading.Thread(target=_send, args=(text, photo), daemon=True).start()


def notify(text: str, photo: bytes = b'') -> None:
    """Bildirishnomani navbatga qo'yadi.

    Tranzaksiya yakunlangandan keyin yuboriladi: aks holda keyin
    bekor bo'lgan sotuv haqida xabar ketib qolardi.
    """
    if not configured():
        return

    transaction.on_commit(lambda: _dispatch(text, photo))


def money(value) -> str:
    """`1234567.00` -> `1 234 567`. Chekdagi kabi uchtadan ajratilgan."""
    return f'{int(round(float(value))):,}'.replace(',', ' ')


def who(user) -> str:
    if user is None:
        return 'noma’lum'

    return user.get_full_name() or user.username
