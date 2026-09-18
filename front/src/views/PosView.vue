<script setup lang="ts">
import { computed, ref } from 'vue'
import { RouterLink } from 'vue-router'

import ReceiptPrint from '@/components/ReceiptPrint.vue'
import ScanField from '@/components/ScanField.vue'
import { catalogApi } from '@/api/catalog'
import { errorMessage } from '@/api/client'
import { salesApi } from '@/api/sales'
import { useAuthStore } from '@/stores/auth'
import { usePosStore } from '@/stores/pos'
import { compareMoney, formatMoney, formatSum, normalizeMoneyInput, subtractMoney } from '@/utils/money'
import type { Sale } from '@/types'

const auth = useAuthStore()
const pos = usePosStore()

const scanner = ref<InstanceType<typeof ScanField> | null>(null)
const receipt = ref<InstanceType<typeof ReceiptPrint> | null>(null)

const error = ref('')
const notice = ref('')
const saving = ref(false)

const paymentMethod = ref<'cash' | 'card' | 'mixed'>('cash')
const cardPart = ref('0')
const cashReceived = ref('')

const lastSale = ref<Sale | null>(null)

const maxDiscount = computed(() => auth.shop?.max_discount_percent ?? '0')

const cashPart = computed(() => {
  if (paymentMethod.value === 'cash') return pos.total
  if (paymentMethod.value === 'card') return '0'

  const card = normalizeMoneyInput(cardPart.value || '0')

  return compareMoney(card, pos.total) >= 0 ? '0' : subtractMoney(pos.total, card)
})

const cardAmount = computed(() => subtractMoney(pos.total, cashPart.value))

/** Naqd to'lovda qaytim. */
const change = computed(() => {
  if (!cashReceived.value.trim()) return '0'

  const received = normalizeMoneyInput(cashReceived.value)

  return compareMoney(received, cashPart.value) > 0
    ? subtractMoney(received, cashPart.value)
    : '0'
})

const discountTooBig = computed(() => !auth.isAdmin && pos.discountExceeds(maxDiscount.value))

const canComplete = computed(
  () => !pos.isEmpty && !saving.value && !discountTooBig.value,
)

function clearMessages() {
  error.value = ''
  notice.value = ''
}

/** Skanerdan kelgan kod: tovarni savatga qo'shadi. */
async function onScan(code: string) {
  clearMessages()

  try {
    const variant = await catalogApi.byBarcode(code)
    const result = pos.add(variant)

    if (!result.ok) {
      error.value = result.message ?? 'Tovar qo‘shilmadi.'
    } else {
      notice.value = `${variant.product_name} ${variant.label} qo‘shildi`
    }
  } catch (err) {
    error.value = errorMessage(err, `«${code}» — bunday shtrix-kod topilmadi.`)
  } finally {
    scanner.value?.focus()
  }
}

function onQuantity(variantId: number, value: string) {
  clearMessages()

  const result = pos.setQuantity(variantId, Number.parseInt(value, 10) || 0)

  if (!result.ok) error.value = result.message ?? ''

  scanner.value?.focus()
}

function onRemove(variantId: number) {
  clearMessages()
  pos.remove(variantId)
  scanner.value?.focus()
}

function onClear() {
  clearMessages()
  pos.clear()
  cashReceived.value = ''
  cardPart.value = '0'
  scanner.value?.focus()
}

async function onComplete() {
  if (!canComplete.value) return

  clearMessages()
  saving.value = true

  try {
    const sale = await salesApi.create({
      lines: pos.lines.map((line) => ({
        variant: line.variantId,
        quantity: line.quantity,
        unit_price: line.price,
        discount_percent: line.discountPercent || '0',
      })),
      discount_percent: pos.discountMode === 'percent' ? pos.discountValue || '0' : undefined,
      discount_amount:
        pos.discountMode === 'amount' ? normalizeMoneyInput(pos.discountValue) : undefined,
      cash_amount: cashPart.value,
      card_amount: cardAmount.value,
      request_key: pos.requestKey,
    })

    lastSale.value = sale
    pos.clear()
    cashReceived.value = ''
    cardPart.value = '0'
    notice.value = `${sale.number} — chek yakunlandi`

    // Chek darhol chop etiladi
    receipt.value?.printReceipt()
  } catch (err) {
    error.value = errorMessage(err, 'Chekni yakunlab bo‘lmadi.')
  } finally {
    saving.value = false
    scanner.value?.focus()
  }
}

