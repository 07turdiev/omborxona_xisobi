<script setup lang="ts">
import { computed } from 'vue'

import { useAuthStore } from '@/stores/auth'
import type { Document, TenantSettings } from '@/types'

const props = defineProps<{
  show: boolean
  document: Document | null
  settings: TenantSettings | null
}>()
const emit = defineEmits<{ close: [] }>()

const auth = useAuthStore()

const isPurchase = computed(() => props.document?.kind === 'purchase')

const companyName = computed(
  () => props.settings?.name ?? auth.user?.current_tenant?.tenant_name ?? '',
)

function money(value: string | null | undefined): string {
  if (value == null) return '—'
  return new Intl.NumberFormat('uz-UZ', { maximumFractionDigits: 0 }).format(Number(value))
}

function number(value: string): string {
  return new Intl.NumberFormat('uz-UZ', { maximumFractionDigits: 3 }).format(Number(value))
}

/**
 * Brauzerning chop etish oynasini ochadi.
 *
 * Nima uchun serverda PDF emas: bu yechim **har qanday printerda**
 * ishlaydi — A4 lazerdan tortib termal chek printerigacha, chunki
 * qog'oz o'lchamini va masshtabni brauzer dialogi hal qiladi. Server
 * tomonda PDF chiqarish (weasyprint) aniqroq nazorat beradi, lekin
 * printer turini oldindan bilishni talab qiladi.
 */
function onPrint() {
  // `body.printing` global chop etish qoidalarini yoqadi
  // (`src/assets/main.css`). Chop etishdan keyin darhol olib
  // tashlanadi — aks holda qoidalar keyingi chop etishlarda ham
  // qolib ketardi.
  document.body.classList.add('printing')

  window.print()

  document.body.classList.remove('printing')
}
</script>

<template>
  <div class="modal print-modal" :class="{ show }">
    <div class="modal-backdrop no-print" @click="emit('close')"></div>

    <div class="modal-dialog modal-large print-dialog">
      <div class="modal-header no-print">
        <div>
          <span class="modal-eyebrow">CHOP ETISH</span>
          <h3>{{ document?.number }}</h3>
          <p>Chop etish oynasida qog‘oz o‘lchamini tanlang.</p>
        </div>

        <button class="modal-close" type="button" @click="emit('close')">
          <svg><use href="#i-close" /></svg>
        </button>
      </div>

      <!-- Chop etiladigan qism -->
      <div v-if="document" class="print-sheet">
        <header class="sheet-head">
          <div>
            <strong class="company">{{ companyName }}</strong>
            <div v-if="settings?.inn" class="company-line">INN: {{ settings.inn }}</div>
            <div v-if="settings?.address" class="company-line">{{ settings.address }}</div>
            <div v-if="settings?.phone" class="company-line">{{ settings.phone }}</div>
          </div>

          <div class="doc-meta">
            <strong>{{ document.kind_display }}</strong>
            <div class="doc-number">{{ document.number }}</div>
            <div>{{ document.date }}</div>
            <div v-if="document.external_number" class="company-line">
              Tashqi hujjat: {{ document.external_number }}
            </div>
          </div>
        </header>

        <div class="parties">
          <div>
            <span>Ombor</span>
            <strong>{{ document.warehouse_name }}</strong>
          </div>

          <div>
            <span>{{ isPurchase ? 'Yetkazib beruvchi' : 'Mijoz' }}</span>
            <strong>{{ document.partner_name || '—' }}</strong>
          </div>
        </div>

        <table class="sheet-table">
          <thead>
            <tr>
              <th class="idx">№</th>
              <th>Mahsulot</th>
              <th class="num">Miqdor</th>
              <th class="num">Narx</th>
              <th class="num">Chegirma</th>
              <th class="num">Summa</th>
            </tr>
          </thead>

          <tbody>
            <tr v-for="(line, index) in document.lines" :key="line.id">
              <td class="idx">{{ index + 1 }}</td>

              <td>
                {{ line.product_name }}
                <small v-if="line.variant_name">{{ line.variant_name }}</small>
                <small class="sku">{{ line.sku }}</small>
              </td>

              <td class="num">
                {{ number(line.quantity) }} {{ line.unit }}
                <small v-if="line.unit !== line.base_unit">
                  = {{ number(line.quantity_base) }} {{ line.base_unit }}
                </small>
              </td>

              <td class="num">{{ money(line.unit_price) }}</td>

              <td class="num">
                {{ Number(line.discount_percent) > 0 ? `${line.discount_percent}%` : '—' }}
              </td>

              <td class="num strong">{{ money(line.line_total) }}</td>
            </tr>
          </tbody>

          <tfoot>
            <tr>
              <td colspan="5" class="total-label">Jami</td>
              <td class="num total">{{ money(document.total_amount) }}</td>
            </tr>
          </tfoot>
        </table>

        <p v-if="document.note" class="sheet-note">{{ document.note }}</p>

        <footer class="sheet-foot">
          <div class="sign">
            <span>Topshirdi</span>
            <i></i>
          </div>

          <div class="sign">
            <span>Qabul qildi</span>
            <i></i>
          </div>
        </footer>
      </div>

      <div class="modal-footer no-print">
        <button class="button button-outline" type="button" @click="emit('close')">
          Yopish
        </button>

        <button class="button button-gradient" type="button" @click="onPrint">
          <svg><use href="#i-print" /></svg>
          <span>Chop etish</span>
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.print-dialog {
  max-height: 90vh;
  overflow-y: auto;
}

