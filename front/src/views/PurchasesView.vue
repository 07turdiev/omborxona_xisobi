<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'

import LabelPrint from '@/components/LabelPrint.vue'
import ProductQuickForm from '@/components/ProductQuickForm.vue'
import ProductSearchField from '@/components/ProductSearchField.vue'
import PurchaseModelGrid from '@/components/PurchaseModelGrid.vue'
import { catalogApi } from '@/api/catalog'
import { errorMessage } from '@/api/client'
import { purchasesApi } from '@/api/purchases'
import { formatDate, todayIso } from '@/utils/date'
import { formatMoney, formatSum, multiplyMoney, normalizeMoneyInput } from '@/utils/money'
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
 * Tovar shtrix-kodsiz keladi, shuning uchun ekranning markazida bitta
 * maydon turadi — u skanerni ham, nom bo'yicha qidiruvni ham tushunadi.
 * Tanlangan model o'lcham × rang katakchasi bo'lib ochiladi va dona
 * shu yerga yoziladi. Yangi model ham shu yerda yaratiladi: mahsulotlar
 * sahifasiga o'tish shart emas.
 */

const route = useRoute()

const purchases = ref<Purchase[]>([])
const suppliers = ref<Supplier[]>([])
const opened = ref<Purchase | null>(null)

const loading = ref(false)
const saving = ref(false)
const error = ref('')
const notice = ref('')

const editorOpen = ref(false)

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

const quickOpen = ref(false)
const quickBarcode = ref('')

/** Topilmagan kod: shu kod bilan yangi mahsulot taklif qilinadi */
const unknownCode = ref('')

/** Tasdiqlangandan keyingi xulosa va yorliqlar */
const summary = ref<{ purchase: Purchase; models: number; units: number } | null>(null)
const extraLabels = ref(0)

const search = ref<InstanceType<typeof ProductSearchField> | null>(null)
const labels = ref<InstanceType<typeof LabelPrint> | null>(null)
const labelItems = ref<LabelItem[]>([])

const units = computed(() => draftUnits(models.value))
const total = computed(() => draftTotal(models.value))

