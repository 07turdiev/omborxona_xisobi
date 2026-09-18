"""Yuklangan rasmni uchta o'lchamga keltirish.

Nega uchta: ro'yxatdagi kartaga 200 px yetarli, mahsulot sahifasiga
800 px, kattalashtirishga esa 1600 px. Har joyda bitta katta faylni
berish telefon internetida sezilarli sekinlik beradi.

Asl fayl **saqlanmaydi**. Sabab: 15 MB gacha bo'lgan asl nusxalar
yuzlab mahsulotda ombor joyini keraksiz egallaydi, 1600 px WebP esa
onlayn do'kon uchun ham yetarli sifat beradi.
"""

from io import BytesIO
from uuid import uuid4

from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.utils.translation import gettext_lazy as _
from PIL import Image, ImageOps, UnidentifiedImageError

#: Bundan kattasi qabul qilinmaydi
MAX_UPLOAD_BYTES = 15 * 1024 * 1024

#: Nomi → eng uzun tomoni (piksel)
SIZES = {'thumb': 200, 'medium': 800, 'large': 1600}

QUALITY = 80


def _open(upload) -> Image.Image:
    try:
        image = Image.open(upload)
        image.load()
    except (UnidentifiedImageError, OSError, ValueError) as error:
        raise ValidationError(
            _('Bu fayl rasm emas yoki buzilgan. JPG, PNG yoki WebP yuklang.')
        ) from error

    return image


def _prepare(image: Image.Image) -> Image.Image:
    """Burilishni qo'llaydi va WebP uchun rang rejimini to'g'rilaydi.

    Telefonda olingan rasm ko'pincha "yotgan" holatda saqlanadi va
    faqat EXIF dagi burilish belgisi uni to'g'ri ko'rsatadi. Rasmni
    qayta o'lchaganda bu belgi yo'qoladi, shuning uchun burilish
    oldindan qo'llanadi. Saqlashda EXIF ko'chirilmaydi — u bilan birga
    suratga olingan joy koordinatalari ham ketardi.
    """
    image = ImageOps.exif_transpose(image)

    if image.mode in ('RGBA', 'LA'):
        return image.convert('RGBA')

    return image.convert('RGB')


def build_sizes(upload) -> dict[str, ContentFile]:
    """Yuklangan fayldan uchta WebP yasaydi: `{'thumb': ..., ...}`."""
    if upload.size > MAX_UPLOAD_BYTES:
        raise ValidationError(
            _('Rasm hajmi 15 MB dan oshmasligi kerak. Kichikroq rasm tanlang.')
        )

    image = _prepare(_open(upload))
    name = uuid4().hex

    result = {}

    for key, longest in SIZES.items():
        # `thumbnail` nisbatni saqlaydi va **faqat kichraytiradi**.
        # Kichik rasmni cho'zish faylni og'irlashtiradi, lekin sifat
        # qo'shmaydi: 300 px li rasm uchala o'lchamda ham 300 px qoladi.
        resized = image.copy()
        resized.thumbnail((longest, longest), Image.LANCZOS)

        buffer = BytesIO()
        resized.save(buffer, format='WEBP', quality=QUALITY, method=4)

        result[key] = ContentFile(buffer.getvalue(), name=f'{name}-{key}.webp')

    return result
