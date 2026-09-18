<script setup lang="ts">
import { computed, nextTick, ref } from 'vue'

import BarcodeImage from '@/components/BarcodeImage.vue'
import { formatMoney } from '@/utils/money'
import { printWithPageSize, rememberReceiptHeight } from '@/utils/print'
import { useAuthStore } from '@/stores/auth'
import type { Sale } from '@/types'

const props = defineProps<{ sale: Sale | null }>()

const auth = useAuthStore()

const shopName = computed(() => auth.shop?.shop_name ?? 'Do‘kon')

/** Qog'oz o'lchami — sozlamalardan, drayverdagi qog'oz bilan bir xil */
const pageWidth = computed(() => auth.shop?.receipt_width_mm ?? 80)
const pageHeight = computed(() => auth.shop?.receipt_page_height_mm ?? 110)

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
 * Chekni chop etadi.
 *
 * Sahifa balandligi **qat'iy** va sozlamalardan olinadi. Ilgari u chek
 * mazmuniga qarab hisoblanardi, lekin haqiqiy printerda bu ishlamaydi:
 * Chrome `@page` dagi balandlikni emas, drayverdagi qog'oz o'lchamini
 * oladi. Natijada har chekda 30 sm lenta bo'shga ketardi.
 *
 * Shuning uchun do'kon drayverda maxsus qog'oz yaratadi (masalan
 * 80 × 110 mm) va shu yerga o'sha o'lchamni yozadi.
 *
 * Mazmunning balandligi baribir o'lchanadi — administrator uni
 * Qurilmalarni sinash sahifasida ko'rib, qog'oz balandligini tanlaydi.
 */
async function printReceipt() {
  // Chek hozirgina yaratilgan bo'lsa, Vue DOM ni hali yangilamagan
  await nextTick()

  const element = sheet.value

  if (element) {
    rememberReceiptHeight((element.scrollHeight / 96) * 25.4)
  }

  printWithPageSize(`@page { size: ${pageWidth.value}mm ${pageHeight.value}mm; margin: 0; }`)
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
        <!-- Har mahsulot uchun alohida `tbody`: nomi va summasi bitta
             bo'lak bo'lib qoladi va sahifa ular orasidan uzilmaydi -->
        <tbody v-for="line in sale.lines" :key="line.id" class="receipt-line">
          <tr>
            <td colspan="2" class="receipt-name">
              {{ line.product_name }}
              <template v-if="line.variant_label"> · {{ line.variant_label }}</template>
            </td>
          </tr>
          <tr>
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

   Kenglik ham millimetrda: XP-80 da bosiladigan en 72 mm, qog'oz esa
   80 mm. `margin: 0 auto` mazmunni gorizontal markazga qo'yadi;
   vertikal markazlash yo'q — chek doim qog'oz tepasidan boshlanadi. */
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

  break-inside: avoid;
  page-break-inside: avoid;
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

/* Mahsulot nomi va uning summasi hech qachon ikki sahifaga bo'linmaydi */
.receipt-line {
  break-inside: avoid;
  page-break-inside: avoid;
}

.receipt-name {
  font-weight: 600;
}

.receipt-sum {
  text-align: right;
  white-space: nowrap;
}

/* Jami blokini oxirgi qatordan ajratmaslikka harakat qilinadi */
.receipt-totals {
  padding-top: 2mm;
  border-top: 1px dashed #000;

  break-inside: avoid;
  page-break-inside: avoid;
  break-before: avoid;
  page-break-before: avoid;
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

  break-inside: avoid;
  page-break-inside: avoid;
}

/* `small` odatda 0.8em bo'lib 2 mm dan kichik chiqardi */
.receipt-barcode small {
  font-size: 3mm;
}
</style>