.print-sheet {
  padding: 24px 26px;
  background: #fff;
  color: #111;
}

.sheet-head {
  display: flex;
  justify-content: space-between;
  gap: 20px;
  padding-bottom: 14px;
  border-bottom: 2px solid #111;
}

.company {
  display: block;
  font-size: 18px;
}

.company-line {
  margin-top: 2px;
  font-size: 13px;
  color: #555;
}

.doc-meta {
  text-align: right;
  font-size: 13px;
}

.doc-meta strong {
  display: block;
  font-size: 16px;
}

.doc-number {
  margin-top: 2px;
  font-size: 15px;
  font-weight: 700;
}

.parties {
  display: flex;
  gap: 30px;
  margin: 14px 0;
}

.parties span {
  display: block;
  color: #666;
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.parties strong {
  display: block;
  margin-top: 2px;
  font-size: 14px;
}

.sheet-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}

.sheet-table th {
  padding: 6px 7px;
  border-bottom: 1px solid #111;
  color: #333;
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  text-align: left;
}

.sheet-table td {
  padding: 6px 7px;
  border-bottom: 1px solid #ddd;
  vertical-align: top;
}

.sheet-table small {
  display: block;
  margin-top: 1px;
  color: #777;
  font-size: 11px;
}

.sheet-table .sku {
  color: #999;
}

.idx {
  width: 24px;
  color: #888;
}

.num {
  text-align: right;
  white-space: nowrap;
}

.strong {
  font-weight: 700;
}

.total-label {
  padding-top: 10px;
  text-align: right;
  font-size: 14px;
  font-weight: 700;
}

.total {
  padding-top: 10px;
  font-size: 16px;
  font-weight: 700;
}

.sheet-note {
  margin-top: 12px;
  color: #555;
  font-size: 13px;
}

.sheet-foot {
  display: flex;
  justify-content: space-between;
  gap: 40px;
  margin-top: 34px;
}

.sign {
  flex: 1;
}

.sign span {
  display: block;
  color: #666;
  font-size: 12px;
}

.sign i {
  display: block;
  margin-top: 22px;
  border-bottom: 1px solid #111;
}

/* Chop etishda faqat hujjat qoladi: modal oynasi, fon va tugmalar
   yashiriladi, varaq esa butun sahifani egallaydi. */
@media print {
  .no-print {
    display: none !important;
  }

  .print-modal {
    position: static;
    padding: 0;
    opacity: 1;
    visibility: visible;
  }

  .print-dialog {
    max-width: none;
    max-height: none;
    overflow: visible;
    box-shadow: none;
    border-radius: 0;
  }

  .print-sheet {
    padding: 0;
  }
}
</style>
