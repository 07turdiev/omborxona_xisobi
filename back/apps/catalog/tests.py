"""Katalog testlari: ltree daraxti, atribut merosi, o'ram konversiyasi."""

from __future__ import annotations

from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase

from apps.catalog.attributes import (
    build_attributes,
    definitions_for,
    normalize_value,
    validate_uniqueness,
)
from apps.catalog.models import (
    AttributeDefinition,
    Barcode,
    Category,
    Product,
    ProductUnit,
    Variant,
)
from apps.core.tenancy import tenant_context
from apps.tenants.models import Tenant


class CategoryTreeTests(TestCase):
    """`ltree` daraxti — 4-arxitektura qarori."""

    @classmethod
    def setUpTestData(cls):
        cls.tenant = Tenant.objects.create(name='Do\'kon', slug='cat-tree')

    def setUp(self):
        self.ctx = tenant_context(self.tenant.id)
        self.ctx.__enter__()

        self.root = Category.objects.create(tenant=self.tenant, name='Qurilish')
        self.cement = Category.objects.create(
            tenant=self.tenant, name='Sement', parent=self.root
        )
        self.portland = Category.objects.create(
            tenant=self.tenant, name='Portlandsement', parent=self.cement
        )

    def tearDown(self):
        self.ctx.__exit__(None, None, None)

    def test_path_built_from_ids(self):
        """Yo'l ID lardan quriladi — nom o'zgarsa buzilmaydi."""
        self.assertEqual(self.root.path, f'c{self.root.pk}')
        self.assertEqual(self.cement.path, f'c{self.root.pk}.c{self.cement.pk}')
        self.assertEqual(
            self.portland.path,
            f'c{self.root.pk}.c{self.cement.pk}.c{self.portland.pk}',
        )

    def test_rename_does_not_change_path(self):
        old_path = self.cement.path

        self.cement.name = 'Sement va aralashmalar'
        self.cement.save()

        self.assertEqual(self.cement.path, old_path)

    def test_ancestors_ordered_from_root(self):
        names = list(self.portland.ancestors().values_list('name', flat=True))
        self.assertEqual(names, ['Qurilish', 'Sement', 'Portlandsement'])

        names = list(
            self.portland.ancestors(include_self=False).values_list('name', flat=True)
        )
        self.assertEqual(names, ['Qurilish', 'Sement'])

    def test_descendants(self):
        names = set(self.root.descendants().values_list('name', flat=True))
        self.assertEqual(names, {'Sement', 'Portlandsement'})

    def test_depth(self):
        self.assertEqual(self.root.depth, 1)
        self.assertEqual(self.portland.depth, 3)

    def test_moving_subtree_updates_all_descendants(self):
        """Ota o'zgarganda butun ostki daraxt ko'chadi."""
        other_root = Category.objects.create(tenant=self.tenant, name='Boshqa')

        self.cement.parent = other_root
        self.cement.save()

        self.cement.refresh_from_db()
        self.portland.refresh_from_db()

        self.assertEqual(self.cement.path, f'c{other_root.pk}.c{self.cement.pk}')
        self.assertEqual(
            self.portland.path,
            f'c{other_root.pk}.c{self.cement.pk}.c{self.portland.pk}',
        )
        self.assertEqual(
            list(other_root.descendants().values_list('name', flat=True)),
            ['Sement', 'Portlandsement'],
        )

    def test_cannot_move_category_into_own_subtree(self):
        self.root.parent = self.portland

        with self.assertRaises(ValidationError):
            self.root.clean()


