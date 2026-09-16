<script setup lang="ts">
import { computed } from 'vue'

import BarcodeImage from '@/components/BarcodeImage.vue'
import { formatMoney } from '@/utils/money'
import { useAuthStore } from '@/stores/auth'
import type { Sale } from '@/types'

const props = defineProps<{ sale: Sale | null }>()

const auth = useAuthStore()

const shopName = computed(() => auth.shop?.shop_name ?? 'Do‘kon')

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

/**
 * Chekni chop etadi.
 *
 * `body.printing` sinfi qo'yiladi: shunda sahifadagi hamma narsa
 * yashirinadi va faqat `.print-sheet` qog'ozga tushadi (assets/main.css).
 */
function printReceipt() {
  document.body.classList.add('printing')
  window.print()
  document.body.classList.remove('printing')
}

defineExpose({ printReceipt })
</script>

<template>
  <div v-if="sale" class="print-sheet receipt">
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
      <BarcodeImage :value="sale.number" format="CODE128" :height="34" :width="1.3" />
      <small>Qaytarish uchun shu chekni saqlang</small>
    </div>
  </div>
</template>

<style scoped>
.receipt {
  width: 72mm;
  margin: 0 auto;
  font-family: 'Segoe UI', sans-serif;
  font-size: 11px;
  color: #000;
}

.receipt-head {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
  padding-bottom: 6px;
  border-bottom: 1px dashed #000;
  text-align: center;
}

.receipt-head strong {
  font-size: 14px;
}

.receipt-lines {
  width: 100%;
  margin: 6px 0;
  border-collapse: collapse;
}

.receipt-lines td {
  padding: 1px 0;
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
  padding-top: 6px;
  border-top: 1px dashed #000;
}

.receipt-totals > div {
  display: flex;
  justify-content: space-between;
  padding: 1px 0;
}

.receipt-total {
  font-size: 13px;
  font-weight: 700;
}

.receipt-barcode {
  margin-top: 8px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  text-align: center;
}
</style>
