"""O'lchov birligi konversiyasi va registr testlari."""

from __future__ import annotations

from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import SimpleTestCase, TestCase

from apps.core.tenancy import tenant_context
from apps.units.conversion import (
    convert_to_unit,
    is_valid_unit,
    to_base_units,
    validate_unit,
)
from apps.units.models import CustomUnit
from apps.units.registry import build_registry, get_registry, invalidate_registry


class ConversionTests(SimpleTestCase):
    """Bazasiz ishlaydigan konversiya testlari (standart birliklar)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.registry = build_registry(None)

    def convert(self, value, unit=None):
        return convert_to_unit(value, unit, registry=self.registry)

    # -- asosiy konversiya ---------------------------------------------

    def test_converts_between_compatible_units(self):
        self.assertEqual(self.convert('12 mm', 'm'), Decimal('0.012'))
        self.assertEqual(self.convert('1 kg', 'g'), Decimal('1000'))

    def test_result_is_always_decimal(self):
        """6-arxitektura qarori: hech qayerda float bo'lmasligi kerak."""
        for value, unit in [('12 mm', 'm'), ('2.5', 'm3'), ('3 dona', None)]:
            with self.subTest(value=value):
                self.assertIsInstance(self.convert(value, unit), Decimal)

    def test_bare_number_takes_target_unit(self):
        """Foydalanuvchi birlikni yozmasa, atributning birligi qabul qilinadi."""
        self.assertEqual(self.convert('12', 'mm'), Decimal('12'))

    def test_incompatible_units_rejected(self):
        """Og'irlikni uzunlikka aylantirib bo'lmaydi."""
        with self.assertRaises(ValidationError):
            self.convert('50 kg', 'm')

    def test_unknown_unit_rejected(self):
        with self.assertRaises(ValidationError):
            self.convert('12', 'qwerty')

    def test_blank_value_rejected(self):
        for value in ['', '   ', None]:
            with self.subTest(value=value):
                with self.assertRaises(ValidationError):
                    self.convert(value, 'mm')

    def test_unparseable_value_rejected(self):
        with self.assertRaises(ValidationError):
            self.convert("Yog'och", 'mm')

    # -- mahalliy birliklar --------------------------------------------

    def test_local_units_available(self):
        for unit in ['dona', 'qop', 'palet', 'rulon', 'm2', 'm3', 'pogonmetr']:
            with self.subTest(unit=unit):
                self.assertTrue(is_valid_unit(unit, registry=self.registry))

    def test_area_and_volume(self):
        self.assertEqual(self.convert('2.5 m2', 'm2'), Decimal('2.5'))
        self.assertEqual(self.convert('1 m3', 'm3'), Decimal('1'))

    def test_counting_units_are_dimensionless(self):
        """`qop`, `dona` — sanoq birliklari, o'lchamsiz."""
        self.assertEqual(self.convert('3 qop'), Decimal('3'))
        self.assertEqual(self.convert('2 dozen'), Decimal('24'))

    def test_pack_unit_has_no_global_weight(self):
        """"qop" global ravishda kilogrammga bog'lanmagan.

        "1 qop = 50 kg" mahsulotga bog'liq (sement 50 kg, gips 30 kg),
        shuning uchun u registrda emas, `apps.catalog.ProductUnit` da
        saqlanadi. Bu test o'sha qarorni qotirib qo'yadi.
        """
        with self.assertRaises(ValidationError):
            self.convert('1 qop', 'kg')

    # -- normalizatsiya ------------------------------------------------

    def test_equivalent_values_normalize_equal(self):
        """"10 mm" va "1 sm" bir xil songa aylanishi kerak.

        Aks holda JSONB atributlari bo'yicha filtrlash ishlamaydi.
        """
        self.assertEqual(
            to_base_units('10 mm', registry=self.registry),
            to_base_units('1 cm', registry=self.registry),
        )

    def test_non_numeric_normalizes_to_none(self):
        """Matnli atribut normalizatsiyalanmaydi — bu xato emas."""
        self.assertIsNone(to_base_units("Yog'och", registry=self.registry))

    def test_validate_unit_returns_trimmed(self):
        self.assertEqual(validate_unit('  kg  ', registry=self.registry), 'kg')

        with self.assertRaises(ValidationError):
            validate_unit('qwerty', registry=self.registry)


