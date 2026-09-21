<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'

import ProductPicker from '@/components/ProductPicker.vue'
import ReceiptPrint from '@/components/ReceiptPrint.vue'
import ScanField from '@/components/ScanField.vue'
import { catalogApi } from '@/api/catalog'
import { errorMessage } from '@/api/client'
import { salesApi } from '@/api/sales'
import { useAuthStore } from '@/stores/auth'
import { usePosStore, type CartLine } from '@/stores/pos'
import { compareMoney, formatMoney, formatSum, normalizeMoneyInput, subtractMoney } from '@/utils/money'
import type { Sale, Variant } from '@/types'

const auth = useAuthStore()
const pos = usePosStore()

const scanner = ref<InstanceType<typeof ScanField> | null>(null)
const receipt = ref<InstanceType<typeof ReceiptPrint> | null>(null)
const changeButton = ref<HTMLButtonElement | null>(null)

const error = ref('')
const notice = ref('')
const saving = ref(false)

const paymentMethod = ref<'cash' | 'card' | 'mixed'>('cash')
const cardPart = ref('0')
const cashReceived = ref('')

const lastSale = ref<Sale | null>(null)

/** Tor ekranda tanlagich panel bo'lib ochiladi */
const pickerOpen = ref(false)

/** Qaytim katta harflarda — kassir yopmaguncha turadi */
const changeOpen = ref(false)
const lastChange = ref('0')

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

const canComplete = computed(() => !pos.isEmpty && !saving.value && !discountTooBig.value)

/** Har amaldan keyin fokus skaner maydoniga qaytadi. */
function focusScanner() {
  scanner.value?.focus()
}

function clearMessages() {
  error.value = ''
  notice.value = ''
}

function addToCart(variant: Variant) {
  const result = pos.add(variant)

  if (!result.ok) error.value = result.message ?? 'Tovar qo‘shilmadi.'
  else notice.value = `${variant.product_name} ${variant.label} qo‘shildi`
}

/** Skanerdan kelgan kod: tovarni savatga qo'shadi. */
async function onScan(code: string) {
  clearMessages()

  try {
    addToCart(await catalogApi.byBarcode(code))
  } catch (err) {
    error.value = errorMessage(err, `«${code}» — bunday shtrix-kod topilmadi.`)
  } finally {
    focusScanner()
  }
}

/** Tanlagichdan tanlangan tovar. */
function onPick(variant: Variant) {
  clearMessages()
  addToCart(variant)
  pickerOpen.value = false
  focusScanner()
}

function onQuantity(variantId: number, value: string) {
  clearMessages()

  const result = pos.setQuantity(variantId, Number.parseInt(value, 10) || 0)

  if (!result.ok) error.value = result.message ?? ''

  focusScanner()
}

/** Bittaga ko'paytirish yoki kamaytirish — barmoq uchun katta tugmalar. */
function step(line: CartLine, delta: number) {
  clearMessages()

  const result = pos.setQuantity(line.variantId, line.quantity + delta)

  if (!result.ok) error.value = result.message ?? ''

  focusScanner()
}

function onLineDiscount(variantId: number, value: string) {
  pos.setLineDiscount(variantId, value)
  focusScanner()
}

function onRemove(variantId: number) {
  clearMessages()
  pos.remove(variantId)
  focusScanner()
}

function onClear() {
  clearMessages()
  pos.clear()
  cashReceived.value = ''
  cardPart.value = '0'
  focusScanner()
}

/** Mijoz aynan kerakli summani berdi. */
function exactCash() {
  cashReceived.value = cashPart.value
  focusScanner()
}

function selectPayment(method: 'cash' | 'card' | 'mixed') {
  paymentMethod.value = method
  focusScanner()
}

/** F4 — to'lov turini almashtiradi. */
function cyclePayment() {
  const order = ['cash', 'card', 'mixed'] as const
  const next = order[(order.indexOf(paymentMethod.value) + 1) % order.length]!

  selectPayment(next)
}

async function onComplete() {
  if (!canComplete.value) return

  clearMessages()
  saving.value = true

  // Qaytim savat tozalangunga qadar hisoblanadi
  const changeAmount = change.value

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

    if (Number(changeAmount) > 0) {
      lastChange.value = changeAmount
      changeOpen.value = true

      // Yopish tugmasi fokusda: Enter ham, Esc ham yopadi
      requestAnimationFrame(() => changeButton.value?.focus())
    } else {
      focusScanner()
    }
  } catch (err) {
    error.value = errorMessage(err, 'Chekni yakunlab bo‘lmadi.')
    focusScanner()
  } finally {
    saving.value = false
  }
}

