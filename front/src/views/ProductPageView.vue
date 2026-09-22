<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'

import ImageGallery from '@/components/ImageGallery.vue'
import LabelPrint from '@/components/LabelPrint.vue'
import ProductForm from '@/components/ProductForm.vue'
import ProductImages from '@/components/ProductImages.vue'
import SizeStockLine from '@/components/SizeStockLine.vue'
import type { LabelItem } from '@/api/agent'
import { catalogApi } from '@/api/catalog'
import { errorMessage } from '@/api/client'
import { inventoryApi } from '@/api/inventory'
import { useAuthStore } from '@/stores/auth'
import { useToastStore } from '@/stores/toast'
import {
  colorStock,
  findVariant,
  galleryImages,
  initialColor,
  sizeOptions,
  type SizeOption,
} from '@/utils/catalog'
import { documentLabel, documentLink } from '@/utils/documents'
import { formatMoney, formatSum } from '@/utils/money'
import { stockLine } from '@/utils/stock'
import type { CatalogProduct, Product, StockMovement, Variant } from '@/types'

/**
 * Mahsulot sahifasi — tovar haqida hamma narsa bir joyda.
 *
 * Hamma ko'radi: rasmlar, rang va o'lcham bo'yicha qoldiq, shtrix-kod,
 * variantlar jadvali. Administrator bundan tashqari: tahrirlash, rasmlar,
 * yorliq, hisobdan chiqarish va variantning qoldiq tarixi.
 */

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const toast = useToastStore()

/** Ko'rsatish uchun: rasmlar rang bo'yicha, o'lchamlar tartibda */
const product = ref<CatalogProduct | null>(null)

/** Variantlarning to'liq ma'lumoti (SKU, eng kam qoldiq, tannarx) va tahrirlash */
const details = ref<Product | null>(null)

const loading = ref(true)
const error = ref('')

const colorId = ref<number | null>(null)
const sizeId = ref<number | null>(null)

const formOpen = ref(false)

const labelItems = ref<LabelItem[]>([])
const labels = ref<InstanceType<typeof LabelPrint> | null>(null)

async function load(keepSelection = false) {
  const id = Number(route.params.id)

  // Boshqa sahifaga o'tilganda parametr yo'qoladi — so'rov yuborilmaydi
  if (!id) return

  loading.value = true
  error.value = ''

  try {
    const [catalog, full] = await Promise.all([
      catalogApi.catalogProduct(id),
      catalogApi.product(id),
    ])

    product.value = catalog
    details.value = full

    if (!keepSelection) {
      colorId.value = initialColor(catalog)
      sizeId.value = null
    }
  } catch (err) {
    error.value = errorMessage(err, 'Mahsulotni yuklab bo‘lmadi.')
  } finally {
    loading.value = false
  }
}

watch(() => route.params.id, () => load(), { immediate: true })

/** Rasm qo'shilgach galereya yangilanadi, tanlov o'zgarmaydi */
async function refreshGallery() {
  if (product.value) product.value = await catalogApi.catalogProduct(product.value.id)
}

const selectedColor = computed(
  () => product.value?.colors.find((color) => color.id === colorId.value) ?? null,
)

const gallery = computed(() =>
  product.value ? galleryImages(product.value.image_groups, colorId.value) : [],
)

const sizes = computed(() => (product.value ? sizeOptions(product.value, colorId.value) : []))

const variant = computed(() =>
  product.value ? findVariant(product.value, sizeId.value, colorId.value) : null,
)

/** Variantlar jadvali — qoldiq sahifasidagi ustunlar */
const rows = computed<Variant[]>(() => details.value?.variants ?? [])

function selectColor(id: number) {
  colorId.value = id

  // Yangi rangda bu o'lcham tugagan bo'lsa tanlov bekor bo'ladi
  const option = sizes.value.find((item) => item.id === sizeId.value)

  if (!option?.quantity) sizeId.value = null
}

function selectSize(option: SizeOption) {
  if (!option.quantity) return

  sizeId.value = sizeId.value === option.id ? null : option.id
}