class AttributeInheritanceTests(TestCase):
    """Atributlarning kategoriya bo'ylab jonli merosi — 2-qaror."""

    @classmethod
    def setUpTestData(cls):
        cls.tenant = Tenant.objects.create(name='Do\'kon', slug='cat-attr')

    def setUp(self):
        self.ctx = tenant_context(self.tenant.id)
        self.ctx.__enter__()

        self.root = Category.objects.create(tenant=self.tenant, name='Qurilish')
        self.child = Category.objects.create(
            tenant=self.tenant, name='Sement', parent=self.root
        )

        AttributeDefinition.objects.create(
            tenant=self.tenant, category=self.root,
            key='ishlab_chiqaruvchi', name='Ishlab chiqaruvchi', position=1,
        )
        AttributeDefinition.objects.create(
            tenant=self.tenant, category=self.child,
            key='marka', name='Marka', position=2,
        )

    def tearDown(self):
        self.ctx.__exit__(None, None, None)

    def test_child_inherits_parent_definitions(self):
        keys = [d.key for d in definitions_for(self.child)]
        self.assertEqual(keys, ['ishlab_chiqaruvchi', 'marka'])

    def test_parent_does_not_see_child_definitions(self):
        keys = [d.key for d in definitions_for(self.root)]
        self.assertEqual(keys, ['ishlab_chiqaruvchi'])

    def test_deeper_definition_overrides_shallower(self):
        """Bir xil kalit ikki darajada bo'lsa, chuqurrog'i ustun."""
        AttributeDefinition.objects.create(
            tenant=self.tenant, category=self.child,
            key='ishlab_chiqaruvchi', name='Zavod', position=1,
        )

        definitions = {d.key: d for d in definitions_for(self.child)}
        self.assertEqual(definitions['ishlab_chiqaruvchi'].name, 'Zavod')

    def test_new_definition_appears_immediately(self):
        """Jonli meros: kategoriyaga atribut qo'shilsa darhol ko'rinadi.

        InvenTree bu yerda boshqacha ishlaydi — u default qiymatlarni
        mahsulot yaratilganda nusxalaydi (part/models.py:2349), shuning
        uchun keyin qo'shilgan atribut eski mahsulotlarda paydo bo'lmaydi.
        """
        before = len(definitions_for(self.child))

        AttributeDefinition.objects.create(
            tenant=self.tenant, category=self.root,
            key='qadoq', name='Qadoq', position=3,
        )

        self.assertEqual(len(definitions_for(self.child)), before + 1)