const labelCount = computed(
  () => (summary.value?.units ?? 0) + Math.max(0, Number(extraLabels.value) || 0),
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

function resetEditor() {
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
  quickOpen.value = false
  quickBarcode.value = ''
  unknownCode.value = ''
}

function openEditor() {
  resetEditor()
  editorOpen.value = true
  opened.value = null
  summary.value = null
  search.value?.focus()
}

/** Saqlangan qoralamani davom ettirish: qatorlar modelga yig'iladi. */
async function editDraft(purchase: Purchase) {
  error.value = ''

  try {
    const full = await purchasesApi.get(purchase.id)

    resetEditor()

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

    editorOpen.value = true
    opened.value = null
    summary.value = null
  } catch (err) {
    error.value = errorMessage(err, 'Qoralamani ochib bo‘lmadi.')
  }
}

/** Ro'yxatdan model tanlandi — katakcha ochiladi (avval kiritilgani bilan). */
function onPick(product: Product) {
  unknownCode.value = ''
  quickOpen.value = false

  const existing = models.value.find((model) => model.product === product.id)

  editing.value = existing ?? emptyModel(product)
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

function openQuick(barcode = '') {
  quickBarcode.value = barcode
  quickOpen.value = true
  unknownCode.value = ''
  editing.value = null
}

/** Yangi mahsulot yaratildi — darhol katakcha ochiladi. */
function onQuickCreated(product: Product) {
  quickOpen.value = false
  quickBarcode.value = ''

  const model = emptyModel(product)

  // Bitta variantli mahsulot (skanerlangan kod) — dona darhol bittaga
  if (model.variants.length === 1) model.quantities[model.variants[0]!.id] = 1

  editing.value = model
  notice.value = `«${product.name}» yaratildi — nechta kelganini yozing.`
}

function removeModel(product: number) {
  models.value = models.value.filter((model) => model.product !== product)

  if (editing.value?.product === product) editing.value = null
}

function showSummary(purchase: Purchase) {
  summary.value = {
    purchase,
    models: new Set(purchase.lines.map((line) => line.product ?? line.variant)).size,
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
      notice.value = ''
    } else {
      notice.value = `${purchase.number} qoralama sifatida saqlandi — keyin davom ettirasiz.`
      opened.value = purchase
    }

    editorOpen.value = false
    resetEditor()
    await load()
  } catch (err) {
    error.value = errorMessage(err, 'Kirimni saqlab bo‘lmadi.')
  } finally {
    saving.value = false
  }
}

async function onConfirm(purchase: Purchase) {
  error.value = ''

  try {
    const updated = await purchasesApi.confirm(purchase.id)

    showSummary(updated)
    opened.value = null
    await load()
  } catch (err) {
    error.value = errorMessage(err, 'Tasdiqlab bo‘lmadi.')
  }
}

/** Qatordagi kirimni ochadi: qatorlari, yorliq va bekor qilish pastda. */
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

async function printLabels(purchase: Purchase, extra = 0) {
  const full = purchase.lines.length ? purchase : await purchasesApi.get(purchase.id)

  sendToPrinter(itemsFor(full.lines, extra))
}

/** Bitta qatorni qayta chop etish: yorliq yirtilsa yoki yo'qolsa. */
function printLine(line: PurchaseLine) {
  sendToPrinter(itemsFor([line]))
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

      <p v-if="draft.id" class="field-hint draft-note">
        {{ draft.number }} qoralamasi davom ettirilmoqda.
      </p>

      <div class="editor-search">
        <ProductSearchField ref="search" @scan="onScan" @pick="onPick" />

        <button class="button button-outline" type="button" @click="openQuick()">
          <svg><use href="#i-plus" /></svg>
          <span>Yangi mahsulot</span>
        </button>
      </div>

      <!-- Noma'lum kod: shu kod bilan mahsulot yaratish taklif qilinadi -->
      <p v-if="unknownCode" class="notice unknown" data-testid="unknown-barcode">
        <span>«{{ unknownCode }}» — bunday shtrix-kod do‘konda yo‘q.</span>

        <button class="button button-outline" type="button" @click="openQuick(unknownCode)">
          Shu kod bilan yangi mahsulot
        </button>
      </p>

      <ProductQuickForm
        v-if="quickOpen"
        :barcode="quickBarcode || undefined"
        @created="onQuickCreated"
        @close="quickOpen = false"
      />

      <PurchaseModelGrid
        v-if="editing"
        :key="editing.product"
        :model="editing"
        @save="onModelSave"
        @close="onModelClose"
      />

      <table class="data-table models-table">
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
          <tr v-if="!models.length">
            <td colspan="5" class="empty-state">
              Tovarni skanerlang, nomini yozing yoki «Yangi mahsulot» tugmasini bosing.
            </td>
          </tr>

          <tr v-for="model in models" v-else :key="model.product">
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
        <strong>{{ units }} dona · {{ formatSum(total) }}</strong>

        <div class="editor-actions">
          <button class="button button-outline" type="button" @click="editorOpen = false">
            Bekor qilish
          </button>

          <button
            class="button button-outline"
            type="button"
            :disabled="saving"
            @click="onSave(false)"
          >
            Qoralama
          </button>

          <button
            class="button button-gradient"
            type="button"
            :disabled="saving"
            @click="onSave(true)"
          >
            {{ saving ? 'Saqlanmoqda…' : 'Saqlash va tasdiqlash' }}
          </button>
        </div>
      </div>
    </div>

    <!-- Tasdiqlangandan keyingi xulosa va yorliqlar -->
    <div v-if="summary" class="table-card card-padded summary" data-testid="purchase-summary">
      <div class="opened-head">
        <h3>{{ summary.purchase.number }} tasdiqlandi — tovar omborga kirdi</h3>

        <button class="icon-button" type="button" aria-label="Yopish" @click="summary = null">
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
          @click="printLabels(summary.purchase, extraLabels)"
        >
          <svg><use href="#i-print" /></svg>
          <span>Yorliqlarni chop etish ({{ labelCount }} ta)</span>
        </button>
      </div>
    </div>

    <!-- Ochilgan kirim: mahsulotning qoldiq tarixidagi havoladan (`?open=<id>`)
         yoki bekor qilish natijasi -->
    <div v-if="opened" class="table-card card-padded opened" data-testid="opened-purchase">
      <div class="opened-head">
        <h3>
          {{ opened.number }}
          <span
            class="pill"
            :class="{
              'pill-green': opened.status === 'confirmed',
              'pill-red': opened.status === 'cancelled',
              'pill-grey': opened.status === 'draft',
            }"
          >
            {{ opened.status_display }}
          </span>
        </h3>

        <button class="icon-button" type="button" aria-label="Yopish" @click="opened = null">
          <svg><use href="#i-close" /></svg>
        </button>
      </div>

      <p class="opened-meta">
        {{ formatDate(opened.date) }} · {{ opened.supplier_name ?? 'Ta’minotchisiz' }} ·
        {{ formatSum(opened.total) }}
      </p>

      <table class="data-table">
        <thead>
          <tr>
            <th>Tovar</th>
            <th class="num">Soni</th>
            <th class="num">Tannarx</th>
            <th class="num">Summa</th>
            <th></th>
          </tr>
        </thead>

        <tbody>
          <tr v-for="line in opened.lines" :key="line.id ?? line.variant">
            <td>
              {{ line.product_name }}
              <small class="cell-sub">{{ line.variant_label || line.sku }}</small>
            </td>
            <td class="num">{{ line.quantity }}</td>
            <td class="num">{{ formatMoney(line.unit_cost) }}</td>
            <td class="num">
              {{ formatMoney(line.line_total ?? multiplyMoney(line.unit_cost, line.quantity)) }}
            </td>

            <td class="num">
              <!-- Yorliq yirtilsa, faqat shu qatorni qayta chiqarish mumkin -->
              <button
                v-if="opened.status === 'confirmed' && line.barcode"
                class="icon-button"
                type="button"
                :aria-label="`${line.product_name} ${line.variant_label}: yorliqni qayta chop etish`"
                @click="printLine(line)"
              >
                <svg><use href="#i-print" /></svg>
              </button>
            </td>
          </tr>
        </tbody>
      </table>

      <div v-if="opened.status === 'confirmed'" class="opened-actions">
        <button class="button button-outline" type="button" @click="printLabels(opened)">
          <svg><use href="#i-print" /></svg>
          <span>Yorliqlar chop etish</span>
        </button>
      </div>

      <!-- Bekor qilish chop etishdan ataylab ajratilgan: tasodifan
           bosilmasin, oqibati esa oldindan yozilgan -->
      <div v-if="opened.status === 'confirmed'" class="danger-zone">
        <div>
          <strong>Kirimni bekor qilish</strong>
          <small>Tovar ombordan chiqariladi, hujjat tarixda qoladi.</small>
        </div>

        <button class="button button-danger" type="button" @click="onCancel(opened)">
          Bekor qilish
        </button>
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

            <tr
              v-for="purchase in purchases"
              v-else
              :key="purchase.id"
              class="clickable"
              :class="{ active: opened?.id === purchase.id }"
              @click="open(purchase)"
            >
              <td><strong>{{ purchase.number }}</strong></td>
              <td>{{ formatDate(purchase.date) }}</td>
              <td>{{ purchase.supplier_name ?? 'Ta’minotchisiz' }}</td>
              <td class="num">{{ formatMoney(purchase.total) }}</td>
              <!-- Ta'minotchisiz va bekor qilingan kirimda qarz bo'lmaydi -->
              <td class="num">{{ Number(purchase.debt) ? formatMoney(purchase.debt) : '—' }}</td>
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
                  @click.stop="onConfirm(purchase)"
                >
                  Tasdiqlash
                </button>

                <!-- Bekor qilish qatorda emas: u hujjatni ochib, chop etish
                     tugmasidan ajratilgan holda turadi -->
                <button
                  v-if="purchase.status === 'confirmed'"
                  class="button button-outline"
                  type="button"
                  @click.stop="printLabels(purchase)"
                >
                  <svg><use href="#i-print" /></svg>
                  <span>Yorliqlar</span>
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

.draft-note {
  margin-bottom: 8px;
}

.editor-search {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 10px;
}

.editor-search .button {
  height: 44px;
  white-space: nowrap;
}

.unknown {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}

.models-table {
  margin-top: 4px;
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
  font-variant-numeric: tabular-nums;
}

.editor-actions {
  display: flex;
  gap: 8px;
}

.row-actions .button {
  margin-left: 6px;
}

.summary {
  margin-bottom: 12px;
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 10px;
  margin: 10px 0 14px;
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

.opened {
  margin-bottom: 12px;
}

.opened-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.opened-head h3 {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 0;
}

.opened-meta {
  margin: 4px 0 10px;
  color: var(--text-muted);
  font-size: 13px;
}

.opened-actions {
  display: flex;
  gap: 8px;
  margin-top: 12px;
}

.danger-zone {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-top: 16px;
  padding: 12px;
  border: 1px solid var(--red);
  border-radius: var(--radius);
  background: var(--red-soft);
}

.danger-zone strong {
  display: block;
  font-size: 13px;
}

.danger-zone small {
  color: var(--text-secondary);
  font-size: 12px;
}

.clickable {
  cursor: pointer;
}

.clickable.active td {
  background: var(--accent-soft);
}
</style>
