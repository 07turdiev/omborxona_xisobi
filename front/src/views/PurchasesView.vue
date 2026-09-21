<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'

import LabelPrint from '@/components/LabelPrint.vue'
import ProductCreateDialog from '@/components/ProductCreateDialog.vue'
import ProductSearchField from '@/components/ProductSearchField.vue'
import PurchaseDocument from '@/components/PurchaseDocument.vue'
import PurchaseModelGrid from '@/components/PurchaseModelGrid.vue'
import RecentModelsStrip from '@/components/RecentModelsStrip.vue'
import { catalogApi } from '@/api/catalog'
import { errorMessage } from '@/api/client'
import { purchasesApi } from '@/api/purchases'
import { formatDayMonth, formatTime, todayIso } from '@/utils/date'
import { formatMoney, formatSum, normalizeMoneyInput } from '@/utils/money'
import {
  cloneModel,
  draftLines,
  draftTotal,
  draftUnits,
  emptyModel,
  modelFromLines,
  modelTotal,
  modelUnits,
  type DraftModel,
} from '@/utils/receiving'
import type { LabelItem } from '@/api/agent'
import type { Product, Purchase, PurchaseLine, Supplier } from '@/types'

/**
 * Kirim: do'konga kelgan tovarni qabul qilish.
 *
 * Tovar shtrix-kodsiz keladi — yorliqni do'konning o'zi chiqaradi.
 * Shuning uchun ekran skanerdan emas, **modeldan** boshlanadi: tepada
 * oxirgi qo'shilgan modellar, ostida nom bo'yicha qidiruv va "Yangi
 * mahsulot". Tanlangan model o'lcham × rang katakchasi bo'lib ochiladi.
 *
 * Hujjat forma sahifada doim ochiq turadi: yangi qoralama o'zidan
 * boshlanadi, saqlangani esa shu yerga yuklanadi.
 */

const route = useRoute()

const purchases = ref<Purchase[]>([])
const suppliers = ref<Supplier[]>([])
const opened = ref<Purchase | null>(null)

const loading = ref(false)
const saving = ref(false)
const error = ref('')
const notice = ref('')

/** Hujjatning sarlavhasi. `id` — saqlangan qoralamani davom ettirish uchun. */
const draft = ref({
  id: null as number | null,
  number: '',
  date: todayIso(),
  supplier: null as number | null,
  note: '',
  amount_paid: '',
})

const models = ref<DraftModel[]>([])

/** Ochiq katakcha — bitta model to'ldirilayotgan payt */
const editing = ref<DraftModel | null>(null)

const dialogOpen = ref(false)
const dialogBarcode = ref('')

/** Topilmagan kod: shu kod bilan yangi mahsulot taklif qilinadi */
const unknownCode = ref('')

/** Tasdiqlangandan keyingi xulosa va yorliqlar */
const summary = ref<{ purchase: Purchase; models: number; units: number } | null>(null)
const extraLabels = ref(0)

const search = ref<InstanceType<typeof ProductSearchField> | null>(null)
const strip = ref<InstanceType<typeof RecentModelsStrip> | null>(null)
const labels = ref<InstanceType<typeof LabelPrint> | null>(null)
const labelItems = ref<LabelItem[]>([])

const units = computed(() => draftUnits(models.value))
const total = computed(() => draftTotal(models.value))

const labelCount = computed(
  () => (summary.value?.units ?? 0) + Math.max(0, Number(extraLabels.value) || 0),
)

/** Saqlangan qoralamalar — forma ostidagi chiplar */
const drafts = computed(() => purchases.value.filter((item) => item.status === 'draft'))

function modelCount(purchase: Purchase): number {
  return new Set(purchase.lines.map((line) => line.product ?? line.variant)).size
}

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

function resetDraft() {
  draft.value = {
    id: null,
    number: '',
    date: todayIso(),
    supplier: null,
    note: '',
    amount_paid: '',
  }

  models.value = []
  editing.value = null
  dialogOpen.value = false
  dialogBarcode.value = ''
  unknownCode.value = ''
}

