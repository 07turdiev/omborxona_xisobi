"""Sayt nishonchalarini logotipdan yasaydi.

Logotip keng yozuvdan iborat ("Madlen sen"), shuning uchun u 16x16 da
umuman o'qilmaydi. Nishoncha uchun logotipdagi **gul** kesib olinadi va
brend rangidagi kvadrat fonga qo'yiladi: shunda belgi brauzerning
yorug' ham, qorong'i ham panelida ko'rinadi.

Ishga tushirish (Pillow kerak):

    python scripts/make-icons.py

Natija `public/` ga tushadi va repoga qo'shiladi — oddiy yig'ishda bu
skript chaqirilmaydi. Logotip o'zgarsa qaytadan yugurtiriladi va
pastdagi kesish koordinatalari qayta o'lchanadi.
"""

from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
LOGO = ROOT / 'src' / 'assets' / 'logo.webp'
PUBLIC = ROOT / 'public'

# Brend ranglari — `src/assets/app.css` dagi `--accent` va `--bg`
BRAND = (138, 102, 54, 255)
PAPER = (247, 244, 239, 255)

# Gulning logotipdagi o'rni (560x250 piksel logotipda o'lchangan)
FLOWER_BOX = (272, 2, 392, 100)

# Gul yonidagi poya va barglar: ular kichik o'lchamda chalkashtiradi
ERASE = [
    (0, 56, 30, 98),    # chapdagi barglar va poya
    (104, 70, 120, 98),  # o'ngdagi poya
]


def flower() -> Image.Image:
    """Logotipdan faqat gulni, atrofidagi novdalarsiz qaytaradi."""
    logo = Image.open(LOGO).convert('RGBA')
    cut = logo.crop(FLOWER_BOX)

    mask = Image.new('L', cut.size, 255)
    draw = ImageDraw.Draw(mask)

    for box in ERASE:
        draw.rectangle(box, fill=0)

    blank = Image.new('L', cut.size, 0)
    cut.putalpha(Image.composite(cut.split()[3], blank, mask))

    return cut.crop(cut.getbbox())


def square(art: Image.Image, size: int, fill: float, radius: float = 0.0) -> Image.Image:
    """Gulni kvadrat fonning o'rtasiga joylaydi.

    `fill` — gul kvadratning qancha qismini egallashi. Kichik
    o'lchamda kattaroq bo'lgani yaxshi, aks holda belgi yo'qoladi.
    `radius` — burchak yumaloqligi (0 bo'lsa to'g'ri kvadrat).
    """
    canvas = Image.new('RGBA', (size, size), (0, 0, 0, 0))

    if radius:
        shape = Image.new('L', (size * 4, size * 4), 0)
        ImageDraw.Draw(shape).rounded_rectangle(
            (0, 0, size * 4 - 1, size * 4 - 1),
            radius=int(size * 4 * radius),
            fill=255,
        )
        corners = shape.resize((size, size), Image.LANCZOS)
    else:
        corners = Image.new('L', (size, size), 255)

    background = Image.new('RGBA', (size, size), BRAND)
    canvas.paste(background, (0, 0), corners)

    width = int(size * fill)
    height = max(1, round(width * art.height / art.width))
    scaled = art.resize((width, height), Image.LANCZOS)

    canvas.alpha_composite(scaled, ((size - width) // 2, (size - height) // 2))

    return canvas


def main() -> None:
    art = flower()

    PUBLIC.mkdir(exist_ok=True)

    # Brauzer paneli: belgi kichkina, shuning uchun gul kattaroq
    small, medium, large = (square(art, n, fill=0.88, radius=0.18) for n in (16, 32, 48))

    medium.save(PUBLIC / 'favicon-32.png')

    # Har o'lcham ALOHIDA chiziladi. Faqat `sizes` berilsa Pillow
    # asosiy rasmni cho'zadi: 16 px dan yasalgan 48 px xira chiqadi.
    large.save(
        PUBLIC / 'favicon.ico',
        format='ICO',
        sizes=[(48, 48), (32, 32), (16, 16)],
        append_images=[medium, small],
    )

    # iOS o'zi burchakni yumaloqlaydi va shaffoflikni qora qiladi:
    # shuning uchun to'g'ri kvadrat va shaffofliksiz
    apple = square(art, 180, fill=0.74).convert('RGB')
    apple.save(PUBLIC / 'apple-touch-icon.png')

    for size in (192, 512):
        square(art, size, fill=0.72).save(PUBLIC / f'icon-{size}.png')

    # «Maskable» nishoncha: Android uni doira qilib qirqishi mumkin,
    # shuning uchun rasm ichki 80% doiradan chiqmasligi kerak. 0.56
    # da gulning burchaklari ham doira ichida qoladi.
    square(art, 512, fill=0.56).save(PUBLIC / 'icon-maskable-512.png')

    for path in sorted(PUBLIC.iterdir()):
        print(f'{path.name:24} {path.stat().st_size:>7} bayt')


if __name__ == '__main__':
    main()