/** Jadvaldagi qator tanlansa — tepadagi rang va o'lcham ham o'shanga o'tadi.
 *  Qoldig'i yo'q variant ham tanlanadi: uning tarixi ham kerak bo'ladi. */
function selectRow(row: Variant) {
  colorId.value = row.color
  sizeId.value = row.size
}

function isLow(row: Variant) {
  return row.min_stock > 0 && row.stock_quantity <= row.min_stock
}

function goBack() {
  // Ro'yxatdan kelingan bo'lsa — o'sha joyga, havola orqali ochilgan bo'lsa — ro'yxatga
  if (window.history.state?.back) router.back()
  else void router.push('/products')
}

// --- Tahrirlash ------------------------------------------------------------

async function onSaved() {
  formOpen.value = false
  toast.show('Saqlandi')

  // O'lcham yoki rang qo'shilgan bo'lishi mumkin — tanlov qaytadan
  await load()
}

// --- Yorliq -----------------------------------------------------------------

/** Tanlangan variantga yoki tanlangan rangning hamma variantlariga yorliq. */
function printLabels() {
  const data = product.value

  if (!data) return

  const items = variant.value
    ? [variant.value]
    : data.variants.filter((item) => colorId.value === null || item.color === colorId.value)

  labelItems.value = items.map((item) => ({
    barcode: item.barcode,
    name: data.name,
    label: [item.size_name, item.color_name].filter(Boolean).join(' / '),
    price: item.price,
    quantity: 1,
  }))

  // Ro'yxat DOM ga chiqishi uchun keyingi kadrda
  setTimeout(() => labels.value?.printLabels(), 50)
}

// --- Hisobdan chiqarish -----------------------------------------------------

const writeOffOpen = ref(false)
const writeOffSaving = ref(false)
const writeOffError = ref('')
const writeOff = ref({ variant: 0, quantity: 1, reason: '' })

const writeOffRow = computed(() => rows.value.find((row) => row.id === writeOff.value.variant))

function openWriteOff() {
  writeOffError.value = ''
  writeOff.value = {
    variant: variant.value?.id ?? rows.value.find((row) => row.stock_quantity > 0)?.id ?? 0,
    quantity: 1,
    reason: '',
  }
  writeOffOpen.value = true
}

async function submitWriteOff() {
  const payload = writeOff.value

  if (!payload.variant || payload.quantity < 1 || !payload.reason.trim() || writeOffSaving.value) {
    return
  }

  writeOffSaving.value = true
  writeOffError.value = ''

  try {
    await inventoryApi.createWriteOff({
      variant: payload.variant,
      quantity: payload.quantity,
      reason: payload.reason.trim(),
    })

    writeOffOpen.value = false
    toast.show(`${payload.quantity} dona hisobdan chiqarildi`)

    await load(true)
    await loadHistory()
  } catch (err) {
    writeOffError.value = errorMessage(err, 'Hisobdan chiqarib bo‘lmadi.')
  } finally {
    writeOffSaving.value = false
  }
}

// --- Qoldiq tarixi (administrator) ------------------------------------------

const history = ref<StockMovement[]>([])
const historyPage = ref(1)
const historyMore = ref(false)
const historyLoading = ref(false)

let historyRequest = 0

async function loadHistory(more = false) {
  const id = variant.value?.id

  if (!auth.isAdmin || !id) {
    history.value = []
    historyMore.value = false
    return
  }

  const current = ++historyRequest
  const target = more ? historyPage.value + 1 : 1

  historyLoading.value = true

  try {
    const data = await inventoryApi.movements({ variant: id, page: target })

    if (current !== historyRequest) return

    history.value = more ? [...history.value, ...data.results] : data.results
    historyPage.value = target
    historyMore.value = Boolean(data.next)
  } catch {
    if (current === historyRequest) history.value = []
  } finally {
    if (current === historyRequest) historyLoading.value = false
  }
}

watch(() => variant.value?.id, () => loadHistory())

