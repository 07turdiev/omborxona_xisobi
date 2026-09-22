<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'

import LabelPrint from '@/components/LabelPrint.vue'
import NewProductPanel from '@/components/NewProductPanel.vue'
import PurchaseDocument from '@/components/PurchaseDocument.vue'
import PurchaseModelGrid from '@/components/PurchaseModelGrid.vue'
import { catalogApi } from '@/api/catalog'
import AmountField from '@/components/AmountField.vue'
import { errorMessage } from '@/api/client'
import { inventoryApi } from '@/api/inventory'
import { purchasesApi } from '@/api/purchases'
import { formatDayMonth, formatTime, todayIso } from '@/utils/date'
import { formatMoney, formatSum, normalizeMoneyInput } from '@/utils/money'
import {
  draftLines,
  draftTotal,
  draftUnits,
  emptyModel,
  modelFromLines,
  type DraftModel,
} from '@/utils/receiving'
import type { LabelItem } from '@/api/agent'
import type { Location, Product, Purchase, PurchaseLine, Supplier } from '@/types'

/**
 * Tovar qabul qilish — uch qadam.
 *
 *   1. Qanday tovar keldi. Do'konga keladigan tovarda shtrix-kod
 *      bo'lmaydi, shuning uchun u shu yerda tizimga kiritiladi.
 *   2. Nechtadan keldi — o'lcham × rang katakchasi va tannarx.
 *   3. Yorliq — har dona uchun bitta, yopishtirish uchun.
 *
 * Ekranda bir vaqtda bitta qadam turadi: xodim "endi nima qilaman"
 * degan savolga tushib qolmasin. Ta'minotchi, to'lov va sana kabi
 * buxgalteriya maydonlari «Qo'shimcha» ostida yashirin.
 */

const route = useRoute()

const purchases = ref<Purchase[]>([])
const suppliers = ref<Supplier[]>([])
const opened = ref<Purchase | null>(null)

const loading = ref(false)
const saving = ref(false)
const error = ref('')
const notice = ref('')

/** 1 — qanday tovar, 2 — nechtadan, 3 — yorliq */
const step = ref<1 | 2 | 3>(1)

/** Hujjat sarlavhasi. `id` — saqlangan qoralamani davom ettirish uchun. */
const draft = ref({
  id: null as number | null,
  number: '',
  date: todayIso(),
  supplier: null as number | null,
  /** Tovar qayerga tushadi: ombor yoki savdo zali */
  location: null as number | null,
  note: '',
  amount_paid: '',
})

const locations = ref<Location[]>([])

const models = ref<DraftModel[]>([])
const extraOpen = ref(false)

/** Qabul qilingandan keyingi xulosa va yorliqlar */
const summary = ref<{ purchase: Purchase; models: number; units: number } | null>(null)
const extraLabels = ref(0)

const labels = ref<InstanceType<typeof LabelPrint> | null>(null)
const labelItems = ref<LabelItem[]>([])

const units = computed(() => draftUnits(models.value))
const total = computed(() => draftTotal(models.value))

const labelCount = computed(
  () => (summary.value?.units ?? 0) + Math.max(0, Number(extraLabels.value) || 0),
)

/** Tugallanmagan qabullar — pastdagi chiplar */
const drafts = computed(() => purchases.value.filter((item) => item.status === 'draft'))

function modelCount(purchase: Purchase): number {
  return new Set(purchase.lines.map((line) => line.product ?? line.variant)).size
}

async function load() {
  loading.value = true
  error.value = ''

  try {
    const [page, supplierPage, places] = await Promise.all([
      purchasesApi.list(),
      purchasesApi.suppliers(),
      inventoryApi.locations(),
    ])

    purchases.value = page.results
    suppliers.value = supplierPage.results
    locations.value = places

    // Joy ro'yxati kelgach standart tanlov qo'yiladi
    draft.value.location ??= places.find((place) => place.kind === 'warehouse')?.id ?? null
  } catch (err) {
    error.value = errorMessage(err, 'Ro‘yxatni yuklab bo‘lmadi.')
  } finally {
    loading.value = false
  }
}

function reset() {
  draft.value = {
    id: null,
    number: '',
    date: todayIso(),
    supplier: null,
    // Odatda ombor: kelgan partiya zaxiraga qo'yiladi
    location: locations.value.find((place) => place.kind === 'warehouse')?.id ?? null,
    note: '',
    amount_paid: '',
  }

  models.value = []
  extraOpen.value = false
  step.value = 1
}

function startOver() {
  reset()
  summary.value = null
  notice.value = ''
  opened.value = null
}

// --- 1-qadam: qanday tovar keldi -------------------------------------------

