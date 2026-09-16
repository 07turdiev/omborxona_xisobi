<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'

import LabelPrint from '@/components/LabelPrint.vue'
import ScanField from '@/components/ScanField.vue'
import { catalogApi } from '@/api/catalog'
import { errorMessage } from '@/api/client'
import { purchasesApi } from '@/api/purchases'
import { formatDate, todayIso } from '@/utils/date'
import { addMoney, formatMoney, formatSum, multiplyMoney, normalizeMoneyInput } from '@/utils/money'
import type { Purchase, Supplier, Variant } from '@/types'

interface DraftLine {
  variant: number
  name: string
  label: string
  barcode: string
  quantity: number
  unit_cost: string
}

const purchases = ref<Purchase[]>([])
const suppliers = ref<Supplier[]>([])
const opened = ref<Purchase | null>(null)

const loading = ref(false)
const saving = ref(false)
const error = ref('')
const notice = ref('')

const editorOpen = ref(false)
const scanner = ref<InstanceType<typeof ScanField> | null>(null)
const labels = ref<InstanceType<typeof LabelPrint> | null>(null)
const labelItems = ref<{ barcode: string; name: string; label: string; price: string; quantity: number }[]>([])

const draft = ref({
  date: todayIso(),
  supplier: null as number | null,
  note: '',
  amount_paid: '',
  lines: [] as DraftLine[],
})

const draftTotal = computed(() =>
  draft.value.lines.reduce(
    (sum, line) => addMoney(sum, multiplyMoney(line.unit_cost || '0', line.quantity)),
    '0',
  ),
)

async function load() {
  loading.value = true
  error.value = ''

  try {
    const [page, supplierPage] = await Promise.all([purchasesApi.list(), purchasesApi.suppliers()])

    purchases.value = page.results
    suppliers.value = supplierPage.results
  } catch (err) {
    error.value = errorMessage(err, 'Kirimlarni yuklab bo‘lmadi.')
  } finally {
    loading.value = false
  }
}

function openEditor() {
  draft.value = { date: todayIso(), supplier: null, note: '', amount_paid: '', lines: [] }
  editorOpen.value = true
  opened.value = null
}

async function onScan(code: string) {
  error.value = ''

  try {
    const variant: Variant = await catalogApi.byBarcode(code)
    const existing = draft.value.lines.find((line) => line.variant === variant.id)

    if (existing) {
      existing.quantity += 1
    } else {
      draft.value.lines.push({
        variant: variant.id,
        name: variant.product_name,
        label: variant.label,
        barcode: variant.barcode,
        quantity: 1,
        // Oxirgi tannarx taklif qilinadi, admin o'zgartira oladi
        unit_cost: variant.average_cost ?? '',
      })
    }
  } catch (err) {
    error.value = errorMessage(err, `«${code}» — tovar topilmadi.`)
  } finally {
    scanner.value?.focus()
  }
}

async function onSaveDraft(confirmAfter: boolean) {
  if (!draft.value.lines.length || saving.value) return

  saving.value = true
  error.value = ''
  notice.value = ''

  try {
    let purchase = await purchasesApi.create({
      date: draft.value.date,
      supplier: draft.value.supplier,
      note: draft.value.note,
      amount_paid: draft.value.amount_paid
        ? normalizeMoneyInput(draft.value.amount_paid)
        : undefined,
      lines: draft.value.lines.map((line) => ({
        variant: line.variant,
        quantity: line.quantity,
        unit_cost: normalizeMoneyInput(line.unit_cost || '0'),
      })),
    })

    if (confirmAfter) {
      purchase = await purchasesApi.confirm(purchase.id)
      notice.value = `${purchase.number} tasdiqlandi — tovar omborga kirdi.`
    } else {
      notice.value = `${purchase.number} qoralama sifatida saqlandi.`
    }

    editorOpen.value = false
    opened.value = purchase
    await load()
  } catch (err) {
    error.value = errorMessage(err, 'Kirimni saqlab bo‘lmadi.')
  } finally {
    saving.value = false
  }
}

