<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'

import ScanField from '@/components/ScanField.vue'
import { catalogApi } from '@/api/catalog'
import { errorMessage } from '@/api/client'
import { salesApi } from '@/api/sales'
import { addMoney, compareMoney, formatMoney, formatSum, multiplyMoney, subtractMoney } from '@/utils/money'
import { uuid } from '@/utils/uuid'
import type { Sale, Variant } from '@/types'

const route = useRoute()
const scanner = ref<InstanceType<typeof ScanField> | null>(null)

const sale = ref<Sale | null>(null)
const error = ref('')
const notice = ref('')
const saving = ref(false)

/** Qaytariladigan miqdorlar: chek qatori → dona */
const returning = ref<Record<number, number>>({})

/** Almashtirishda beriladigan yangi tovarlar */
const exchangeLines = ref<{ variant: Variant; quantity: number }[]>([])

const method = ref<'cash' | 'card'>('cash')
const requestKey = ref(uuid())

const refundTotal = computed(() =>
  (sale.value?.lines ?? []).reduce((sum, line) => {
    const quantity = returning.value[line.id] ?? 0

    if (!quantity) return sum

    const perUnit = line.quantity ? divide(line.line_total, line.quantity) : '0'

    return addMoney(sum, multiplyMoney(perUnit, quantity))
  }, '0'),
)

const exchangeTotal = computed(() =>
  exchangeLines.value.reduce(
    (sum, item) => addMoney(sum, multiplyMoney(item.variant.price, item.quantity)),
    '0',
  ),
)

/** Musbat — mijozdan olinadi, manfiy — mijozga qaytariladi. */
const difference = computed(() => subtractMoney(exchangeTotal.value, refundTotal.value))

const hasReturn = computed(() => Object.values(returning.value).some((value) => value > 0))
const isExchange = computed(() => exchangeLines.value.length > 0)

/** Pulni butun songa bo'ladi (tiyingacha). */
function divide(value: string, count: number): string {
  const cents = BigInt(value.replace('.', '').replace('-', ''))
  const part = cents / BigInt(count)

  return `${part / 100n}.${(part % 100n).toString().padStart(2, '0')}`
}

function reset() {
  sale.value = null
  returning.value = {}
  exchangeLines.value = []
  requestKey.value = uuid()
  method.value = 'cash'
}

/** Chek raqami yoki chekdagi shtrix-kod. */
async function onScanReceipt(code: string) {
  error.value = ''
  notice.value = ''

  try {
    const found = await salesApi.byNumber(code)

    if (!found) {
      error.value = `«${code}» — bunday chek topilmadi.`
      return
    }

    if (found.status === 'voided') {
      error.value = `${found.number} — bekor qilingan chek.`
      return
    }

    sale.value = found
    returning.value = {}
    exchangeLines.value = []
    requestKey.value = uuid()
  } catch (err) {
    error.value = errorMessage(err, 'Chekni topib bo‘lmadi.')
  } finally {
    scanner.value?.focus()
  }
}

/** Almashtirish uchun yangi tovar skanerlanadi. */
async function onScanProduct(code: string) {
  error.value = ''

  try {
    const variant = await catalogApi.byBarcode(code)
    const existing = exchangeLines.value.find((item) => item.variant.id === variant.id)

    if (existing) {
      if (existing.quantity + 1 > variant.stock_quantity) {
        error.value = `Omborda ${variant.stock_quantity} dona qolgan.`
        return
      }

      existing.quantity += 1
    } else {
      if (variant.stock_quantity < 1) {
        error.value = `${variant.product_name} — omborda qolmagan.`
        return
      }

      exchangeLines.value.push({ variant, quantity: 1 })
    }
  } catch (err) {
    error.value = errorMessage(err, `«${code}» — bunday shtrix-kod topilmadi.`)
  } finally {
    scanner.value?.focus()
  }
}

function maxReturn(lineId: number): number {
  const line = sale.value?.lines.find((item) => item.id === lineId)

  return line ? line.quantity - line.returned_quantity : 0
}

async function onSubmit() {
  if (!sale.value || !hasReturn.value || saving.value) return

  error.value = ''
  notice.value = ''
  saving.value = true

  const items = Object.entries(returning.value)
    .filter(([, quantity]) => quantity > 0)
    .map(([lineId, quantity]) => ({ sale_line: Number(lineId), quantity }))

  try {
    if (isExchange.value) {
      const result = await salesApi.exchange({
        sale: sale.value.id,
        items,
        lines: exchangeLines.value.map((item) => ({
          variant: item.variant.id,
          quantity: item.quantity,
          unit_price: item.variant.price,
        })),
        refund_method: method.value,
        // Farq bitta usulda: qaytarish ham, yangi sotuv ham shu usulda
        cash_amount: method.value === 'cash' ? exchangeTotal.value : '0',
        card_amount: method.value === 'card' ? exchangeTotal.value : '0',
        request_key: requestKey.value,
      })

      notice.value =
        compareMoney(result.difference, '0') >= 0
          ? `Almashtirildi. Mijozdan oling: ${formatSum(result.difference)}`
          : `Almashtirildi. Mijozga qaytaring: ${formatSum(result.difference.replace('-', ''))}`
    } else {
      const result = await salesApi.createReturn({
        sale: sale.value.id,
        items,
        refund_method: method.value,
        request_key: requestKey.value,
      })

      notice.value = `${result.number} — mijozga qaytaring: ${formatSum(result.total)}`
    }

    reset()
  } catch (err) {
    error.value = errorMessage(err, 'Qaytarishni yakunlab bo‘lmadi.')
  } finally {
    saving.value = false
    scanner.value?.focus()
  }
}