/** Yangi tovar yaratildi — tannarxi bilan ikkinchi qadamga o'tadi. */
function onCreated(product: Product, prices: { cost: string; markup: string }) {
  const model = emptyModel(product)

  model.cost = prices.cost
  model.markup = prices.markup

  // Bitta variantli tovarda dona darhol bittaga qo'yiladi
  if (model.variants.length === 1) model.quantities[model.variants[0]!.id] = 1

  models.value.push(model)
  summary.value = null
  notice.value = ''
  step.value = 2
}

/** Shu tovar avval ham kelgan — yangisi yaratilmaydi. */
async function onExisting(product: Product) {
  error.value = ''

  try {
    const full = await catalogApi.product(product.id)

    if (!models.value.some((item) => item.product === full.id)) {
      models.value.push(emptyModel(full))
    }

    summary.value = null
    step.value = 2
  } catch (err) {
    error.value = errorMessage(err, 'Tovarni ochib bo‘lmadi.')
  }
}

// --- 2-qadam: nechtadan keldi ----------------------------------------------

function removeModel(product: number) {
  models.value = models.value.filter((model) => model.product !== product)

  if (!models.value.length) step.value = 1
}

function showSummary(purchase: Purchase) {
  summary.value = {
    purchase,
    models: modelCount(purchase),
    units: purchase.lines.reduce((sum, line) => sum + line.quantity, 0),
  }

  extraLabels.value = 0
  step.value = 3
}

async function save(confirmAfter: boolean) {
  const lines = draftLines(models.value)

  if (!lines.length || saving.value) return

  saving.value = true
  error.value = ''
  notice.value = ''

  const payload = {
    date: draft.value.date,
    supplier: draft.value.supplier,
    location: draft.value.location,
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
      reset()
      showSummary(purchase)
    } else {
      notice.value = `${purchase.number} saqlandi — keyin davom ettirasiz.`
      reset()
    }

    await load()
  } catch (err) {
    error.value = errorMessage(err, 'Saqlab bo‘lmadi.')
  } finally {
    saving.value = false
  }
}

// --- Tugallanmagan va tugallangan hujjatlar --------------------------------