class CustomUnitTests(TestCase):
    """Tashkilotning o'z birliklari — baza talab qiladi."""

    @classmethod
    def setUpTestData(cls):
        from apps.tenants.models import Tenant

        cls.tenant_a = Tenant.objects.create(name='A do\'kon', slug='a-dokon')
        cls.tenant_b = Tenant.objects.create(name='B do\'kon', slug='b-dokon')

    def test_definition_string(self):
        unit = CustomUnit(name='mashina', definition='6 * m3', symbol='msh')
        self.assertEqual(unit.definition_string, 'mashina = 6 * m3 = msh')

        unit.symbol = ''
        self.assertEqual(unit.definition_string, 'mashina = 6 * m3')

    def test_invalid_name_rejected(self):
        for name in ['2mashina', 'katta qop', 'qop-katta', '']:
            with self.subTest(name=name):
                unit = CustomUnit(tenant=self.tenant_a, name=name, definition='1')
                with self.assertRaises(ValidationError):
                    unit.clean()

    def test_invalid_definition_rejected(self):
        unit = CustomUnit(tenant=self.tenant_a, name='mashina', definition='6 * qwerty')
        with self.assertRaises(ValidationError):
            unit.clean()

    def test_custom_unit_usable_after_save(self):
        CustomUnit.objects.create(
            tenant=self.tenant_a, name='mashina', definition='6 * m3', symbol='msh'
        )

        result = convert_to_unit('2 mashina', 'm3', tenant_id=self.tenant_a.id)
        self.assertEqual(result, Decimal('12'))

    def test_custom_unit_does_not_leak_between_tenants(self):
        """Eng muhim test: bir tashkilotning birligi boshqasiga o'tmasligi kerak.

        InvenTree'da registr global (`InvenTree/conversion.py:83`), ya'ni
        bu holat u yerda buziladi. Tahlil hisobotining 3-bo'limiga qarang.
        """
        CustomUnit.objects.create(tenant=self.tenant_a, name='mashina', definition='6 * m3')

        self.assertEqual(
            convert_to_unit('1 mashina', 'm3', tenant_id=self.tenant_a.id),
            Decimal('6'),
        )

        with self.assertRaises(ValidationError):
            convert_to_unit('1 mashina', 'm3', tenant_id=self.tenant_b.id)

    def test_same_name_allowed_in_different_tenants(self):
        """Ikki tashkilot bir nomni turlicha ta'riflashi mumkin."""
        CustomUnit.objects.create(tenant=self.tenant_a, name='mashina', definition='6 * m3')
        CustomUnit.objects.create(tenant=self.tenant_b, name='mashina', definition='10 * m3')

        self.assertEqual(
            convert_to_unit('1 mashina', 'm3', tenant_id=self.tenant_a.id),
            Decimal('6'),
        )
        self.assertEqual(
            convert_to_unit('1 mashina', 'm3', tenant_id=self.tenant_b.id),
            Decimal('10'),
        )

    def test_registry_rebuilds_after_change(self):
        """Birlik o'zgarganda registr qayta quriladi."""
        unit = CustomUnit.objects.create(
            tenant=self.tenant_a, name='mashina', definition='6 * m3'
        )
        self.assertEqual(
            convert_to_unit('1 mashina', 'm3', tenant_id=self.tenant_a.id), Decimal('6')
        )

        unit.definition = '8 * m3'
        unit.save()

        self.assertEqual(
            convert_to_unit('1 mashina', 'm3', tenant_id=self.tenant_a.id), Decimal('8')
        )

    def test_registry_rebuilds_after_delete(self):
        unit = CustomUnit.objects.create(
            tenant=self.tenant_a, name='mashina', definition='6 * m3'
        )
        get_registry(self.tenant_a.id)

        unit.delete()

        with self.assertRaises(ValidationError):
            convert_to_unit('1 mashina', 'm3', tenant_id=self.tenant_a.id)

    def test_tenant_assigned_from_context(self):
        """`TenantOwnedModel.save()` tenantni kontekstdan oladi."""
        with tenant_context(self.tenant_a.id):
            unit = CustomUnit.objects.create(name='mashina', definition='6 * m3')

        self.assertEqual(unit.tenant_id, self.tenant_a.id)

    def tearDown(self):
        invalidate_registry(self.tenant_a.id)
        invalidate_registry(self.tenant_b.id)