function clearDraft() {
  resetDraft()
  summary.value = null
  notice.value = ''
  search.value?.focus()
}

/** Saqlangan qoralamani davom ettirish: qatorlar modelga yig'iladi. */
async function editDraft(purchase: Purchase) {
  error.value = ''

  try {
    const full = await purchasesApi.get(purchase.id)

    resetDraft()

    draft.value = {
      id: full.id,
      number: full.number,
      date: full.date,
      supplier: full.supplier,
      note: full.note,
      amount_paid: Number(full.amount_paid) ? full.amount_paid : '',
    }

    const ids = [...new Set(full.lines.map((line) => line.product).filter(Boolean))] as number[]
    const products = await Promise.all(ids.map((id) => catalogApi.product(id)))

    models.value = products.map((product) =>
      modelFromLines(
        product,
        full.lines.filter((line) => line.product === product.id),
      ),
    )

    opened.value = null
    summary.value = null
    notice.value = `${full.number} qoralamasi ochildi.`
  } catch (err) {
    error.value = errorMessage(err, 'Qoralamani ochib bo‘lmadi.')
  }
}

/** Ro'yxatdan yoki tezkor qatordan model tanlandi — katakcha ochiladi. */
function onPick(product: Product) {
  unknownCode.value = ''
  summary.value = null

  const existing = models.value.find((model) => model.product === product.id)

  editing.value = existing ? cloneModel(existing) : emptyModel(product)
}

async function onPickId(id: number) {
  error.value = ''

  try {
    onPick(await catalogApi.product(id))
  } catch (err) {
    error.value = errorMessage(err, 'Modelni ochib bo‘lmadi.')
  }
}

/** Skanerlangan kod: variant topilsa, o'sha katakka bitta qo'shiladi. */
async function onScan(code: string) {
  error.value = ''
  unknownCode.value = ''

  try {
    const variant = await catalogApi.byBarcode(code)
    const product = await catalogApi.product(variant.product)

    const found = models.value.find((item) => item.product === product.id)
    const model = found ? cloneModel(found) : emptyModel(product)

    model.quantities[variant.id] = (model.quantities[variant.id] ?? 0) + 1

    summary.value = null
    editing.value = model
  } catch {
    // Kod noma'lum — do'konga birinchi marta kelgan tovar bo'lishi mumkin
    unknownCode.value = code
    search.value?.focus()
  }
}

function onModelSave(model: DraftModel) {
  const index = models.value.findIndex((item) => item.product === model.product)

  if (modelUnits(model) === 0) {
    // Katakcha bo'sh qoldi — model ro'yxatda turmaydi
    if (index !== -1) models.value.splice(index, 1)
  } else if (index === -1) {
    models.value.push(model)
  } else {
    models.value[index] = model
  }

  editing.value = null
  search.value?.focus()
}

function onModelClose() {
  editing.value = null
  search.value?.focus()
}

function openDialog(barcode = '') {
  dialogBarcode.value = barcode
  dialogOpen.value = true
  unknownCode.value = ''
  editing.value = null
}

/** Yangi mahsulot yaratildi — darhol katakcha ochiladi. */
function onCreated(product: Product, prices: { cost: string; markup: string }) {
  dialogOpen.value = false
  dialogBarcode.value = ''
  summary.value = null

  const model = emptyModel(product)

  model.cost = prices.cost
  model.markup = prices.markup

  // Bitta variantli mahsulot (skanerlangan kod) — dona darhol bittaga
  if (model.variants.length === 1) model.quantities[model.variants[0]!.id] = 1

  editing.value = model
  notice.value = `«${product.name}» yaratildi — nechta kelganini yozing.`

  void strip.value?.reload()
}

function removeModel(product: number) {
  models.value = models.value.filter((model) => model.product !== product)

  if (editing.value?.product === product) editing.value = null
}

function showSummary(purchase: Purchase) {
  summary.value = {
    purchase,
    models: modelCount(purchase),
    units: purchase.lines.reduce((sum, line) => sum + line.quantity, 0),
  }

  extraLabels.value = 0
}

