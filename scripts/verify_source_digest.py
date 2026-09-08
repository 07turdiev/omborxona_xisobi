"""NOTICE faylidagi manba digestini qayta hisoblab tekshiradi.

Foydalanish:
    python scripts/verify_source_digest.py [manba-papka]

Standart manba papka: InvenTree-master/ (repoga kirmaydi, .gitignore da).
Papka mavjud bo'lmasa skript ogohlantirish bilan chiqadi — bu xato emas,
chunki manba read-only ma'lumotnoma va har bir ishchida bo'lishi shart emas.
"""

from __future__ import annotations

import hashlib
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SOURCE = REPO_ROOT / 'InvenTree-master'
NOTICE = REPO_ROOT / 'NOTICE'


def compute_digest(root: Path) -> tuple[str, int]:
    """Papka tarkibidan barqaror digest hisoblaydi.

    Har fayl uchun "<sha256>  <nisbiy_yo'l>\\n" satri hosil qilinadi,
    satrlar yo'l bo'yicha saralanadi va ketma-ketlikning SHA-256 i olinadi.
    """
    files = sorted(p for p in root.rglob('*') if p.is_file())
    outer = hashlib.sha256()

    for path in files:
        rel = path.relative_to(root).as_posix()
        inner = hashlib.sha256(path.read_bytes()).hexdigest()
        outer.update(f'{inner}  {rel}\n'.encode())

    return outer.hexdigest(), len(files)


def read_expected_digest() -> str:
    """NOTICE faylidan kutilayotgan digestni o'qiydi."""
    match = re.search(r'^\s{4}([0-9a-f]{64})\s*$', NOTICE.read_text(encoding='utf-8'), re.M)

    if not match:
        raise SystemExit('NOTICE faylida SHA-256 digest topilmadi')

    return match.group(1)


def main() -> int:
    source = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_SOURCE

    if not source.is_dir():
        print(f'Manba papka topilmadi: {source}')
        print('Tekshiruv o\'tkazib yuborildi (manba read-only ma\'lumotnoma).')
        return 0

    expected = read_expected_digest()
    actual, count = compute_digest(source)

    print(f'Manba   : {source}')
    print(f'Fayllar : {count}')
    print(f'Kutilgan: {expected}')
    print(f'Hisoblab: {actual}')

    if actual != expected:
        print('\nMOS KELMADI — manba NOTICE da qayd etilgan holatdan farq qiladi.')
        print('NOTICE dagi fayl:qator havolalari eskirgan bo\'lishi mumkin.')
        return 1

    print('\nMOS KELDI.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