async function onConfirm(purchase: Purchase) {
  try {
    const updated = await purchasesApi.confirm(purchase.id)

    notice.value = `${updated.number} tasdiqlandi.`
    opened.value = updated
    await load()
  } catch (err) {
    error.value = errorMessage(err, 'Tasdiqlab bo‘lmadi.')
  }
}

async function onCancel(purchase: Purchase) {
  if (!window.confirm(`${purchase.number} bekor qilinsinmi? Tovar ombordan chiqariladi.`)) return

  try {
    const updated = await purchasesApi.cancel(purchase.id)

    notice.value = `${updated.number} bekor qilindi.`
    opened.value = updated
    await load()
  } catch (err) {
    error.value = errorMessage(err, 'Bekor qilib bo‘lmadi — qoldiq yetarli emas.')
  }
}

/** Kirim qatorlari bo'yicha yorliq: har dona uchun bittadan. */
async function printLabels(purchase: Purchase) {
  const full = await purchasesApi.get(purchase.id)

  labelItems.value = full.lines
    .filter((line) => line.barcode)
    .map((line) => ({
      barcode: line.barcode ?? '',
      name: line.product_name ?? '',
      label: line.variant_label ?? '',
      price: '0',
      quantity: line.quantity,
    }))

  // Narx yorliqda kerak — variantdan olamiz
  const variants = await Promise.all(
    full.lines.map((line) => catalogApi.variants({ search: line.sku ?? '' })),
  )

  labelItems.value = labelItems.value.map((item, index) => ({
    ...item,
    price: variants[index]?.results[0]?.price ?? '0',
  }))

  setTimeout(() => labels.value?.printLabels(), 50)
}

onMounted(load)
</script>

