"""Hujjat serializerlari."""

from __future__ import annotations

from decimal import Decimal

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from rest_framework import serializers

from apps.catalog.models import Variant
from apps.documents import services
from apps.documents.models import Document, DocumentLine
from apps.stock.models import Batch


class DocumentLineSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='variant.product.name', read_only=True)
    sku = serializers.CharField(source='variant.sku', read_only=True)
    variant_name = serializers.CharField(source='variant.name', read_only=True)
    base_unit = serializers.CharField(
        source='variant.product.effective_unit', read_only=True
    )
    batch_code = serializers.CharField(source='batch.code', read_only=True, default=None)
    unit_price_base = serializers.DecimalField(
        max_digits=18, decimal_places=2, read_only=True
    )

    class Meta:
        model = DocumentLine
        fields = (
            'id', 'variant', 'product_name', 'variant_name', 'sku',
            'batch', 'batch_code', 'unit', 'base_unit', 'factor',
            'quantity', 'quantity_base', 'unit_price', 'unit_price_base',
            'discount_percent', 'line_total', 'line_cost', 'note', 'position',
        )
        read_only_fields = (
            'id', 'product_name', 'variant_name', 'sku', 'base_unit',
            'batch_code', 'factor', 'quantity_base', 'unit_price_base',
            'line_total', 'line_cost',
        )


class DocumentLineInputSerializer(serializers.Serializer):
    """Hujjat yaratishda kelib tushadigan qator."""

    variant = serializers.IntegerField()
    batch = serializers.IntegerField(required=False, allow_null=True)
    unit = serializers.CharField(required=False, allow_blank=True)
    quantity = serializers.DecimalField(max_digits=18, decimal_places=3)
    unit_price = serializers.DecimalField(max_digits=18, decimal_places=2)
    discount_percent = serializers.DecimalField(
        max_digits=5, decimal_places=2, required=False, default=Decimal('0')
    )
    note = serializers.CharField(required=False, allow_blank=True)