/** Cheklar sahifasidan kelingan bo'lsa (`?number=SOT-…`) — chek darhol ochiladi */
onMounted(() => {
  const number = String(route.query.number ?? '').trim()

  if (number) void onScanReceipt(number)
})
</script>

<template>
  <section class="app-section active">
    <div class="returns-head">
      <ScanField
        ref="scanner"
        :placeholder="sale ? 'Almashtirish uchun tovarni skanerlang' : 'Chek raqamini skanerlang yoki kiriting'"
        @scan="sale ? onScanProduct($event) : onScanReceipt($event)"
      />

      <button v-if="sale" class="button button-outline" type="button" @click="reset">
        Boshqa chek
      </button>
    </div>

    <p v-if="error" class="load-error" role="alert">{{ error }}</p>
    <p v-if="notice" class="notice success-notice">{{ notice }}</p>

    <p v-if="!sale" class="empty-state">
      Chekdagi shtrix-kodni skanerlang yoki raqamini kiriting (masalan SOT-2026-000001).
    </p>

    <template v-else>
      <div class="table-card card-padded">
        <h3>{{ sale.number }} · {{ formatSum(sale.total) }}</h3>

        <div class="table-scroll">
          <table class="data-table">
            <thead>
              <tr>
                <th>Mahsulot</th>
                <th class="num">Sotilgan</th>
                <th class="num">Qaytarilgan</th>
                <th class="num">Qaytariladi</th>
                <th class="num">Summa</th>
              </tr>
            </thead>

            <tbody>
              <tr v-for="line in sale.lines" :key="line.id">
                <td>
                  <strong>{{ line.product_name }}</strong>
                  <small class="cell-sub">{{ line.variant_label || line.sku }}</small>
                </td>

                <td class="num">{{ line.quantity }}</td>
                <td class="num">{{ line.returned_quantity }}</td>

                <td class="num">
                  <input
                    class="cart-number"
                    type="number"
                    min="0"
                    :max="maxReturn(line.id)"
                    :value="returning[line.id] ?? 0"
                    @change="returning[line.id] = Math.min(maxReturn(line.id), Number(($event.target as HTMLInputElement).value) || 0)"
                  />
                </td>

                <td class="num">{{ formatMoney(line.line_total) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <div v-if="isExchange" class="table-card card-padded">
        <h3>Almashtirishga beriladi</h3>

        <table class="data-table">
          <tbody>
            <tr v-for="item in exchangeLines" :key="item.variant.id">
              <td>
                <strong>{{ item.variant.product_name }}</strong>
                <small class="cell-sub">{{ item.variant.label || item.variant.sku }}</small>
              </td>
              <td class="num">{{ item.quantity }} × {{ formatMoney(item.variant.price) }}</td>
              <td class="num">
                <strong>{{ formatMoney(multiplyMoney(item.variant.price, item.quantity)) }}</strong>
              </td>
              <td class="num">
                <button
                  class="icon-button delete"
                  type="button"
                  @click="exchangeLines = exchangeLines.filter((row) => row.variant.id !== item.variant.id)"
                >
                  <svg><use href="#i-trash" /></svg>
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <div class="table-card card-padded finish">
        <div class="finish-amount">
          <span v-if="!isExchange">Mijozga qaytariladi</span>
          <span v-else-if="compareMoney(difference, '0') >= 0">Mijozdan olinadi</span>
          <span v-else>Mijozga qaytariladi</span>

          <strong>
            {{ formatSum(isExchange ? difference.replace('-', '') : refundTotal) }}
          </strong>
        </div>

        <div class="finish-controls">
          <div class="field">
            <label>Usul</label>
            <select v-model="method">
              <option value="cash">Naqd</option>
              <option value="card">Karta</option>
            </select>
          </div>

          <button
            class="button button-gradient"
            type="button"
            :disabled="!hasReturn || saving"
            @click="onSubmit"
          >
            {{ saving ? 'Saqlanmoqda…' : isExchange ? 'Almashtirish' : 'Qaytarish' }}
          </button>
        </div>
      </div>
    </template>
  </section>
</template>

<style scoped>
.returns-head {
  display: flex;
  gap: 8px;
  align-items: center;
  margin-bottom: 12px;
}

.returns-head > :first-child {
  flex: 1;
  max-width: 520px;
}

.cart-number {
  width: 80px;
  text-align: right;
}

.success-notice {
  border-color: var(--green);
  background: var(--green-soft);
  color: var(--text);
  font-weight: 600;
}

.finish {
  margin-top: 12px;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.finish-amount {
  display: flex;
  flex-direction: column;
}

.finish-amount strong {
  font-size: 24px;
  font-variant-numeric: tabular-nums;
}

.finish-controls {
  display: flex;
  align-items: flex-end;
  gap: 8px;
}

.finish-controls .field {
  min-width: 140px;
}
</style>
