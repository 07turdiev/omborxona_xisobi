"""Excel eksport testlari.

Asosiy xavf bitta: **son matn bo'lib qolishi**. DRF `Decimal`ni matn
sifatida qaytaradi ("1500.00") va uni shundayligicha yozsak, Excel'da
`SUM()` ishlamaydi — buxgalter uchun bunday fayl foydasiz.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from apps.core.export import (
    DATE,
    DATETIME,
    MONEY,
    QUANTITY,
    TEXT,
    Column,
    build_workbook,
    excel_response,
)

D = Decimal


class CellValueTests(TestCase):
    """Qiymat Excel katagiga qanday tushishi."""

    def build(self, columns, rows):
        return build_workbook(columns, rows).active

    def test_decimal_son_sifatida_yoziladi(self):
        sheet = self.build(
            [Column('amount', 'Summa', MONEY)], [{'amount': D('1500.25')}]
        )

        cell = sheet.cell(row=2, column=1)

        self.assertEqual(cell.value, 1500.25)
        self.assertIsInstance(cell.value, float)
        self.assertEqual(cell.number_format, '#,##0.00')

    def test_serializer_qaytargan_matn_songa_ogiriladi(self):
        """DRF `Decimal`ni matn qiladi — biz uni qaytarib son qilamiz."""
        sheet = self.build(
            [Column('amount', 'Summa', MONEY), Column('qty', 'Miqdor', QUANTITY)],
            [{'amount': '1500.00', 'qty': '2.500'}],
        )

        self.assertEqual(sheet.cell(row=2, column=1).value, 1500.0)
        self.assertEqual(sheet.cell(row=2, column=2).value, 2.5)

    def test_songa_ogirib_bolmaydigan_matn_ozgarmaydi(self):
        sheet = self.build([Column('amount', 'Summa', MONEY)], [{'amount': '—'}])

        self.assertEqual(sheet.cell(row=2, column=1).value, '—')

    def test_matn_ustuni_songa_ogirilmaydi(self):
        """SKU «0012» bo'lsa, u 12 bo'lib qolmasligi kerak."""
        sheet = self.build([Column('sku', 'SKU', TEXT)], [{'sku': '0012'}])

        self.assertEqual(sheet.cell(row=2, column=1).value, '0012')

    def test_iso_sana_matni_sanaga_ogiriladi(self):
        sheet = self.build([Column('date', 'Sana', DATE)], [{'date': '2026-03-15'}])

        value = sheet.cell(row=2, column=1).value

        self.assertEqual(value.year, 2026)
        self.assertEqual(value.month, 3)
        self.assertEqual(value.day, 15)

    def test_vaqt_zonasi_mahalliyga_ogiriladi(self):
        """Excel vaqt zonasini bilmaydi — naive mahalliy vaqt yoziladi."""
        moment = timezone.make_aware(datetime(2026, 3, 15, 9, 30))

        sheet = self.build(
            [Column('at', 'Vaqt', DATETIME)],
            [{'at': moment.isoformat()}, {'at': moment}],
        )

        for row in (2, 3):
            value = sheet.cell(row=row, column=1).value

            self.assertIsNone(value.tzinfo)
            self.assertEqual(value.hour, 9)
            self.assertEqual(value.minute, 30)

    def test_sana_obyekti_ozgarmaydi(self):
        sheet = self.build([Column('d', 'Sana', DATE)], [{'d': date(2026, 1, 2)}])

        self.assertEqual(sheet.cell(row=2, column=1).value, date(2026, 1, 2))

    def test_bosh_qiymat_bosh_katak(self):
        sheet = self.build([Column('amount', 'Summa', MONEY)], [{'amount': None}])

        self.assertIsNone(sheet.cell(row=2, column=1).value)

    def test_ichma_ich_kalit(self):
        sheet = self.build(
            [Column('variant.product.name', 'Nomi', TEXT)],
            [{'variant': {'product': {'name': 'Sement'}}}],
        )

        self.assertEqual(sheet.cell(row=2, column=1).value, 'Sement')

    def test_yoq_kalit_xato_bermaydi(self):
        sheet = self.build([Column('yoq.kalit', 'X', TEXT)], [{'bor': 1}])

        self.assertIsNone(sheet.cell(row=2, column=1).value)


class WorkbookLayoutTests(TestCase):
    def test_sarlavha_va_meta_jadvalni_pastga_suradi(self):
        workbook = build_workbook(
            [Column('name', 'Nomi', TEXT)],
            [{'name': 'Sement'}],
            title='Qoldiqlar',
            meta=[('Ombor', 'Asosiy'), ('Davr', 'mart')],
        )
        sheet = workbook.active

        self.assertEqual(sheet.cell(row=1, column=1).value, 'Qoldiqlar')
        self.assertEqual(sheet.cell(row=2, column=1).value, 'Ombor:')
        self.assertEqual(sheet.cell(row=2, column=2).value, 'Asosiy')
        # 1 sarlavha + 2 meta + 1 bo'sh = 4, jadval sarlavhasi 5-qatorda
        self.assertEqual(sheet.cell(row=5, column=1).value, 'Nomi')
        self.assertEqual(sheet.cell(row=6, column=1).value, 'Sement')

    def test_meta_bolmasa_jadval_birinchi_qatordan(self):
        sheet = build_workbook([Column('name', 'Nomi', TEXT)], [{'name': 'A'}]).active

        self.assertEqual(sheet.cell(row=1, column=1).value, 'Nomi')

    def test_varaq_nomi_qisqartiriladi(self):
        workbook = build_workbook(
            [Column('a', 'A', TEXT)], [], sheet_name='Juda/uzun ' + 'x' * 40
        )

        self.assertLessEqual(len(workbook.active.title), 31)
        self.assertNotIn('/', workbook.active.title)

    def test_sarlavha_qatori_qotiriladi(self):
        sheet = build_workbook(
            [Column('name', 'Nomi', TEXT)], [{'name': 'A'}], title='X'
        ).active

        # Sarlavha 1-qatorda, bo'sh 2-qator, jadval sarlavhasi 3-qatorda
        self.assertEqual(sheet.freeze_panes, 'A4')
        self.assertEqual(sheet.auto_filter.ref, 'A3:A4')


class ExcelResponseTests(TestCase):
    def test_yuklab_olish_javobi(self):
        workbook = build_workbook([Column('a', 'A', TEXT)], [])
        response = excel_response(workbook, 'qoldiqlar')

        self.assertEqual(
            response['Content-Type'],
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        )

        stamp = timezone.localdate().strftime('%Y-%m-%d')

        self.assertEqual(
            response['Content-Disposition'],
            f"attachment; filename*=UTF-8''qoldiqlar-{stamp}.xlsx",
        )
        # xlsx — bu zip arxiv, u «PK» bilan boshlanadi
        self.assertTrue(response.content.startswith(b'PK'))


class ColumnValidationTests(TestCase):
    """Ustun turi tekshiriladi.

    Bir marta shunday bo'ldi: modulda `MONEY` nomi boshqa narsa bilan
    band edi va ustun turi o'rniga Django maydoni tushdi. Natijada
    pul summalari matn bo'lib chiqdi va buni faqat faylni ochganda
    sezish mumkin edi.
    """

    def test_notogri_tur_darhol_xato_beradi(self):
        with self.assertRaises(ValueError):
            Column('amount', 'Summa', 'valyuta')

    def test_tur_orniga_obyekt_berilsa_ham(self):
        from django.db.models import DecimalField

        with self.assertRaises(ValueError):
            Column('amount', 'Summa', DecimalField(max_digits=18, decimal_places=2))