class AttributeValueTests(TestCase):
    """Qiymatlarning `{raw, num}` juftligi sifatida saqlanishi."""

    @classmethod
    def setUpTestData(cls):
        cls.tenant = Tenant.objects.create(name='Do\'kon', slug='cat-val')

    def setUp(self):
        self.ctx = tenant_context(self.tenant.id)
        self.ctx.__enter__()

        self.category = Category.objects.create(tenant=self.tenant, name='Profil')

        self.thickness = AttributeDefinition.objects.create(
            tenant=self.tenant, category=self.category,
            key='qalinlik', name='Qalinlik',
            value_type=AttributeDefinition.ValueType.NUMBER, unit='mm',
        )
        self.material = AttributeDefinition.objects.create(
            tenant=self.tenant, category=self.category,
            key='material', name='Material',
            value_type=AttributeDefinition.ValueType.CHOICE,
            choices=['Yog\'och', 'Metall'],
        )

    def tearDown(self):
        self.ctx.__exit__(None, None, None)

    def test_number_stored_with_normalized_value(self):
        entry = normalize_value(self.thickness, '12 mm')

        self.assertEqual(entry['raw'], '12 mm')
        self.assertEqual(Decimal(entry['num']), Decimal('0.012'))

    def test_equivalent_values_normalize_equal(self):
        """"10 mm" va "1 sm" bir xil songa keltiriladi.

        Busiz JSONB bo'yicha sonli filtrlash ishlamaydi.
        """
        a = normalize_value(self.thickness, '10 mm')
        b = normalize_value(self.thickness, '1 cm')

        self.assertEqual(Decimal(a['num']), Decimal(b['num']))
        self.assertNotEqual(a['raw'], b['raw'])

    def test_bare_number_takes_definition_unit(self):
        entry = normalize_value(self.thickness, '12')
        self.assertEqual(Decimal(entry['num']), Decimal('0.012'))

    def test_num_is_string_not_float(self):
        """6-qaror: `Decimal` aniqligi saqlanishi uchun satr sifatida."""
        entry = normalize_value(self.thickness, '0.1 mm')
        self.assertIsInstance(entry['num'], str)

    def test_text_attribute_has_no_num(self):
        entry = normalize_value(self.material, 'Yog\'och')

        self.assertEqual(entry['raw'], 'Yog\'och')
        self.assertIsNone(entry['num'])

    def test_unparseable_number_rejected(self):
        with self.assertRaises(ValidationError):
            normalize_value(self.thickness, 'yo\'g\'on')

    def test_invalid_choice_rejected(self):
        with self.assertRaises(ValidationError):
            build_attributes(self.category, {'material': 'Plastik', 'qalinlik': '1 mm'})

    def test_required_attribute_enforced(self):
        self.thickness.is_required = True
        self.thickness.save()

        with self.assertRaises(ValidationError):
            build_attributes(self.category, {'material': 'Metall'})

    def test_unknown_keys_are_dropped(self):
        """Ta'rifda yo'q kalit jimgina tashlanadi."""
        result = build_attributes(
            self.category, {'qalinlik': '5 mm', 'begona': 'qiymat'}
        )

        self.assertIn('qalinlik', result)
        self.assertNotIn('begona', result)

    def test_uniqueness_detects_equivalent_values(self):
        """"1000 mm" va "1 m" dublikat deb topiladi.

        Manba g'oyasi: InvenTree common/models.py:2949 (MIT).
        """
        self.thickness.uniqueness = AttributeDefinition.Uniqueness.TENANT
        self.thickness.save()

        product = Product.objects.create(
            tenant=self.tenant, category=self.category, name='Profil A'
        )
        Variant.objects.create(
            tenant=self.tenant, product=product, sku='A-1',
            attributes=build_attributes(self.category, {'qalinlik': '1000 mm'}),
        )

        new_variant = Variant(tenant=self.tenant, product=product, sku='A-2')
        attributes = build_attributes(self.category, {'qalinlik': '1 m'})

        with self.assertRaises(ValidationError):
            validate_uniqueness(new_variant, self.category, attributes)


class ProductUnitTests(TestCase):
    """«1 qop = 50 kg» — mahsulotga bog'liq konversiya."""

    @classmethod
    def setUpTestData(cls):
        cls.tenant = Tenant.objects.create(name='Do\'kon', slug='cat-unit')

    def setUp(self):
        self.ctx = tenant_context(self.tenant.id)
        self.ctx.__enter__()

        self.category = Category.objects.create(
            tenant=self.tenant, name='Sement', default_unit='kg'
        )

    def tearDown(self):
        self.ctx.__exit__(None, None, None)

    def make_variant(self, name, sku):
        product = Product.objects.create(
            tenant=self.tenant, category=self.category, name=name
        )
        return Variant.objects.create(tenant=self.tenant, product=product, sku=sku)

    def test_pack_conversion_is_per_product(self):
        """Sement qopi 50 kg, gips qopi 30 kg — global bo'lolmaydi."""
        cement = self.make_variant('Portlandsement M400', 'CEM-1')
        gypsum = self.make_variant('Gips', 'GYP-1')

        cement_bag = ProductUnit.objects.create(
            tenant=self.tenant, variant=cement, unit='qop',
            factor_to_base=Decimal('50'),
        )
        gypsum_bag = ProductUnit.objects.create(
            tenant=self.tenant, variant=gypsum, unit='qop',
            factor_to_base=Decimal('30'),
        )

        self.assertEqual(cement_bag.to_base(Decimal('3')), Decimal('150'))
        self.assertEqual(gypsum_bag.to_base(Decimal('3')), Decimal('90'))

    def test_multiple_packs_per_variant(self):
        """Bir mahsulotda bir nechta o'ram: qop, palet, tonna."""
        cement = self.make_variant('Portlandsement M400', 'CEM-2')

        for unit, factor in [('qop', '50'), ('palet', '1500'), ('tonna', '1000')]:
            ProductUnit.objects.create(
                tenant=self.tenant, variant=cement, unit=unit,
                factor_to_base=Decimal(factor),
            )

        self.assertEqual(cement.units.count(), 3)

        palet = cement.units.get(unit='palet')
        self.assertEqual(palet.to_base(Decimal('2')), Decimal('3000'))
        self.assertEqual(palet.from_base(Decimal('3000')), Decimal('2'))

    def test_product_inherits_unit_from_category(self):
        cement = self.make_variant('Portlandsement M400', 'CEM-3')
        self.assertEqual(cement.product.effective_unit, 'kg')

    def test_negative_factor_rejected(self):
        cement = self.make_variant('Portlandsement M400', 'CEM-4')

        unit = ProductUnit(
            tenant=self.tenant, variant=cement, unit='qop',
            factor_to_base=Decimal('-1'),
        )

        with self.assertRaises(ValidationError):
            unit.full_clean()


class BarcodeTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.tenant = Tenant.objects.create(name='Do\'kon', slug='cat-bar')

    def setUp(self):
        self.ctx = tenant_context(self.tenant.id)
        self.ctx.__enter__()

        category = Category.objects.create(tenant=self.tenant, name='Tovar')
        product = Product.objects.create(
            tenant=self.tenant, category=category, name='Tovar A'
        )
        self.variant = Variant.objects.create(
            tenant=self.tenant, product=product, sku='A-1'
        )

    def tearDown(self):
        self.ctx.__exit__(None, None, None)

    def test_multiple_barcodes_per_variant(self):
        """InvenTree da bir obyektga bitta kod, bizda bir nechta."""
        for code in ['4780012345678', 'INT-001']:
            Barcode.objects.create(tenant=self.tenant, variant=self.variant, code=code)

        self.assertEqual(self.variant.barcodes.count(), 2)

    def test_code_is_normalized_for_search(self):
        """Skaner qo'shgan bo'shliq va registr qidiruvni buzmasligi kerak."""
        barcode = Barcode.objects.create(
            tenant=self.tenant, variant=self.variant, code='  int-001  '
        )

        self.assertEqual(barcode.code, 'int-001')
        self.assertEqual(barcode.code_normalized, 'INT-001')

        found = Barcode.objects.filter(
            code_normalized=Barcode.normalize(' Int-001 ')
        ).first()
        self.assertEqual(found, barcode)


class CatalogIsolationTests(TestCase):
    """Katalog ham RLS bilan himoyalanganini qotiradi."""

    @classmethod
    def setUpTestData(cls):
        cls.tenant_a = Tenant.objects.create(name='A', slug='cat-iso-a')
        cls.tenant_b = Tenant.objects.create(name='B', slug='cat-iso-b')

    def test_categories_are_isolated(self):
        with tenant_context(self.tenant_a.id):
            Category.objects.create(tenant=self.tenant_a, name='A kategoriya')

        with tenant_context(self.tenant_b.id):
            Category.objects.create(tenant=self.tenant_b, name='B kategoriya')

        with tenant_context(self.tenant_a.id):
            self.assertEqual(
                list(Category.objects.values_list('name', flat=True)), ['A kategoriya']
            )

    def test_same_sku_allowed_in_different_tenants(self):
        for tenant in (self.tenant_a, self.tenant_b):
            with tenant_context(tenant.id):
                category = Category.objects.create(tenant=tenant, name='Tovar')
                product = Product.objects.create(
                    tenant=tenant, category=category, name='Tovar'
                )
                Variant.objects.create(tenant=tenant, product=product, sku='SKU-1')

        with tenant_context(self.tenant_a.id):
            self.assertEqual(Variant.objects.count(), 1)