async function onSave(confirmAfter: boolean) {
  const lines = draftLines(models.value)

  if (!lines.length || saving.value) return

  saving.value = true
  error.value = ''
  notice.value = ''

  const payload = {
    date: draft.value.date,
    supplier: draft.value.supplier,
    note: draft.value.note,
    amount_paid: draft.value.amount_paid
      ? normalizeMoneyInput(draft.value.amount_paid)
      : undefined,
    lines,
  }

  try {
    let purchase = draft.value.id
      ? await purchasesApi.update(draft.value.id, payload)
      : await purchasesApi.create(payload)

    if (confirmAfter) {
      purchase = await purchasesApi.confirm(purchase.id)
      showSummary(purchase)
    } else {
      notice.value = `${purchase.number} qoralama sifatida saqlandi — keyin davom ettirasiz.`
    }

    resetDraft()
    await load()
  } catch (err) {
    error.value = errorMessage(err, 'Kirimni saqlab bo‘lmadi.')
  } finally {
    saving.value = false
  }
}

/** Qatordagi hujjatni ochadi; qoralama esa formaga yuklanadi. */
async function open(purchase: Purchase) {
  error.value = ''

  if (purchase.status === 'draft') {
    await editDraft(purchase)
    return
  }

  try {
    opened.value = await purchasesApi.get(purchase.id)
    summary.value = null
  } catch (err) {
    error.value = errorMessage(err, 'Kirimni ochib bo‘lmadi.')
  }
}

async function onCancel(purchase: Purchase) {
  if (!window.confirm(`${purchase.number} bekor qilinsinmi? Tovar ombordan chiqariladi.`)) return

  try {
    const updated = await purchasesApi.cancel(purchase.id)

    notice.value = `${updated.number} bekor qilindi.`
    opened.value = updated
    summary.value = null
    await load()
  } catch (err) {
    error.value = errorMessage(err, 'Bekor qilib bo‘lmadi — qoldiq yetarli emas.')
  }
}

// --- Yorliqlar -------------------------------------------------------------

function itemsFor(lines: PurchaseLine[], extra = 0): LabelItem[] {
  const items = lines
    .filter((line) => line.barcode)
    .map((line) => ({
      barcode: line.barcode ?? '',
      name: line.product_name ?? '',
      label: line.variant_label ?? '',
      price: line.price ?? '0',
      quantity: line.quantity,
    }))

  // Qo'shimcha yorliqlar qatorlar bo'ylab navbat bilan taqsimlanadi:
  // bittasidan ortib, boshqasidan yetmay qolmasin
  for (let index = 0; index < extra && items.length; index += 1) {
    items[index % items.length]!.quantity += 1
  }

  return items
}

/** Yorliq chizilishini kutadi: shtrix-kod rasmi keyingi kadrda tayyor bo'ladi */
function sendToPrinter(items: LabelItem[]) {
  labelItems.value = items

  setTimeout(() => labels.value?.printLabels(), 50)
}

function printLines(lines: PurchaseLine[], extra = 0) {
  sendToPrinter(itemsFor(lines, extra))
}

/** Mahsulotning qoldiq tarixidan kelingan bo'lsa (`?open=<id>`) — o'sha kirim ochiladi */
onMounted(async () => {
  await load()

  const id = Number(route.query.open)

  if (!id) return

  try {
    opened.value = await purchasesApi.get(id)
  } catch (err) {
    error.value = errorMessage(err, 'Kirimni ochib bo‘lmadi.')
  }
})
</script>

