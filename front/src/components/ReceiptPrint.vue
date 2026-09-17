<script setup lang="ts">
import { computed, nextTick, ref } from 'vue'

import BarcodeImage from '@/components/BarcodeImage.vue'
import { formatMoney } from '@/utils/money'
import { printWithPageSize } from '@/utils/print'
import { useAuthStore } from '@/stores/auth'
import type { Sale } from '@/types'

const props = defineProps<{ sale: Sale | null }>()

const auth = useAuthStore()

const shopName = computed(() => auth.shop?.shop_name ?? 'Do‘kon')

/**
 * Chekdagi shtrix-kod faqat raqamdan iborat: 'SOT-2026-000001' dagi
 * harflarni skaner klaviatura tiliga qarab boshqacha yozib yuborardi.
 */
const barcodeValue = computed(() => (props.sale?.number ?? '').replace(/\D/g, ''))

const printedAt = computed(() => {
  if (!props.sale) return ''

  return new Date(props.sale.created_at).toLocaleString('uz-UZ', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
})

const sheet = ref<HTMLElement | null>(null)

/**
 * Chekni chop etadi: 80 mm lenta, bo'yi chek mazmuniga qarab.
 *
 * `size: 80mm auto` deb yozib bo'lmaydi — CSS uzunlik bilan `auto` ni
 * aralashtirishga ruxsat bermaydi va brauzer butun qoidani tashlab
 * yuboradi (natijada A4/Letter qog'oz chiqadi). Shuning uchun balandlik
 * chekning o'zidan o'lchanadi: ekranda 96px = 25.4 mm.
 */
async function printReceipt() {
  // Chek hozirgina yaratilgan bo'lsa (kassada «Yakunlash»), Vue DOM ni
  // hali yangilamagan bo'ladi va varaq mavjud emas. O'lchashdan oldin
  // shuni kutamiz — aks holda balandlik topilmay, chek oxirida uzun
  // bo'sh lenta chiqib ketadi.
  await nextTick()

  const element = sheet.value
  const heightMm = element ? Math.ceil((element.scrollHeight / 96) * 25.4) + 6 : 120

  printWithPageSize(`@page { size: 80mm ${heightMm}mm; margin: 0; }`)
}

defineExpose({ printReceipt })
</script>

<template>
  <!-- Varaq <body> ga chiqariladi — izoh: assets/main.css -->
  <Teleport to="body">
    <div v-if="sale" ref="sheet" class="print-sheet receipt">
    <div class="receipt-head">
      <strong>{{ shopName }}</strong>
      <span>{{ printedAt }}</span>
      <span>Chek: {{ sale.number }}</span>
      <span>Kassir: {{ sale.cashier_name ?? '—' }}</span>
    </div>

    <table class="receipt-lines">
      <tbody>
        <tr v-for="line in sale.lines" :key="line.id">
          <td colspan="2" class="receipt-name">
            {{ line.product_name }}
            <template v-if="line.variant_label"> · {{ line.variant_label }}</template>
          </td>
        </tr>
        <tr v-for="line in sale.lines" :key="`sum-${line.id}`">
          <td>{{ line.quantity }} × {{ formatMoney(line.unit_price) }}</td>
          <td class="receipt-sum">{{ formatMoney(line.line_total) }}</td>
        </tr>
      </tbody>
    </table>

    <div class="receipt-totals">
      <div v-if="sale.discount_total !== '0.00'">
        <span>Chegirma</span>
        <span>{{ formatMoney(sale.discount_total) }}</span>
      </div>

      <div class="receipt-total">
        <span>JAMI</span>
        <span>{{ formatMoney(sale.total) }}</span>
      </div>

      <div v-if="sale.cash_amount !== '0.00'">
        <span>Naqd</span>
        <span>{{ formatMoney(sale.cash_amount) }}</span>
      </div>

      <div v-if="sale.card_amount !== '0.00'">
        <span>Karta</span>
        <span>{{ formatMoney(sale.card_amount) }}</span>
      </div>
    </div>

    <div class="receipt-barcode">
      <!-- 72 mm bosiladigan enda 27.5 mm kod bemalol joylashadi -->
      <BarcodeImage :value="barcodeValue" format="CODE128" :height-mm="15" :text-mm="3" />
        <small>Qaytarish uchun shu chekni saqlang</small>
      </div>
    </div>
  </Teleport>
</template>

<style scoped>
/* Shrift o'lchamlari MILLIMETRDA berilgan — ataylab.
   Qonun talabi: chekdagi belgilar balandligi kamida 2 mm.
   3 mm shriftda bosh harf balandligi ~2.1 mm, ya'ni talab bajariladi.
   `px` da yozilsa, chek printerining zichligiga (203 dpi) qarab
   o'lcham suzib ketardi; `mm` esa qog'ozdagi haqiqiy o'lchamni beradi. */
.receipt {
  width: 72mm;
  margin: 0 auto;
  padding: 3mm 0;
  font-family: 'Segoe UI', sans-serif;
  font-size: 3mm;
  line-height: 1.3;
  color: #000;
}

.receipt-head {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.5mm;
  padding-bottom: 2mm;
  border-bottom: 1px dashed #000;
  text-align: center;
}

.receipt-head strong {
  font-size: 4.5mm;
}

.receipt-lines {
  width: 100%;
  margin: 2mm 0;
  border-collapse: collapse;
}

.receipt-lines td {
  padding: 0.3mm 0;
  vertical-align: top;
}

.receipt-name {
  font-weight: 600;
}

.receipt-sum {
  text-align: right;
  white-space: nowrap;
}

.receipt-totals {
  padding-top: 2mm;
  border-top: 1px dashed #000;
}

.receipt-totals > div {
  display: flex;
  justify-content: space-between;
  padding: 0.3mm 0;
}

.receipt-total {
  font-size: 4mm;
  font-weight: 700;
}

.receipt-barcode {
  margin-top: 3mm;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 1mm;
  text-align: center;
}

/* `small` odatda 0.8em bo'lib 2 mm dan kichik chiqardi */
.receipt-barcode small {
  font-size: 3mm;
}
</style>