<template>
  <section class="app-section active">
    <div class="section-toolbar">
      <div class="filters"></div>

      <button class="button button-gradient" type="button" @click="openEditor">
        <svg><use href="#i-plus" /></svg>
        <span>Yangi kirim</span>
      </button>
    </div>

    <p v-if="error" class="load-error">{{ error }}</p>
    <p v-if="notice" class="notice">{{ notice }}</p>

    <!-- Kirim yaratish -->
    <div v-if="editorOpen" class="table-card card-padded editor">
      <div class="editor-head">
        <div class="field">
          <label>Sana</label>
          <input v-model="draft.date" type="date" />
        </div>

        <div class="field">
          <label>Ta’minotchi</label>
          <select v-model="draft.supplier">
            <option :value="null">Ta’minotchisiz (boshlang‘ich qoldiq)</option>
            <option v-for="item in suppliers" :key="item.id" :value="item.id">{{ item.name }}</option>
          </select>
        </div>

        <div class="field">
          <label>To‘langan summa</label>
          <input v-model="draft.amount_paid" type="text" inputmode="decimal" placeholder="0" />
        </div>

        <div class="field">
          <label>Izoh</label>
          <input v-model="draft.note" type="text" />
        </div>
      </div>

      <ScanField ref="scanner" placeholder="Kirim qilinadigan tovarni skanerlang" @scan="onScan" />

      <table class="data-table">
        <thead>
          <tr>
            <th>Mahsulot</th>
            <th class="num">Soni</th>
            <th class="num">Tannarx</th>
            <th class="num">Summa</th>
            <th></th>
          </tr>
        </thead>

        <tbody>
          <tr v-if="!draft.lines.length">
            <td colspan="5" class="empty-state">Tovar skanerlang yoki shtrix-kodni kiriting.</td>
          </tr>

          <tr v-for="(line, index) in draft.lines" v-else :key="line.variant">
            <td>
              <strong>{{ line.name }}</strong>
              <small class="cell-sub">{{ line.label }}</small>
            </td>

            <td class="num">
              <input v-model.number="line.quantity" class="cart-number" type="number" min="1" />
            </td>

            <td class="num">
              <input v-model="line.unit_cost" class="cart-number wide" type="text" inputmode="decimal" />
            </td>

            <td class="num">
              {{ formatMoney(multiplyMoney(line.unit_cost || '0', line.quantity)) }}
            </td>

            <td class="num">
              <button
                class="icon-button delete"
                type="button"
                @click="draft.lines.splice(index, 1)"
              >
                <svg><use href="#i-trash" /></svg>
              </button>
            </td>
          </tr>
        </tbody>
      </table>

      <div class="editor-footer">
        <strong>Jami: {{ formatSum(draftTotal) }}</strong>

        <div class="editor-actions">
          <button class="button button-outline" type="button" @click="editorOpen = false">
            Bekor qilish
          </button>

          <button
            class="button button-outline"
            type="button"
            :disabled="saving"
            @click="onSaveDraft(false)"
          >
            Qoralama
          </button>

          <button
            class="button button-gradient"
            type="button"
            :disabled="saving"
            @click="onSaveDraft(true)"
          >
            {{ saving ? 'Saqlanmoqda…' : 'Saqlash va tasdiqlash' }}
          </button>
        </div>
      </div>
    </div>

    <div class="table-card">
      <div class="table-scroll">
        <table class="data-table">
          <thead>
            <tr>
              <th>Hujjat</th>
              <th>Sana</th>
              <th>Ta’minotchi</th>
              <th class="num">Summa</th>
              <th class="num">Qarz</th>
              <th>Holati</th>
              <th></th>
            </tr>
          </thead>

          <tbody>
            <tr v-if="loading">
              <td colspan="7" class="empty-state">Yuklanmoqda…</td>
            </tr>

            <tr v-else-if="!purchases.length">
              <td colspan="7" class="empty-state">Kirim hujjati yo‘q.</td>
            </tr>

            <tr v-for="purchase in purchases" v-else :key="purchase.id">
              <td><strong>{{ purchase.number }}</strong></td>
              <td>{{ formatDate(purchase.date) }}</td>
              <td>{{ purchase.supplier_name ?? 'Ta’minotchisiz' }}</td>
              <td class="num">{{ formatMoney(purchase.total) }}</td>
              <td class="num">{{ formatMoney(purchase.debt) }}</td>
              <td>
                <span
                  class="pill"
                  :class="{
                    'pill-green': purchase.status === 'confirmed',
                    'pill-grey': purchase.status === 'draft',
                    'pill-red': purchase.status === 'cancelled',
                  }"
                >
                  {{ purchase.status_display }}
                </span>
              </td>

              <td class="num row-actions">
                <button
                  v-if="purchase.status === 'draft'"
                  class="button button-gradient"
                  type="button"
                  @click="onConfirm(purchase)"
                >
                  Tasdiqlash
                </button>

                <button
                  v-if="purchase.status === 'confirmed'"
                  class="button button-outline"
                  type="button"
                  @click="printLabels(purchase)"
                >
                  <svg><use href="#i-print" /></svg>
                  <span>Yorliqlar</span>
                </button>

                <button
                  v-if="purchase.status === 'confirmed'"
                  class="button button-danger"
                  type="button"
                  @click="onCancel(purchase)"
                >
                  Bekor
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <LabelPrint ref="labels" :items="labelItems" />
  </section>
</template>

<style scoped>
.editor {
  margin-bottom: 12px;
}

.editor-head {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 10px;
  margin-bottom: 12px;
}

.cart-number {
  width: 80px;
  text-align: right;
}

.cart-number.wide {
  width: 120px;
}

.editor-footer {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid var(--border);
}

.editor-footer strong {
  font-size: 18px;
}

.editor-actions {
  display: flex;
  gap: 8px;
}

.row-actions .button {
  margin-left: 6px;
}
</style>