<template>
  <section class="app-section active receiving">
    <!-- Sarlavha kartasi: ixcham, raqamlar birinchi ekranda qolsin -->
    <header class="receiving-header">
      <div>
        <span class="eyebrow">YANGI KOLLEKSIYA</span>
        <h2>Tovar qabul qilish</h2>
        <p>
          Kelgan tovarni model bo‘yicha kiriting: nomi, o‘lcham va rang bo‘yicha soni,
          tannarx. Tasdiqlagach yorliq chiqadi.
        </p>
      </div>

      <button class="button button-gradient new-product" type="button" @click="openDialog()">
        <svg><use href="#i-plus" /></svg>
        <span>Yangi mahsulot</span>
      </button>
    </header>

    <!-- Oxirgi qo'shilgan modellar: bir bosishda katakcha ochiladi -->
    <RecentModelsStrip ref="strip" @pick="onPickId" />

    <p v-if="error" class="load-error">{{ error }}</p>
    <p v-if="notice" class="notice">{{ notice }}</p>

    <!-- Kirim hujjati: sahifada doim ochiq -->
    <div v-if="!summary" class="table-card card-padded editor">
      <h3 class="card-title">Kirim hujjati</h3>

      <div class="editor-head">
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

        <div class="field narrow">
          <label>Sana</label>
          <input v-model="draft.date" type="date" />
        </div>
      </div>

      <p v-if="draft.id" class="field-hint draft-note">
        {{ draft.number }} qoralamasi davom ettirilmoqda.
      </p>

      <ProductSearchField ref="search" @scan="onScan" @pick="onPick" />

      <!-- Noma'lum kod: shu kod bilan mahsulot yaratish taklif qilinadi -->
      <p v-if="unknownCode" class="notice unknown" data-testid="unknown-barcode">
        <span>«{{ unknownCode }}» — bunday shtrix-kod do‘konda yo‘q.</span>

        <button class="button button-outline" type="button" @click="openDialog(unknownCode)">
          Shu kod bilan yangi mahsulot
        </button>
      </p>

      <PurchaseModelGrid
        v-if="editing"
        :key="editing.product"
        :model="editing"
        @save="onModelSave"
        @close="onModelClose"
      />

      <!-- Bo'sh holat -->
      <div v-if="!models.length" class="editor-empty">
        <svg aria-hidden="true"><use href="#i-bag" /></svg>
        <strong>Tovar qo‘shing</strong>
        <span>Nomini yozing yoki yangi mahsulot qo‘shing</span>
      </div>

      <table v-else class="data-table models-table">
        <thead>
          <tr>
            <th>Model</th>
            <th class="num">Dona</th>
            <th class="num">Tannarx</th>
            <th class="num">Summa</th>
            <th></th>
          </tr>
        </thead>

        <tbody>
          <tr v-for="model in models" :key="model.product">
            <td>
              <strong>{{ model.name }}</strong>
              <small class="cell-sub">
                {{ Object.keys(model.quantities).length }} ta o‘lcham/rang
              </small>
            </td>

            <td class="num">{{ modelUnits(model) }}</td>
            <td class="num">{{ formatMoney(model.cost || '0') }}</td>
            <td class="num">{{ formatMoney(modelTotal(model)) }}</td>

            <td class="num row-actions">
              <button class="button button-outline" type="button" @click="editing = model">
                Tahrirlash
              </button>

              <button
                class="icon-button delete"
                type="button"
                :aria-label="`${model.name}: o‘chirish`"
                @click="removeModel(model.product)"
              >
                <svg><use href="#i-trash" /></svg>
              </button>
            </td>
          </tr>
        </tbody>
      </table>

      <div class="editor-footer">
        <strong>Jami: {{ formatSum(total) }}</strong>
        <span v-if="units" class="editor-units">{{ units }} dona</span>

        <div class="editor-actions">
          <button
            class="button button-outline"
            type="button"
            :disabled="saving || !models.length"
            @click="onSave(false)"
          >
            Qoralama
          </button>

          <button class="button button-outline" type="button" @click="clearDraft">Tozalash</button>

          <button
            class="button button-gradient"
            type="button"
            :disabled="saving || !models.length"
            @click="onSave(true)"
          >
            {{ saving ? 'Saqlanmoqda…' : 'Tasdiqlash' }}
          </button>
        </div>
      </div>
    </div>

    <!-- Tasdiqlangandan keyin forma o'rnida xulosa turadi -->
    <div v-else class="table-card card-padded summary" data-testid="purchase-summary">
      <div class="summary-head">
        <h3 class="card-title">{{ summary.purchase.number }} tasdiqlandi — tovar omborga kirdi</h3>

        <button class="icon-button" type="button" aria-label="Yopish" @click="clearDraft">
          <svg><use href="#i-close" /></svg>
        </button>
      </div>

      <ul class="summary-grid">
        <li>
          <span>Model</span>
          <strong>{{ summary.models }}</strong>
        </li>

        <li>
          <span>Dona</span>
          <strong>{{ summary.units }}</strong>
        </li>

        <li>
          <span>Tannarx jami</span>
          <strong>{{ formatSum(summary.purchase.total) }}</strong>
        </li>

        <li>
          <span>Yorliq</span>
          <strong data-testid="label-count">{{ labelCount }}</strong>
        </li>
      </ul>

      <div class="summary-actions">
        <label class="field extra">
          <span>Qo‘shimcha yorliq</span>
          <input
            v-model.number="extraLabels"
            type="number"
            min="0"
            aria-label="Qo‘shimcha yorliq"
          />
        </label>

        <button
          class="button button-gradient"
          type="button"
          @click="printLines(summary.purchase.lines, extraLabels)"
        >
          <svg><use href="#i-print" /></svg>
          <span>Yorliqlarni chop etish ({{ labelCount }} ta)</span>
        </button>

        <button class="button button-outline" type="button" @click="clearDraft">
          Yangi kirim boshlash
        </button>
      </div>
    </div>

    <!-- Ochilgan hujjat -->
    <PurchaseDocument
      v-if="opened"
      :purchase="opened"
      @close="opened = null"
      @edit="editDraft"
      @print="printLines"
      @cancel="onCancel"
    />

    <!-- Oxirgi kirimlar -->
    <div class="table-card card-padded history">
      <h3 class="card-title">Oxirgi kirimlar</h3>

      <div class="table-scroll">
        <table class="data-table">
          <thead>
            <tr>
              <th>Hujjat</th>
              <th>Sana</th>
              <th>Xodim</th>
              <th class="num">Summa</th>
              <th>Holati</th>
              <th></th>
            </tr>
          </thead>

          <tbody>
            <tr v-if="loading">
              <td colspan="6" class="empty-state">Yuklanmoqda…</td>
            </tr>

            <tr v-else-if="!purchases.length">
              <td colspan="6" class="empty-state">Kirim hujjati yo‘q.</td>
            </tr>

            <tr
              v-for="purchase in purchases"
              v-else
              :key="purchase.id"
              class="clickable"
              :class="{ active: opened?.id === purchase.id }"
              @click="open(purchase)"
            >
              <td>
                <strong>{{ purchase.number }}</strong>
                <small class="cell-sub">{{ purchase.supplier_name ?? 'Ta’minotchisiz' }}</small>
              </td>

              <td>
                {{ formatDayMonth(purchase.date) }}
                <small class="cell-sub">{{ formatTime(purchase.created_at) }}</small>
              </td>

              <td>{{ purchase.created_by_name || '—' }}</td>

              <td class="num">
                {{ formatMoney(purchase.total) }}
                <!-- Qarz faqat ta'minotchili va to'lanmagan hujjatda -->
                <small v-if="Number(purchase.debt)" class="cell-sub">
                  Qarz: {{ formatMoney(purchase.debt) }}
                </small>
              </td>

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

              <td class="num">
                <button
                  class="icon-button"
                  type="button"
                  :aria-label="`${purchase.number}: ochish`"
                  @click.stop="open(purchase)"
                >
                  <svg><use href="#i-eye" /></svg>
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Qoralamalar -->
    <div v-if="drafts.length" class="table-card card-padded drafts">
      <h3 class="card-title">Qoralamalar</h3>

      <div class="draft-chips">
        <button
          v-for="item in drafts"
          :key="item.id"
          class="draft-chip"
          type="button"
          :aria-label="`${item.number} qoralamasi: ${modelCount(item)} model`"
          @click="editDraft(item)"
        >
          {{ formatDayMonth(item.date) }}, {{ formatTime(item.created_at) }} ·
          {{ modelCount(item) }} model
        </button>
      </div>
    </div>

    <ProductCreateDialog
      v-if="dialogOpen"
      :barcode="dialogBarcode || undefined"
      @created="onCreated"
      @close="dialogOpen = false"
    />

    <LabelPrint ref="labels" :items="labelItems" />
  </section>
