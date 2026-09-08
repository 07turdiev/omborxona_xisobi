"""PostgreSQL `ltree` maydoni.

Loyihaning 4-arxitektura qarori: kategoriya daraxti uchun `ltree`,
`django-mptt` emas. Sabab: MPTT har qo'shishda `lft`/`rght` ustunlarini
butun daraxt bo'ylab qayta hisoblaydi va daraxt buzilganda `rebuild()`
talab qiladi. `ltree` da yo'l — oddiy ustun, ajdod/avlod so'rovi esa
GiST indeks ustidagi bitta operator.

Django `ltree` ni bilmaydi, shuning uchun maydon va operatorlar shu
yerda ta'riflangan. Kutubxona qo'shmadik: kerakli qism ~60 qator va
uni o'zimiz nazorat qilganimiz ma'qul.

Yo'l belgilari `ltree` cheklovi bo'yicha faqat `[A-Za-z0-9_]` bo'lishi
mumkin. O'zbekcha nomlarda apostrof va bo'shliq bor, shuning uchun yo'l
**nomdan emas, ID dan** quriladi: `c1.c7.c23`. Bu nomni o'zgartirganda
yo'l buzilmasligini ham ta'minlaydi.
"""

from __future__ import annotations

from django.db import models


class LtreeField(models.Field):
    """PostgreSQL `ltree` ustuni."""

    description = 'PostgreSQL ltree yo\'li'

    def db_type(self, connection) -> str:
        return 'ltree'

    def from_db_value(self, value, expression, connection):
        return value

    def to_python(self, value):
        if value is None or isinstance(value, str):
            return value
        return str(value)

    def get_prep_value(self, value):
        if value is None:
            return None
        return str(value)


class _LtreeOperatorLookup(models.Lookup):
    """`ltree` operatorlari uchun umumiy asos."""

    operator = ''

    def as_sql(self, compiler, connection):
        lhs, lhs_params = self.process_lhs(compiler, connection)
        rhs, rhs_params = self.process_rhs(compiler, connection)

        return f'{lhs} {self.operator} {rhs}', list(lhs_params) + list(rhs_params)


@LtreeField.register_lookup
class AncestorOf(_LtreeOperatorLookup):
    """`path__ancestor_of=X` — chap tomon X ning ajdodi (yoki o'zi)."""

    lookup_name = 'ancestor_of'
    operator = '@>'


@LtreeField.register_lookup
class DescendantOf(_LtreeOperatorLookup):
    """`path__descendant_of=X` — chap tomon X ning avlodi (yoki o'zi)."""

    lookup_name = 'descendant_of'
    operator = '<@'


@LtreeField.register_lookup
class MatchesLquery(_LtreeOperatorLookup):
    """`path__matches='c1.*{1}'` — lquery shabloni bo'yicha moslik."""

    lookup_name = 'matches'
    operator = '~'


@LtreeField.register_lookup
class Depth(models.Transform):
    """`path__depth` — yo'ldagi darajalar soni (`nlevel`)."""

    lookup_name = 'depth'
    output_field = models.IntegerField()

    def as_sql(self, compiler, connection):
        lhs, params = compiler.compile(self.lhs)
        return f'nlevel({lhs})', params