class DocumentSerializer(serializers.ModelSerializer):
    """Hujjat va uning qatorlari.

    Qatorlar hujjat bilan birga bitta so'rovda yuboriladi: yetkazma
    hujjatini yarim tayyor holda saqlash ma'nosiz, u yaxlit narsa.
    """

    lines = DocumentLineSerializer(many=True, read_only=True)
    items = DocumentLineInputSerializer(many=True, write_only=True, required=False)

    kind_display = serializers.CharField(source='get_kind_display', read_only=True)
    status_display = serializers.CharField(source='get_status_display', read_only=True)
    warehouse_name = serializers.CharField(source='warehouse.name', read_only=True)
    partner_name = serializers.CharField(
        source='partner.name', read_only=True, default=None
    )
    profit = serializers.DecimalField(max_digits=18, decimal_places=2, read_only=True)
    is_editable = serializers.BooleanField(read_only=True)
    line_count = serializers.SerializerMethodField()
    payment_method_display = serializers.CharField(
        source='get_payment_method_display', read_only=True
    )
    debt = serializers.SerializerMethodField()

    class Meta:
        model = Document
        fields = (
            'id', 'kind', 'kind_display', 'number', 'date',
            'status', 'status_display', 'is_editable',
            'warehouse', 'warehouse_name', 'partner', 'partner_name',
            'currency', 'external_number', 'note',
            'payment_method', 'payment_method_display',
            'is_credit', 'credit_markup_percent', 'due_date',
            'customer_name', 'customer_phone', 'customer_document', 'debt',
            'total_amount', 'total_cost', 'profit',
            'confirmed_at', 'cancelled_at',
            'lines', 'items', 'line_count',
        )
        read_only_fields = (
            'id', 'number', 'status', 'status_display', 'is_editable',
            'kind_display', 'warehouse_name', 'partner_name',
            'total_amount', 'total_cost', 'profit',
            'confirmed_at', 'cancelled_at', 'lines', 'line_count',
            'payment_method_display', 'debt',
        )

    def get_line_count(self, obj) -> int:
        return obj.lines.count()

    def get_debt(self, obj) -> dict | None:
        """Qarzga sotuvning qarz holati — ro'yxatda belgi va havola uchun."""
        from apps.debts.models import Debt

        try:
            debt = obj.debt
        except Debt.DoesNotExist:
            return None

        return {
            'id': debt.pk,
            'number': debt.number,
            'status': debt.display_status,
            'remaining': str(debt.remaining),
        }

    def validate(self, attrs):
        """Qarzga sotuv va to'lov usuli qoidalari.

        Model `clean()` da ham shunday tekshiruv bor (tasdiqlashda), bu
        yerda esa xato formada darhol, to'g'ri maydon ostida ko'rinsin.
        """
        instance = self.instance

        def current(field, default=None):
            if field in attrs:
                return attrs[field]

            return getattr(instance, field, default) if instance else default

        kind = current('kind')
        is_credit = current('is_credit', False)
        errors = {}

        if is_credit and kind != Document.Kind.SALE:
            errors['is_credit'] = 'Qarzga faqat sotuv qilinadi.'

        if (
            kind == Document.Kind.SALE
            and current('payment_method') == Document.PaymentMethod.DEFERRED
        ):
            errors['payment_method'] = (
                'Sotuvda to‘lovni kechiktirish uchun «Qarzga» belgisini qo‘ying.'
            )

        markup = current('credit_markup_percent') or Decimal('0')

        if markup < 0 or markup > 1000:
            errors['credit_markup_percent'] = 'Ustama 0 dan 1000 % gacha bo‘lishi kerak.'

        if is_credit and not current('partner'):
            name = (current('customer_name', '') or '').strip()
            phone = (current('customer_phone', '') or '').strip()

            if not name or not phone:
                errors['customer_name'] = (
                    'Qarzga sotuvda mijozni tanlang yoki ism va telefonini kiriting.'
                )

        if errors:
            raise serializers.ValidationError(errors)

        return attrs

    #: Summasi kirim narxini ochib beradigan hujjat turlari
    PURCHASE_PRICED_KINDS = frozenset({Document.Kind.PURCHASE, Document.Kind.RETURN_OUT})

    def to_representation(self, instance):
        """Kirim narxini ko'rish ruxsati bo'lmasa, kirim summalarini tozalaydi.

        Umumiy yashirish (`FinancialRedactionMixin`) kalit nomiga qaraydi,
        `total_amount` esa sotuvda tushum, kirimda — xarid narxi. Farqni
        faqat hujjat turi biladi, shuning uchun bu shu yerda.
        """
        data = super().to_representation(instance)

        request = self.context.get('request')
        membership = getattr(request, 'membership', None)

        if membership is None or instance.kind not in self.PURCHASE_PRICED_KINDS:
            return data

        from apps.core.access import Perm

        if membership.has_perm(Perm.VIEW_PURCHASE_PRICE):
            return data

        data['total_amount'] = None

        for line in data.get('lines') or []:
            for key in ('unit_price', 'unit_price_base', 'line_total'):
                line[key] = None

        return data

    @transaction.atomic
    def create(self, validated_data):
        items = validated_data.pop('items', [])
        request = self.context['request']

        document = Document.objects.create(
            **validated_data,
            number=services.next_number(
                request.tenant_id, validated_data['kind'], validated_data.get('date')
            ),
            created_by=request.user,
        )

        self._replace_lines(document, items)

        return services.recalculate_totals(document)

    @transaction.atomic
    def update(self, instance, validated_data):
        items = validated_data.pop('items', None)

        if not instance.is_editable:
            raise serializers.ValidationError({
                'detail': 'Tasdiqlangan hujjatni tahrirlab bo\'lmaydi.'
            })

        for field, value in validated_data.items():
            setattr(instance, field, value)

        instance.save()

        if items is not None:
            self._replace_lines(instance, items)
        elif {'is_credit', 'credit_markup_percent'} & validated_data.keys():
            # Ustama har qator summasiga kiradi — qatorlar qayta hisoblanadi
            for line in instance.lines.all():
                line.document = instance
                line.recalculate()
                line.save(update_fields=['quantity_base', 'line_total', 'updated_at'])

        return services.recalculate_totals(instance)

    def _replace_lines(self, document: Document, items: list) -> None:
        """Qatorlarni butunlay almashtiradi.

        Qisman yangilash (qaysi qator o'zgardi, qaysisi o'chdi) mijoz
        tomonda murakkab holat boshqarishni talab qilardi. Hujjat
        qoralama ekan, qatorlarni qayta yozish arzon va xatosiz.
        """
        document.lines.all().delete()

        for position, item in enumerate(items, start=1):
            try:
                services.build_line(
                    document,
                    variant=Variant.objects.get(pk=item['variant']),
                    quantity=item['quantity'],
                    unit_price=item['unit_price'],
                    unit=item.get('unit', ''),
                    batch=(
                        Batch.objects.get(pk=item['batch'])
                        if item.get('batch')
                        else None
                    ),
                    discount_percent=item.get('discount_percent') or Decimal('0'),
                    note=item.get('note', ''),
                    position=position,
                )
            except DjangoValidationError as exc:
                raise serializers.ValidationError({'items': exc.messages})
            except Variant.DoesNotExist:
                raise serializers.ValidationError({
                    'items': [f'Mahsulot topilmadi: {item["variant"]}']
                })