function closeChange() {
  changeOpen.value = false
  focusScanner()
}

function reprint() {
  receipt.value?.printReceipt()
  focusScanner()
}

/**
 * Klaviatura: F2 — yakunlash, F4 — to'lov turi, Esc — ochiq oynani
 * yopadi, ochiq oyna bo'lmasa savatni tozalaydi. Kassir sichqonchaga
 * qo'l uzatmasdan ishlaydi.
 */
function onKeydown(event: KeyboardEvent) {
  if (event.key === 'F2') {
    event.preventDefault()
    void onComplete()
    return
  }

  if (event.key === 'F4') {
    event.preventDefault()
    cyclePayment()
    return
  }

  if (event.key === 'Escape') {
    event.preventDefault()

    if (changeOpen.value) {
      closeChange()
    } else if (pickerOpen.value) {
      pickerOpen.value = false
      focusScanner()
    } else {
      onClear()
    }
  }
}

onMounted(() => window.addEventListener('keydown', onKeydown))
onBeforeUnmount(() => window.removeEventListener('keydown', onKeydown))
</script>

<template>
  <section class="pos">
    <!-- Tanlagich: yorliq o'qilmasa yoki skaner ishlamasa shu yerdan sotiladi -->
    <aside class="pos-picker" :class="{ open: pickerOpen }">
      <div class="picker-head">
        <strong>Tovar tanlash</strong>

        <button
          class="icon-button"
          type="button"
          aria-label="Yopish"
          @click="pickerOpen = false"
        >
          <svg><use href="#i-close" /></svg>
        </button>
      </div>

      <ProductPicker @pick="onPick" />
    </aside>

    <!-- Savat -->
    <div class="pos-cart">
      <div class="cart-head">
        <ScanField ref="scanner" @scan="onScan" />

        <button class="button button-outline picker-toggle" type="button" @click="pickerOpen = true">
          <svg><use href="#i-catalog" /></svg>
          <span>Tovar tanlash</span>
        </button>
      </div>

      <p v-if="error" class="pos-error" role="alert">{{ error }}</p>
      <p v-else-if="notice" class="pos-notice">{{ notice }}</p>

      <div class="cart-table-wrap">
        <table class="data-table cart-table">
          <thead>
            <!-- Narx alohida ustun emas: 1366 px ekranda yon menyudan keyin
                 savatga ~500 px qoladi va oltita ustun sig'masdi -->
            <tr>
              <th>Mahsulot</th>
              <th class="num">Soni</th>
              <th class="num">Chegirma</th>
              <th class="num">Summa</th>
              <th></th>
            </tr>
          </thead>

          <tbody>
            <tr v-if="pos.isEmpty">
              <td colspan="5" class="empty-state">
                Savat bo‘sh. Shtrix-kodni skanerlang yoki tovarni ro‘yxatdan tanlang.
              </td>
            </tr>

            <tr v-for="(line, index) in pos.lines" :key="line.variantId">
              <td>
                <strong>{{ line.name }}</strong>
                <small class="cell-sub">
                  {{ line.label || line.sku }} · {{ formatMoney(line.price) }} so‘m
                </small>
              </td>

              <td class="num">
                <div class="quantity">
                  <button
                    class="step"
                    type="button"
                    :aria-label="`${line.name}: bittaga kamaytirish`"
                    @click="step(line, -1)"
                  >
                    −
                  </button>

                  <input
                    class="cart-number"
                    type="number"
                    min="1"
                    :max="line.stock"
                    :value="line.quantity"
                    :aria-label="`${line.name}: soni`"
                    @change="onQuantity(line.variantId, ($event.target as HTMLInputElement).value)"
                  />

                  <button
                    class="step"
                    type="button"
                    :disabled="line.quantity >= line.stock"
                    :aria-label="`${line.name}: bittaga ko‘paytirish`"
                    @click="step(line, 1)"
                  >
                    +
                  </button>
                </div>
              </td>

              <td class="num">
                <input
                  class="cart-number discount"
                  type="number"
                  min="0"
                  max="100"
                  :value="line.discountPercent"
                  :aria-label="`${line.name}: chegirma foizi`"
                  @change="onLineDiscount(line.variantId, ($event.target as HTMLInputElement).value)"
                />
              </td>

              <td class="num">
                <strong>{{ formatMoney(pos.lineTotals[index]?.total ?? '0') }}</strong>
              </td>

              <td class="num">
                <button
                  class="icon-button delete"
                  type="button"
                  :aria-label="`${line.name}: o‘chirish`"
                  @click="onRemove(line.variantId)"
                >
                  <svg><use href="#i-trash" /></svg>
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Hisob va to'lov -->
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
            <select v-model="pos.discountMode" aria-label="Chegirma turi">
              <option value="percent">%</option>
              <option value="amount">so‘m</option>
            </select>

            <input
              v-model="pos.discountValue"
              type="text"
              inputmode="decimal"
              aria-label="Chegirma"
            />
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
            @click="selectPayment(method)"
          >
            {{ method === 'cash' ? 'Naqd' : method === 'card' ? 'Karta' : 'Aralash' }}
          </button>
        </div>

        <p class="shortcut-hint">F4 — to‘lov turini almashtiradi</p>

        <div v-if="paymentMethod === 'mixed'" class="field">
          <label>Kartadan</label>
          <input v-model="cardPart" type="text" inputmode="decimal" />
          <small class="field-hint">Naqd qismi: {{ formatSum(cashPart) }}</small>
        </div>

        <div v-if="paymentMethod !== 'card'" class="field">
          <label>Mijoz berdi</label>

          <div class="cash-row">
            <input v-model="cashReceived" type="text" inputmode="decimal" placeholder="0" />

            <button class="button button-outline exact" type="button" @click="exactCash">
              Aniq summa
            </button>
          </div>

          <small v-if="change !== '0'" class="change">Qaytim: {{ formatSum(change) }}</small>
        </div>
      </div>

      <div class="pos-actions">
        <button class="button button-outline" type="button" :disabled="pos.isEmpty" @click="onClear">
          Savatni tozalash <span class="key">Esc</span>
        </button>

        <button
          class="button button-gradient complete"
          type="button"
          :disabled="!canComplete"
          @click="onComplete"
        >
          {{ saving ? 'Saqlanmoqda…' : 'Yakunlash' }}
          <span class="key light">F2</span>
        </button>
      </div>

      <!-- Qaytarish kassadan ochiladi: administrator menyusida alohida band yo'q -->
      <RouterLink class="returns-link" to="/returns">Qaytarish yoki almashtirish</RouterLink>

      <div v-if="lastSale" class="last-sale">
        <span>
          Oxirgi chek: <strong>{{ lastSale.number }}</strong> — {{ formatSum(lastSale.total) }}
        </span>

        <button class="button button-outline" type="button" @click="reprint">
          <svg><use href="#i-print" /></svg>
          <span>Qayta chop etish</span>
        </button>
      </div>
    </aside>

    <!-- Qaytim: kassir yopmaguncha ko'rinib turadi -->
    <div v-if="changeOpen" class="change-overlay" @click.self="closeChange">
      <div class="change-card" role="dialog" aria-modal="true" aria-label="Qaytim">
        <span class="change-label">Qaytim</span>

        <strong class="change-amount" data-testid="change-amount">{{ formatSum(lastChange) }}</strong>

        <span class="change-receipt">{{ lastSale?.number }}</span>

        <button
          ref="changeButton"
          class="button button-gradient change-close"
          type="button"
          @click="closeChange"
        >
          Yopish <span class="key light">Esc</span>
        </button>
      </div>
    </div>

    <ReceiptPrint ref="receipt" :sale="lastSale" />
  </section>