/** Tugallanmagan qabulni davom ettirish: qatorlar katakchaga qaytadi. */
async function continueDraft(purchase: Purchase) {
  error.value = ''

  try {
    const full = await purchasesApi.get(purchase.id)

    reset()

    draft.value = {
      id: full.id,
      number: full.number,
      date: full.date,
      supplier: full.supplier,
      location: full.location,
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
    step.value = 2
    notice.value = `${full.number} davom ettirilmoqda.`
  } catch (err) {
    error.value = errorMessage(err, 'Ochib bo‘lmadi.')
  }
}

/** Tugallangani ko'rish uchun ochiladi, tugallanmagani esa davom etadi. */
async function open(purchase: Purchase) {
  error.value = ''

  if (purchase.status === 'draft') {
    await continueDraft(purchase)
    return
  }

  try {
    opened.value = await purchasesApi.get(purchase.id)
  } catch (err) {
    error.value = errorMessage(err, 'Ochib bo‘lmadi.')
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
function printLines(lines: PurchaseLine[], extra = 0) {
  labelItems.value = itemsFor(lines, extra)

  setTimeout(() => labels.value?.printLabels(), 50)
}

/**
 * Havoladan kelish:
 *   `?model=<id>` — tovar sahifasidagi «Yana keldi»;
 *   `?open=<id>`  — qoldiq tarixidagi hujjat havolasi.
 */
onMounted(async () => {
  await load()

  const model = Number(route.query.model)

  if (model) {
    try {
      const product = await catalogApi.product(model)

      models.value = [emptyModel(product)]
      step.value = 2
    } catch (err) {
      error.value = errorMessage(err, 'Tovarni ochib bo‘lmadi.')
    }

    return
  }

  const id = Number(route.query.open)

  if (!id) return

  try {
    opened.value = await purchasesApi.get(id)
  } catch (err) {
    error.value = errorMessage(err, 'Hujjatni ochib bo‘lmadi.')
  }
})
</script>

<template>
  <section class="app-section active receiving">
    <!-- Qadamlar: hozir qayerdaman. Sahifa nomi tepada turibdi,
         shuning uchun bu yerda takrorlanmaydi. -->
    <ol class="steps" data-testid="receiving-steps">
      <li :class="{ active: step === 1, done: step > 1 }">
        <span class="step-number">1</span>
        <span class="step-name">Qanday tovar</span>
      </li>

      <li :class="{ active: step === 2, done: step > 2 }">
        <span class="step-number">2</span>
        <span class="step-name">Nechtadan</span>
      </li>

      <li :class="{ active: step === 3 }">
        <span class="step-number">3</span>
        <span class="step-name">Yorliq</span>
      </li>
    </ol>

    <p v-if="error" class="load-error">{{ error }}</p>
    <p v-if="notice" class="notice">{{ notice }}</p>

    <!-- 1-qadam -->
    <div v-if="step === 1" class="table-card card-padded stage">
      <h3 class="card-title">Qanday tovar keldi?</h3>

      <NewProductPanel @created="onCreated" @existing="onExisting" />

      <p v-if="models.length" class="back-line">
        <button class="button button-outline" type="button" @click="step = 2">
          ‹ Kiritilganlarga qaytish ({{ models.length }})
        </button>
      </p>
    </div>

    <!-- 2-qadam -->
    <div v-else-if="step === 2" class="table-card card-padded stage" data-testid="step-quantities">
      <h3 class="card-title">Nechtadan keldi?</h3>

      <p v-if="draft.id" class="field-hint draft-note">{{ draft.number }}</p>

      <PurchaseModelGrid
        v-for="model in models"
        :key="model.product"
        :model="model"
        @remove="removeModel(model.product)"
      />

      <button class="button button-outline add-more" type="button" @click="step = 1">
        <svg><use href="#i-plus" /></svg>
        <span>Yana tovar qo‘shish</span>
      </button>

      <!-- Buxgalteriya maydonlari ko'rinib turmaydi: kerak bo'lsa ochiladi -->
      <div class="extra">
        <button
          class="button button-outline"
          type="button"
          :aria-expanded="extraOpen"
          @click="extraOpen = !extraOpen"
        >
          Qo‘shimcha
        </button>

        <div v-if="extraOpen" class="extra-fields">
          <div class="field">
            <label>Kim keltirdi</label>
            <select v-model="draft.supplier">
              <option :value="null">Ko‘rsatilmagan</option>
              <option v-for="item in suppliers" :key="item.id" :value="item.id">
                {{ item.name }}
              </option>
            </select>
          </div>

          <div class="field">
            <label>To‘langan summa</label>
            <AmountField v-model="draft.amount_paid" placeholder="0" />
          </div>

          <div class="field">
            <label>Izoh</label>
            <input v-model="draft.note" type="text" />
          </div>

          <div class="field">
            <label>Sana</label>
            <input v-model="draft.date" type="date" />
          </div>
        </div>
      </div>

      <footer class="stage-foot">
        <strong>Jami: {{ units }} dona · {{ formatSum(total) }}</strong>

        <label class="where">
          <span>Qayerga tushsin?</span>

          <select v-model="draft.location" aria-label="Qayerga tushsin">
            <option v-for="place in locations" :key="place.id" :value="place.id">
              {{ place.name }}
            </option>
          </select>
        </label>

        <div class="stage-actions">
          <button
            class="button button-outline"
            type="button"
            :disabled="saving || !units"
            @click="save(false)"
          >
            Keyinroq tugataman
          </button>

          <button
            class="button button-gradient big"
            type="button"
            :disabled="saving || !units"
            @click="save(true)"
          >
            {{ saving ? 'Saqlanmoqda…' : 'Qabul qilish' }}
          </button>
        </div>
      </footer>
    </div>

    <!-- 3-qadam -->
    <div v-else class="table-card card-padded stage" data-testid="purchase-summary">
      <h3 class="card-title">Qabul qilindi — endi yorliqlarni yopishtiring</h3>

      <ul v-if="summary" class="summary-grid">
        <li>
          <span>Tovar turi</span>
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

        <li>
          <span>Qayerda</span>
          <strong data-testid="summary-location">{{ summary.purchase.location_name }}</strong>
        </li>
      </ul>

      <div class="summary-actions">
        <label class="field extra-labels">
          <span>Qo‘shimcha yorliq</span>
          <input
            v-model.number="extraLabels"
            type="number"
            min="0"
            aria-label="Qo‘shimcha yorliq"
          />
        </label>

        <button
          v-if="summary"
          class="button button-gradient big"
          type="button"
          @click="printLines(summary.purchase.lines, extraLabels)"
        >
          <svg><use href="#i-print" /></svg>
          <span>Yorliqlarni chop etish ({{ labelCount }} ta)</span>
        </button>

        <button class="button button-outline" type="button" @click="startOver">
          Yana tovar qabul qilish
        </button>
      </div>
    </div>

    <!-- Tugallanmagan qabullar -->
    <div v-if="drafts.length" class="table-card card-padded drafts">
      <h3 class="card-title">Tugallanmagan</h3>

      <div class="draft-chips">
        <button
          v-for="item in drafts"
          :key="item.id"
          class="draft-chip"
          type="button"
          :aria-label="`${item.number} qoralamasi: ${modelCount(item)} model`"
          @click="continueDraft(item)"
        >
          {{ formatDayMonth(item.date) }}, {{ formatTime(item.created_at) }} ·
          {{ modelCount(item) }} tovar
        </button>
      </div>
    </div>

    <!-- Ochilgan hujjat -->
    <PurchaseDocument
      v-if="opened"
      :purchase="opened"
      @close="opened = null"
      @edit="continueDraft"
      @print="printLines"
      @cancel="onCancel"
    />

    <!-- Oxirgi qabul qilinganlar -->
    <div class="table-card card-padded history">
      <h3 class="card-title">Oxirgi qabul qilinganlar</h3>

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
              <td colspan="6" class="empty-state">Hali tovar qabul qilinmagan.</td>
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
                <small class="cell-sub">{{ purchase.supplier_name ?? 'Ko‘rsatilmagan' }}</small>
              </td>

              <td>
                {{ formatDayMonth(purchase.date) }}
                <small class="cell-sub">{{ formatTime(purchase.created_at) }}</small>
              </td>

              <td>{{ purchase.created_by_name || '—' }}</td>

              <td class="num">
                {{ formatMoney(purchase.total) }}
                <!-- Qarz faqat keltirgani ko'rsatilgan va to'lanmagan hujjatda -->
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

    <LabelPrint ref="labels" :items="labelItems" />
  </section>
</template>

<style scoped>
/* --- Qadamlar --- */

.steps {
  display: flex;
  gap: 8px;
  margin-bottom: 14px;
  padding: 0;
  list-style: none;
}

.steps li {
  display: flex;
  flex: 1;
  align-items: center;
  gap: 10px;
  padding: 12px 16px;
  border: 1px solid var(--border);
  border-radius: var(--radius-card);
  background: var(--surface);
  color: var(--text-muted);
  font-size: 15px;
}

.steps li.active {
  border-color: var(--accent);
  background: var(--accent-soft);
  color: var(--text);
  font-weight: 600;
}

.steps li.done {
  color: var(--text-secondary);
}

.step-number {
  display: grid;
  place-items: center;
  width: 30px;
  height: 30px;
  border-radius: 50%;
  background: var(--gray-1);
  color: var(--text-secondary);
  font-size: 15px;
  font-weight: 600;
}

.steps li.active .step-number {
  background: var(--accent);
  color: var(--accent-text);
}

.steps li.done .step-number {
  background: var(--accent-soft-2);
  color: var(--accent-strong);
}

/* --- Qadam mazmuni --- */

.stage {
  margin-bottom: 12px;
}

.card-title {
  margin-bottom: 14px;
  font-family: var(--font-display);
  font-size: 23px;
  font-weight: 500;
}

.back-line {
  margin-top: 14px;
}

.draft-note {
  margin-bottom: 10px;
}

.add-more {
  margin: 4px 0 14px;
}

.extra {
  margin-bottom: 14px;
}

.extra-fields {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 10px;
  margin-top: 10px;
}

.stage-foot {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 12px;
  padding-top: 14px;
  border-top: 1px solid var(--border);
}

.stage-foot strong {
  font-size: 19px;
  font-variant-numeric: tabular-nums;
}

.stage-actions {
  display: flex;
  gap: 8px;
  margin-left: auto;
}

.big {
  min-height: 48px;
  padding: 0 24px;
  font-size: 16px;
}

/* --- Xulosa --- */

.summary-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 10px;
  margin: 0 0 16px;
  padding: 0;
  list-style: none;
}

.summary-grid li {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 12px 14px;
  border: 1px solid var(--border);
  border-radius: var(--radius);
  background: var(--surface-soft);
}

.summary-grid span {
  color: var(--text-muted);
  font-size: 13px;
}

.summary-grid strong {
  font-size: 22px;
  font-variant-numeric: tabular-nums;
}

.summary-actions {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-end;
  gap: 10px;
}

.summary-actions .field.extra-labels {
  width: 160px;
}

.summary-actions .field span {
  color: var(--text-secondary);
  font-size: 13px;
}

/* --- Pastki bo'limlar --- */

.drafts,
.history {
  margin-bottom: 12px;
}

.where {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
}

.where select {
  width: auto;
}

.draft-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.draft-chip {
  padding: 10px 16px;
  border: 1px solid var(--border-strong);
  border-radius: 999px;
  background: var(--surface);
  color: var(--text-secondary);
  font-size: 14px;
  cursor: pointer;
}

.draft-chip:hover {
  border-color: var(--accent);
  background: var(--accent-soft);
  color: var(--text);
}

.clickable {
  cursor: pointer;
}

.clickable.active td {
  background: var(--accent-soft);
}

@media (max-width: 720px) {
  .steps li:not(.active) .step-name {
    display: none;
  }

  .stage-actions {
    width: 100%;
    margin-left: 0;
  }

  .stage-actions .button {
    flex: 1;
  }
}
</style>