function reprint() {
  receipt.value?.printReceipt()
  scanner.value?.focus()
}
</script>

<template>
  <section class="pos">
    <!-- Chap taraf: skaner va savat -->
    <div class="pos-cart">
      <ScanField ref="scanner" @scan="onScan" />

      <p v-if="error" class="pos-error" role="alert">{{ error }}</p>
      <p v-else-if="notice" class="pos-notice">{{ notice }}</p>

      <div class="cart-table-wrap">
        <table class="data-table cart-table">
          <thead>
            <tr>
              <th>Mahsulot</th>
              <th class="num">Narx</th>
              <th class="num">Soni</th>
              <th class="num">Chegirma %</th>
              <th class="num">Summa</th>
              <th></th>
            </tr>
          </thead>

          <tbody>
            <tr v-if="pos.isEmpty">
              <td colspan="6" class="empty-state">
                Savat bo‘sh. Tovar shtrix-kodini skanerlang.
              </td>
            </tr>

            <tr v-for="(line, index) in pos.lines" :key="line.variantId">
              <td>
                <strong>{{ line.name }}</strong>
                <small class="cell-sub">{{ line.label || line.sku }}</small>
              </td>

              <td class="num">{{ formatMoney(line.price) }}</td>

              <td class="num">
                <input
                  class="cart-number"
                  type="number"
                  min="1"
                  :max="line.stock"
                  :value="line.quantity"
                  @change="onQuantity(line.variantId, ($event.target as HTMLInputElement).value)"
                />
              </td>

              <td class="num">
                <input
                  class="cart-number"
                  type="number"
                  min="0"
                  max="100"
                  :value="line.discountPercent"
                  @change="pos.setLineDiscount(line.variantId, ($event.target as HTMLInputElement).value); scanner?.focus()"
                />
              </td>

              <td class="num">
                <strong>{{ formatMoney(pos.lineTotals[index]?.total ?? '0') }}</strong>
              </td>

              <td class="num">
                <button class="icon-button delete" type="button" title="O‘chirish" @click="onRemove(line.variantId)">
                  <svg><use href="#i-trash" /></svg>
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- O'ng taraf: hisob va to'lov -->
    <aside class="pos-summary">
      <div class="summary-rows">
        <div>
          <span>Tovar</span>
          <strong>{{ pos.itemCount }} dona</strong>
        </div>

        <div>
          <span>Chegirmasiz</span>
          <strong>{{ formatMoney(pos.subtotal) }}</strong>
        </div>

        <div class="discount-row">
          <span>Chek chegirmasi</span>

          <div class="discount-controls">
            <select v-model="pos.discountMode">
              <option value="percent">%</option>
              <option value="amount">so‘m</option>
            </select>

            <input v-model="pos.discountValue" type="text" inputmode="decimal" />
          </div>
        </div>

        <div>
          <span>Chegirma</span>
          <strong>{{ formatMoney(pos.discountTotal) }}</strong>
        </div>
      </div>

      <div class="summary-total">
        <span>To‘lov</span>
        <strong>{{ formatSum(pos.total) }}</strong>
      </div>

      <p v-if="discountTooBig" class="pos-error">
        Chegirma {{ maxDiscount }} % dan oshmasligi kerak.
      </p>

      <div class="payment">
        <div class="payment-methods">
          <button
            v-for="method in (['cash', 'card', 'mixed'] as const)"
            :key="method"
            class="button"
            :class="paymentMethod === method ? 'button-gradient' : 'button-outline'"
            type="button"
            @click="paymentMethod = method; scanner?.focus()"
          >
            {{ method === 'cash' ? 'Naqd' : method === 'card' ? 'Karta' : 'Aralash' }}
          </button>
        </div>

        <div v-if="paymentMethod === 'mixed'" class="field">
          <label>Kartadan</label>
          <input v-model="cardPart" type="text" inputmode="decimal" />
          <small class="field-hint">Naqd qismi: {{ formatSum(cashPart) }}</small>
        </div>

        <div v-if="paymentMethod !== 'card'" class="field">
          <label>Mijoz berdi</label>
          <input v-model="cashReceived" type="text" inputmode="decimal" placeholder="0" />
          <small v-if="change !== '0'" class="change">Qaytim: {{ formatSum(change) }}</small>
        </div>
      </div>

      <div class="pos-actions">
        <button class="button button-outline" type="button" :disabled="pos.isEmpty" @click="onClear">
          Savatni tozalash
        </button>

        <button
          class="button button-gradient complete"
          type="button"
          :disabled="!canComplete"
          @click="onComplete"
        >
          {{ saving ? 'Saqlanmoqda…' : 'Yakunlash' }}
        </button>
      </div>

      <!-- Qaytarish kassadan ochiladi: administrator menyusida alohida band yo'q -->
      <RouterLink class="returns-link" to="/returns">Qaytarish yoki almashtirish</RouterLink>

      <div v-if="lastSale" class="last-sale">
        <span>Oxirgi chek: <strong>{{ lastSale.number }}</strong> — {{ formatSum(lastSale.total) }}</span>
        <button class="button button-outline" type="button" @click="reprint">
          <svg><use href="#i-print" /></svg>
          <span>Qayta chop etish</span>
        </button>
      </div>
    </aside>

    <ReceiptPrint ref="receipt" :sale="lastSale" />
  </section>