</template>

<style scoped>
/* --- Sarlavha --- */

.receiving-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
  margin-bottom: 14px;
  padding: 16px 22px;
  border: 1px solid #ece2d2;
  border-radius: var(--radius-card);
  background: linear-gradient(110deg, #f3e8d7, #fdfaf4 70%);
}

.eyebrow {
  display: block;
  margin-bottom: 4px;
  color: var(--accent);
  font-size: 10px;
  letter-spacing: 2px;
}

.receiving-header h2 {
  font-family: var(--font-display);
  font-size: 27px;
  font-weight: 500;
  line-height: 1.15;
}

.receiving-header p {
  max-width: 62ch;
  margin-top: 4px;
  color: var(--text-secondary);
  font-size: 12px;
  line-height: 1.6;
}

.new-product {
  flex: none;
  min-height: 42px;
  padding: 0 18px;
  font-size: 14px;
}

/* --- Hujjat formasi --- */

.card-title {
  margin-bottom: 12px;
  font-family: var(--font-display);
  font-size: 21px;
  font-weight: 500;
}

.editor {
  margin-bottom: 12px;
}

.editor-head {
  display: grid;
  grid-template-columns: minmax(0, 1.4fr) minmax(0, 1fr) minmax(0, 1.4fr) 150px;
  gap: 10px;
  margin-bottom: 12px;
}