function when(value: string) {
  return new Date(value).toLocaleString('uz-UZ', {
    day: '2-digit',
    month: '2-digit',
    year: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}
</script>

<template>
  <section class="app-section active product-page">
    <button class="back-link" type="button" @click="goBack">‹ Mahsulotlar</button>

    <p v-if="error" class="load-error">{{ error }}</p>
    <p v-else-if="loading && !product" class="empty-state">Yuklanmoqda…</p>

    <template v-if="product">
      <div class="product-layout">
        <ImageGallery :images="gallery" :alt="product.name" />

        <div class="product-info">
          <p class="info-meta">
            {{ product.category_name }}<template v-if="product.brand"> · {{ product.brand }}</template>
          </p>

          <h2 class="info-name">{{ product.name }}</h2>

          <p class="info-price">{{ formatSum(variant?.price ?? product.sale_price) }}</p>

          <div v-if="auth.isAdmin" class="admin-actions">
            <!-- Shu tovar yana kelgan bo'lsa: qabul qilish ekrani darhol
                 shu modelning katakchasi bilan ochiladi -->
            <RouterLink class="button button-gradient" :to="`/purchases?model=${product.id}`">
              <svg><use href="#i-import" /></svg>
              <span>Yana keldi</span>
            </RouterLink>

            <button class="button button-outline" type="button" @click="formOpen = true">
              Tahrirlash
            </button>

            <button class="button button-outline" type="button" @click="printLabels">
              <svg><use href="#i-print" /></svg>
              <span>
                {{
                  variant
                    ? 'Yorliq chop etish'
                    : selectedColor
                      ? `${selectedColor.name} rangidagi yorliqlar`
                      : 'Yorliqlar'
                }}
              </span>
            </button>

            <button class="button button-outline danger" type="button" @click="openWriteOff">
              Hisobdan chiqarish
            </button>
          </div>

          <div v-if="product.colors.length" class="option-group">
            <p class="option-label">
              Rang: <strong>{{ selectedColor?.name }}</strong>
            </p>

            <div class="swatches" role="group" aria-label="Rang">
              <button
                v-for="color in product.colors"
                :key="color.id"
                class="swatch"
                :class="{ active: color.id === colorId, empty: !colorStock(product, color.id) }"
                type="button"
                :aria-pressed="color.id === colorId"
                @click="selectColor(color.id)"
              >
                <span class="swatch-dot" :style="{ background: color.hex_code }" />
                <span>{{ color.name }}</span>
                <small class="swatch-stock">{{ colorStock(product, color.id) }}</small>
              </button>
            </div>
          </div>

          <div v-if="product.sizes.length" class="option-group">
            <p class="option-label">
              O‘lcham<template v-if="selectedColor"> — {{ selectedColor.name }} rangida</template>
            </p>

            <div class="sizes" role="group" aria-label="O‘lcham">
              <!-- Tugagan o'lcham ham ro'yxatda qoladi, faqat tanlab bo'lmaydi -->
              <button
                v-for="option in sizes"
                :key="option.id"
                class="size-button"
                :class="{ active: option.id === sizeId }"
                type="button"
                :disabled="!option.quantity"
                :aria-pressed="option.id === sizeId"
                @click="selectSize(option)"
              >
                <span class="size-name">{{ option.name }}</span>
                <small>{{ option.quantity ? `${option.quantity} dona` : 'yo‘q' }}</small>
              </button>
            </div>
          </div>

          <!-- Hamma ranglar bo'yicha jami: rang tanlangan bo'lsa ham ko'rinib turadi -->
          <p class="all-colors" data-testid="all-colors">
            {{ product.colors.length ? 'Hamma ranglarda:' : 'Qoldiq:' }}
            <SizeStockLine v-if="product.size_stock.length" :entries="product.size_stock" />
            <strong class="all-total">jami {{ product.total_stock }} dona</strong>
          </p>

          <dl v-if="variant" class="variant-box">
            <div>
              <dt>Shtrix-kod</dt>
              <dd class="barcode-text">{{ variant.barcode }}</dd>
            </div>

            <div>
              <dt>Qoldiq</dt>
              <dd>
                {{ variant.stock_quantity }} dona
                <small class="cell-sub">{{ stockLine(variant) }}</small>
              </dd>
            </div>
          </dl>


          <dl v-if="product.material || product.care" class="details">
            <div v-if="product.material">
              <dt>Tarkibi</dt>
              <dd>{{ product.material }}</dd>
            </div>

            <div v-if="product.care">
              <dt>Parvarish</dt>
              <dd>{{ product.care }}</dd>
            </div>
          </dl>

          <p v-if="product.description" class="description">{{ product.description }}</p>
        </div>
      </div>

      <!-- Variantlar: ilgari "Qoldiq" sahifasidagi ustunlar -->
      <div class="table-card panel" data-testid="variants">
        <h3 class="panel-title">Variantlar</h3>

        <div class="table-scroll">
          <table class="data-table">
            <thead>
              <tr>
                <th>Variant</th>
                <th>SKU</th>
                <th>Shtrix-kod</th>
                <th class="num">Qoldiq</th>
                <th class="num">Eng kam</th>
                <th v-if="auth.isAdmin" class="num">Tannarx</th>
                <th class="num">Narx</th>
              </tr>
            </thead>

            <tbody>
              <tr
                v-for="row in rows"
                :key="row.id"
                class="clickable"
                :class="{ active: row.id === variant?.id }"
                @click="selectRow(row)"
              >
                <td>
                  {{ row.label || '—' }}
                  <span v-if="!row.is_active" class="pill pill-grey">faol emas</span>
                </td>
                <td>{{ row.sku }}</td>
                <td class="barcode-cell">{{ row.barcode }}</td>
                <td class="num">
                  <span :class="{ low: isLow(row) }">{{ row.stock_quantity }}</span>
                </td>
                <td class="num">{{ row.min_stock || '—' }}</td>
                <td v-if="auth.isAdmin" class="num">{{ formatMoney(row.average_cost ?? null) }}</td>
                <td class="num">{{ formatMoney(row.price) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <div v-if="auth.isAdmin" class="admin-panels">
        <!-- Qoldiq tarixi: tanlangan variant bo'yicha, hujjatga havola bilan -->
        <div class="table-card panel" data-testid="stock-history">
          <h3 class="panel-title">
            Qoldiq tarixi
            <small v-if="variant">{{ [variant.size_name, variant.color_name].filter(Boolean).join(' / ') || product.name }}</small>
          </h3>

          <p v-if="!variant" class="hint panel-hint">Variantni tanlang.</p>

          <div v-else class="table-scroll">
            <table class="data-table">
              <thead>
                <tr>
                  <th>Vaqti</th>
                  <th>Sabab</th>
                  <th>Joy</th>
                  <th class="num">Miqdor</th>
                  <th>Hujjat</th>
                  <th>Kim</th>
                </tr>
              </thead>

              <tbody>
                <tr v-if="historyLoading && !history.length">
                  <td colspan="6" class="empty-state">Yuklanmoqda…</td>
                </tr>

                <tr v-else-if="!history.length">
                  <td colspan="6" class="empty-state">Harakat yo‘q.</td>
                </tr>

                <tr v-for="movement in history" :key="movement.id">
                  <td>{{ when(movement.created_at) }}</td>
                  <td>{{ movement.reason_display }}</td>
                  <td>{{ movement.location_name }}</td>
                  <td class="num">
                    <span :class="movement.quantity > 0 ? 'plus' : 'minus'">
                      {{ movement.quantity > 0 ? `+${movement.quantity}` : movement.quantity }}
                    </span>
                  </td>
                  <td>
                    <RouterLink v-if="documentLink(movement)" :to="documentLink(movement)!">
                      {{ documentLabel(movement) }}
                    </RouterLink>
                    <span v-else class="muted">{{ documentLabel(movement) }}</span>
                  </td>
                  <td>{{ movement.user_name ?? '—' }}</td>
                </tr>
              </tbody>
            </table>
          </div>

          <button
            v-if="historyMore"
            class="button button-outline more"
            type="button"
            :disabled="historyLoading"
            @click="loadHistory(true)"
          >
            Yana ko‘rsatish
          </button>
        </div>

        <div class="table-card card-padded panel">
          <ProductImages
            :product-id="product.id"
            :colors="product.colors"
            @changed="refreshGallery"
          />
        </div>
      </div>
    </template>

    <ProductForm v-if="formOpen && details" :product="details" @saved="onSaved" @close="formOpen = false" />

    <!-- Hisobdan chiqarish -->
    <div v-if="writeOffOpen" class="overlay" @click.self="writeOffOpen = false">
      <div class="overlay-card" role="dialog" aria-modal="true" aria-label="Hisobdan chiqarish">
        <h3>Hisobdan chiqarish</h3>

        <p v-if="writeOffError" class="load-error">{{ writeOffError }}</p>

        <div class="field">
          <label>Variant</label>
          <select v-model.number="writeOff.variant">
            <option v-for="row in rows" :key="row.id" :value="row.id" :disabled="!row.stock_quantity">
              {{ row.label || product?.name }} — {{ row.stock_quantity }} dona
            </option>
          </select>
        </div>

        <div class="field">
          <label>Miqdor</label>
          <input
            v-model.number="writeOff.quantity"
            type="number"
            min="1"
            :max="writeOffRow?.stock_quantity ?? 1"
          />
        </div>

        <div class="field">
          <label>Sababi</label>
          <input v-model="writeOff.reason" type="text" placeholder="Yaroqsiz, yo‘qolgan…" />
          <small class="field-hint">
            Tovar qoldiqdan chiqadi va yo‘qotish sifatida hisobotda ko‘rinadi.
          </small>
        </div>

        <div class="form-actions">
          <button class="button button-outline" type="button" @click="writeOffOpen = false">
            Bekor qilish
          </button>

          <button
            class="button button-danger"
            type="button"
            :disabled="!writeOff.variant || !writeOff.reason.trim() || writeOffSaving"
            @click="submitWriteOff"
          >
            {{ writeOffSaving ? 'Saqlanmoqda…' : 'Hisobdan chiqarish' }}
          </button>
        </div>
      </div>
    </div>

    <LabelPrint ref="labels" :items="labelItems" />
  </section>
</template>

<style scoped>
.back-link {
  display: inline-flex;
  align-items: center;
  min-height: 40px;
  margin-bottom: 8px;
  padding: 0 4px;
  border: 0;
  background: none;
  color: var(--accent);
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
}

.product-layout {
  display: grid;
  grid-template-columns: minmax(0, 440px) minmax(0, 1fr);
  align-items: start;
  gap: 24px;
  margin-bottom: 16px;
}

.product-info {
  display: flex;
  flex-direction: column;
  gap: 14px;
  min-width: 0;
}

.info-meta {
  margin: 0;
  color: var(--text-muted);
  font-size: 14px;
}

/* Mahsulot nomi — sahifaning sarlavhasi, shuning uchun serifda */
.info-name {
  margin: 0;
  font-family: var(--font-display);
  font-size: 29px;
  font-weight: 500;
  line-height: 1.2;
}

.info-price {
  margin: 0;
  color: var(--accent);
  font-size: 24px;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
}

.admin-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.button.danger:hover:not(:disabled) {
  border-color: var(--red);
  color: var(--red);
}

.option-label {
  margin: 0 0 8px;
  color: var(--text-secondary);
  font-size: 14px;
}

.swatches,
.sizes {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.swatch {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  min-height: 44px;
  padding: 0 12px 0 8px;
  border: 1px solid var(--border-strong);
  border-radius: 999px;
  background: var(--surface);
  color: var(--text);
  font-size: 15px;
  cursor: pointer;
}

.swatch.active {
  border-color: var(--accent);
  box-shadow: 0 0 0 2px var(--accent-soft-2);
  font-weight: 600;
}

.swatch.empty {
  color: var(--text-muted);
}

/* Chegara — oq rang oq fonda ham ko'rinsin */
.swatch-dot {
  flex: none;
  width: 24px;
  height: 24px;
  border: 1px solid rgb(0 0 0 / 18%);
  border-radius: 50%;
}

.swatch-stock {
  color: var(--text-muted);
  font-variant-numeric: tabular-nums;
}

.size-button {
  display: inline-flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 2px;
  min-width: 64px;
  min-height: 52px;
  padding: 4px 10px;
  border: 1px solid var(--border-strong);
  border-radius: var(--radius);
  background: var(--surface);
  color: var(--text);
  cursor: pointer;
}

.size-name {
  font-size: 16px;
  font-weight: 600;
}

.size-button small {
  color: var(--text-muted);
  font-size: 12px;
}

.size-button.active {
  border-color: var(--accent);
  background: var(--accent-soft);
}

.size-button:disabled {
  border-style: dashed;
  background: var(--surface-soft);
  color: var(--gray-5);
  cursor: not-allowed;
}

.size-button:disabled .size-name {
  text-decoration: line-through;
}

.all-colors {
  margin: 0;
  padding: 8px 10px;
  border-radius: var(--radius);
  background: var(--surface-soft);
  color: var(--text-secondary);
  font-size: 14px;
}

.all-total {
  margin-left: 8px;
  color: var(--text);
  white-space: nowrap;
}

.variant-box {
  display: flex;
  flex-wrap: wrap;
  gap: 8px 24px;
  margin: 0;
  padding: 10px 12px;
  border: 1px solid var(--border);
  border-radius: var(--radius-card);
}

.variant-box dt,
.details dt {
  color: var(--text-muted);
  font-size: 13px;
}

.variant-box dd,
.details dd {
  margin: 2px 0 0;
  font-size: 15px;
}

.barcode-text {
  font-family: ui-monospace, Consolas, monospace;
  font-size: 17px;
  letter-spacing: 0.04em;
}

.hint {
  margin: 0;
  color: var(--text-muted);
  font-size: 14px;
}

.details {
  display: grid;
  gap: 10px;
  margin: 0;
}

.description {
  margin: 0;
  font-size: 15px;
  line-height: 1.6;
  white-space: pre-line;
}

/* --- Pastki panellar --- */

.panel {
  margin-bottom: 12px;
}

.panel-title {
  display: flex;
  align-items: baseline;
  gap: 8px;
  margin: 0;
  padding: 12px 14px 8px;
  font-size: 16px;
}

.panel-title small {
  color: var(--text-muted);
  font-size: 13px;
  font-weight: 400;
}

.panel-hint {
  padding: 0 14px 14px;
}

.admin-panels {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
  align-items: start;
  gap: 12px;
}

.clickable {
  cursor: pointer;
}

.clickable.active td {
  background: var(--accent-soft);
}

.barcode-cell {
  font-variant-numeric: tabular-nums;
}

.low {
  color: var(--red);
  font-weight: 700;
}

.plus {
  color: var(--green);
  font-weight: 600;
}

.minus {
  color: var(--red);
  font-weight: 600;
}

.muted {
  color: var(--text-muted);
}

.more {
  display: flex;
  margin: 8px auto 12px;
}

/* --- Hisobdan chiqarish oynasi --- */

.overlay {
  position: fixed;
  inset: 0;
  z-index: 50;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 16px;
  background: rgb(35 27 20 / 45%);
}

.overlay-card {
  width: 100%;
  max-width: 420px;
  padding: 20px;
  border-radius: var(--radius-card);
  background: var(--surface);
}

.overlay-card > .field {
  margin-bottom: 12px;
}

.form-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 16px;
}

@media (max-width: 1100px) {
  .admin-panels {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 760px) {
  .product-layout {
    grid-template-columns: 1fr;
    gap: 16px;
  }

  .admin-actions .button {
    flex: 1 1 140px;
    min-height: 44px;
  }
}
</style>