</template>

<style scoped>
/* 1366×768 ekranda hamma narsa sig'adi: faqat savat ro'yxati va
   tanlagich ichkaridan suriladi, sahifaning o'zi surilmaydi. */
/* 1366 px ekranda yon menyudan keyin ~1070 px qoladi: tanlagich va hisob
   iloji boricha tor, qolgani savatga beriladi */
.pos {
  display: grid;
  grid-template-columns: minmax(220px, 280px) minmax(0, 1fr) minmax(280px, 320px);
  gap: 10px;
  height: calc(100vh - 56px - 48px);
}

.pos-picker {
  display: flex;
  flex-direction: column;
  gap: 8px;
  min-height: 0;
  padding: 10px;
  border: 1px solid var(--border);
  border-radius: var(--radius);
  background: var(--surface);
}

.picker-head {
  display: none;
  align-items: center;
  justify-content: space-between;
}

.pos-cart {
  display: flex;
  flex-direction: column;
  gap: 8px;
  min-width: 0;
}

.cart-head {
  display: flex;
  gap: 8px;
}

.cart-head .scan-field {
  flex: 1;
}

/* Keng ekranda tanlagich doim ko'rinadi — tugma kerak emas */
.picker-toggle {
  display: none;
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

/* Savat tor ustunda: katakchalar orasidagi bo'shliq kamaytirildi */
.cart-table th,
.cart-table td {
  padding-right: 6px;
  padding-left: 6px;
}

/* Ustun kengliklari qat'iy: uzun tovar nomi jadvalni kengaytirib,
   "Summa" ustunini chetga chiqarib yuborardi */
.cart-table {
  width: 100%;
  table-layout: fixed;
}

.cart-table th:nth-child(2) {
  width: 136px;
}

.cart-table th:nth-child(3) {
  width: 74px;
}

.cart-table th:nth-child(4) {
  width: 94px;
}

.cart-table th:nth-child(5) {
  width: 40px;
}

/* Jadval katakchasida umumiy `nowrap` bor — uzun nom shu yerda o'raladi */
.cart-table td:first-child {
  white-space: normal;
}

.cart-table td:first-child strong {
  display: block;
  overflow-wrap: anywhere;
}

.cart-number {
  width: 52px;
  text-align: center;
}

.cart-number.discount {
  width: 56px;
}


.quantity {
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

/* Barmoq uchun katta nishon */
.step {
  width: 40px;
  height: 40px;
  border: 1px solid var(--border-strong);
  border-radius: var(--radius);
  background: var(--surface);
  color: var(--text);
  font-size: 20px;
  line-height: 1;
  cursor: pointer;
}

.step:hover:not(:disabled) {
  border-color: var(--accent);
  background: var(--accent-soft);
}

.step:disabled {
  opacity: 0.4;
  cursor: not-allowed;
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
  gap: 10px;
  overflow-y: auto;
  padding: 14px;
  border: 1px solid var(--border);
  border-radius: var(--radius);
  background: var(--surface);
}

.summary-rows > div {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 3px 0;
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
  padding: 10px 0;
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
}

.shortcut-hint {
  margin: 4px 0 0;
  color: var(--text-muted);
  font-size: 11px;
  text-align: center;
}

.cash-row {
  display: flex;
  gap: 6px;
}

.cash-row input {
  flex: 1;
  min-width: 0;
}

.exact {
  flex: none;
  white-space: nowrap;
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

.key {
  margin-left: 6px;
  padding: 1px 5px;
  border: 1px solid var(--border-strong);
  border-radius: var(--radius-small);
  color: var(--text-muted);
  font-size: 11px;
}

.key.light {
  border-color: rgb(255 255 255 / 45%);
  color: rgb(255 255 255 / 85%);
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
  padding-top: 10px;
  border-top: 1px solid var(--border);
  font-size: 13px;
}

/* --- Qaytim --- */

.change-overlay {
  position: fixed;
  inset: 0;
  z-index: 60;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 16px;
  background: rgb(15 23 42 / 55%);
}

.change-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  padding: 32px 48px;
  border-radius: var(--radius);
  background: var(--surface);
  text-align: center;
}

.change-label {
  color: var(--text-muted);
  font-size: 16px;
}

/* Xonaning narigi chetidan ham o'qiladi */
.change-amount {
  font-size: 56px;
  line-height: 1.1;
  font-variant-numeric: tabular-nums;
}

.change-receipt {
  color: var(--text-muted);
  font-size: 13px;
}

.change-close {
  min-width: 180px;
  min-height: 48px;
  margin-top: 12px;
}

/* Planshet va tor ekran: tanlagich panel bo'lib ochiladi */
@media (max-width: 1280px) {
  .pos {
    grid-template-columns: minmax(0, 1fr) 320px;
  }

  .pos-picker {
    position: fixed;
    inset: 56px 0 0;
    z-index: 45;
    display: none;
    border-radius: 0;
  }

  .pos-picker.open {
    display: flex;
  }

  .picker-head,
  .picker-toggle {
    display: flex;
  }
}

@media (max-width: 900px) {
  .pos {
    grid-template-columns: 1fr;
    height: auto;
  }

  .cart-table-wrap {
    max-height: 50vh;
  }

  .step {
    width: 44px;
    height: 44px;
  }
}
</style>
