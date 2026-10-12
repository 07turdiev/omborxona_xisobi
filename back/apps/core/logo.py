"""Chek logotipi: yuklangan rasmdan chek printeri chiza oladigan nuqtalar.

Chek printeri kulrangni bilmaydi: har nuqta yo qora, yo oq. Shuning
uchun rasm bir marta — yuklanganda — tayyorlanadi:

1. shaffof joylar oq qilinadi va rasm kulrangga o'tkaziladi;
2. atrofidagi bo'sh hoshiya kesiladi — aks holda logotip chekda
   keraksiz kichik chiqadi;
3. o'lchami chekka moslanadi: eni ko'pi bilan 48 mm, bo'yi 24 mm;
4. har nuqta chegara bo'yicha qora yoki oq bo'ladi. Aralashtirish
   (dithering) qilinmaydi: logotipda tekis ranglar bo'ladi va
   aralashtirish ularni nuqtali qilib yuboradi.

Natija ikki ko'rinishda saqlanadi: chop etish agenti uchun ESC/POS
nuqtalari (`raster`) va brauzer uchun PNG. Ikkalasi bitta rasmdan
yasaladi, shuning uchun Sozlamalarda ko'ringani qog'ozda chiqadigani
bilan bir xil.
"""

import base64
from io import BytesIO

from django.core.exceptions import ValidationError
from PIL import Image, ImageOps, UnidentifiedImageError

#: Bundan kattasi qabul qilinmaydi
MAX_UPLOAD_BYTES = 5 * 1024 * 1024

#: Logotip chekda shundan katta bo'lmaydi, nuqta (203 dpi: 8 nuqta = 1 mm)
MAX_WIDTH = 384
MAX_HEIGHT = 192

#: Shundan to'qroq nuqta qora bo'ladi (0 — qora, 255 — oq)
THRESHOLD = 128


def _open(upload) -> Image.Image:
    if upload.size > MAX_UPLOAD_BYTES:
        raise ValidationError('Rasm hajmi 5 MB dan oshmasligi kerak.')

    try:
        image = Image.open(upload)
        image.load()
    except (UnidentifiedImageError, OSError, ValueError) as error:
        raise ValidationError('Bu fayl rasm emas yoki buzilgan. PNG yoki JPG yuklang.') from error

    return ImageOps.exif_transpose(image)


def _gray_on_white(image: Image.Image) -> Image.Image:
    """Shaffof joylar oq qog'oz bo'ladi.

    To'g'ridan-to'g'ri kulrangga o'tkazilsa, shaffof nuqtalar odatda
    qora bo'lib qoladi (ularning rangi — 0, 0, 0) va logotip o'rnida
    qora to'rtburchak chiqadi.
    """
    paper = Image.new('RGBA', image.size, 'white')
    paper.alpha_composite(image.convert('RGBA'))

    return paper.convert('L')


def build_receipt_logo(upload) -> dict:
    """Yuklangan rasmdan chek logotipini yasaydi.

    Qaytadi: `{'width', 'height', 'raster', 'png'}`. `width` — 8 ga
    karrali: printer har qatorni baytlab oladi. `raster` — qatorma-qator
    baytlar (1 — qora nuqta), base64 da. `png` — brauzer uchun
    `data:` manzil.
    """
    gray = _gray_on_white(_open(upload))

    # Bo'sh hoshiya kesiladi: faqat qora bo'ladigan joy qoladi
    box = gray.point(lambda value: 255 if value < THRESHOLD else 0).getbbox()

    if box is None:
        raise ValidationError('Rasmda chiziladigan narsa yo‘q: u butunlay oq yoki juda och.')

    gray = gray.crop(box)

    # Chekka moslanadi: kattasi kichrayadi, kichigi kattalashadi
    scale = min(MAX_WIDTH / gray.width, MAX_HEIGHT / gray.height)
    size = (max(1, round(gray.width * scale)), max(1, round(gray.height * scale)))
    gray = gray.resize(size, Image.LANCZOS)

    width = (gray.width + 7) // 8 * 8
    padded = Image.new('L', (width, gray.height), 255)
    padded.paste(gray, ((width - gray.width) // 2, 0))

    mono = padded.point(lambda value: 0 if value < THRESHOLD else 255).convert(
        '1', dither=Image.Dither.NONE
    )

    # Pillow da 1 — oq, printerda esa 1 — qora nuqta
    raster = bytes(byte ^ 0xFF for byte in mono.tobytes())

    png = BytesIO()
    mono.save(png, format='PNG', optimize=True)

    return {
        'width': width,
        'height': mono.height,
        'raster': base64.b64encode(raster).decode('ascii'),
        'png': 'data:image/png;base64,' + base64.b64encode(png.getvalue()).decode('ascii'),
    }