</template>

<style scoped>
/* 1366×768 ekranda savat qismi aylantirilmasdan sig'adi */
.pos {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 340px;
  gap: 12px;
  height: calc(100vh - 56px - 32px);
}

.pos-cart {
  display: flex;
  flex-direction: column;
  gap: 8px;
  min-width: 0;
}

.cart-table-wrap {
  flex: 1;
  overflow-y: auto;
  border: 1px solid var(--border);
  border-radius: var(--radius);
  background: var(--surface);
}

.cart-table th {
  position: sticky;
  top: 0;
  z-index: 1;
}

.cart-number {
  width: 72px;
  text-align: right;
}

.pos-error,
.pos-notice {
  margin: 0;
  padding: 8px 12px;
  border-radius: var(--radius);
  font-size: 13px;
}

.pos-error {
  background: var(--red-soft);
  color: var(--red);
  font-weight: 600;
}

.pos-notice {
  background: var(--green-soft);
  color: var(--green);
}

.pos-summary {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 16px;
  border: 1px solid var(--border);
  border-radius: var(--radius);
  background: var(--surface);
  overflow-y: auto;
}

.summary-rows > div {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 4px 0;
  font-size: 13px;
}

.discount-controls {
  display: flex;
  gap: 6px;
}

.discount-controls select {
  width: 72px;
}

.discount-controls input {
  width: 96px;
  text-align: right;
}

.summary-total {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  padding: 12px 0;
  border-top: 1px solid var(--border);
  border-bottom: 1px solid var(--border);
}

.summary-total strong {
  font-size: 24px;
  font-variant-numeric: tabular-nums;
}

.payment-methods {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 6px;
  margin-bottom: 8px;
}

.change {
  margin-top: 4px;
  color: var(--green);
  font-weight: 700;
}

.pos-actions {
  display: grid;
  gap: 8px;
}

.complete {
  min-height: 48px;
  font-size: 16px;
}

.returns-link {
  align-self: center;
  color: var(--accent);
  font-size: 13px;
  font-weight: 600;
}

.last-sale {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding-top: 12px;
  border-top: 1px solid var(--border);
  font-size: 13px;
}

@media (max-width: 1000px) {
  .pos {
    grid-template-columns: 1fr;
    height: auto;
  }
}
</style>