.draft-note {
  margin-bottom: 8px;
}

.unknown {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  margin-top: 10px;
}

.editor-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  padding: 28px 16px 24px;
  color: var(--text-muted);
  text-align: center;
}

.editor-empty svg {
  width: 30px;
  height: 30px;
  margin-bottom: 4px;
  fill: none;
  stroke: var(--gray-4);
  stroke-width: 1.2;
  stroke-linejoin: round;
}

.editor-empty strong {
  color: var(--text-secondary);
  font-size: 14px;
}

.editor-empty span {
  font-size: 12px;
}

.models-table {
  margin-top: 12px;
}

.editor-footer {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 10px;
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid var(--border);
}

.editor-footer strong {
  font-size: 18px;
  font-variant-numeric: tabular-nums;
}

.editor-units {
  color: var(--text-muted);
  font-size: 13px;
}

.editor-actions {
  display: flex;
  gap: 8px;
  margin-left: auto;
}

.row-actions .button {
  margin-left: 6px;
}

/* --- Xulosa --- */

.summary {
  margin-bottom: 12px;
}

.summary-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.summary-head .card-title {
  margin-bottom: 0;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 10px;
  margin: 12px 0 14px;
  padding: 0;
  list-style: none;
}

.summary-grid li {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 10px 12px;
  border: 1px solid var(--border);
  border-radius: var(--radius);
  background: var(--surface-soft);
}

.summary-grid span {
  color: var(--text-muted);
  font-size: 12px;
}

.summary-grid strong {
  font-size: 20px;
  font-variant-numeric: tabular-nums;
}

.summary-actions {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-end;
  gap: 10px;
}

.summary-actions .field.extra {
  width: 150px;
}

.summary-actions .field span {
  color: var(--text-secondary);
  font-size: 12px;
}

/* --- Tarix va qoralamalar --- */

.history,
.drafts {
  margin-bottom: 12px;
}

.clickable {
  cursor: pointer;
}

.clickable.active td {
  background: var(--accent-soft);
}

.draft-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.draft-chip {
  padding: 8px 14px;
  border: 1px solid var(--border-strong);
  border-radius: 999px;
  background: var(--surface);
  color: var(--text-secondary);
  font-size: 13px;
  cursor: pointer;
}

.draft-chip:hover {
  border-color: var(--accent);
  background: var(--accent-soft);
  color: var(--text);
}

@media (max-width: 1000px) {
  .editor-head {
    grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
  }
}

@media (max-width: 640px) {
  .receiving-header {
    flex-direction: column;
    align-items: flex-start;
  }

  .editor-actions {
    width: 100%;
    margin-left: 0;
  }

  .editor-actions .button {
    flex: 1;
  }
}
</style>
