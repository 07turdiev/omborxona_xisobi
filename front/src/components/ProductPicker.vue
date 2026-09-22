<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'

import { catalogApi } from '@/api/catalog'
import { errorMessage } from '@/api/client'
import { formatMoney } from '@/utils/money'
import { shopStock, warehouseStock } from '@/utils/stock'
import type { CatalogCard, CatalogVariant, Category, Product, Variant } from '@/types'

/**
 * Kassadagi tovar tanlagich.
 *
 * Yorliq yirtilgan yoki o'qilmaydigan bo'lsa, kassir skanersiz ham sota
 * olishi kerak: rasmli plitkadan tovar tanlanadi, bir nechta varianti
 * bo'lsa o'lcham × rang katakchasi ochiladi va qoldiq ko'rinib turadi.
 */

const emit = defineEmits<{ pick: [variant: Variant] }>()

const search = ref('')
const category = ref('')

const cards = ref<CatalogCard[]>([])
const categories = ref<Category[]>([])
const loading = ref(false)
const error = ref('')

/** Variantlari ko'p tovar tanlanganda ochiladigan katakcha */
const chosen = ref<Product | null>(null)
const opening = ref(false)

let request = 0
let timer: ReturnType<typeof setTimeout> | undefined

async function load() {
  const current = ++request

  loading.value = true
  error.value = ''

  try {
    const data = await catalogApi.catalog({
      search: search.value.trim() || undefined,
      category: category.value || undefined,
      // Kassada faqat sotiladigan tovar kerak
      in_stock: 'true',
      ordering: 'name',
    })

    if (current !== request) return

    cards.value = data.results
  } catch (err) {
    if (current === request) error.value = errorMessage(err, 'Tovarlarni yuklab bo‘lmadi.')
  } finally {
    if (current === request) loading.value = false
  }
}

watch(search, () => {
  clearTimeout(timer)
  timer = setTimeout(load, 250)
})

watch(category, () => void load())

onMounted(async () => {
  try {
    categories.value = await catalogApi.categories()
  } catch {
    // Kategoriya filtrisiz ham ishlaydi
  }

  await load()
})

/** Plitka bosilganda: yagona variant darhol savatga, aks holda katakcha. */
async function choose(card: CatalogCard) {
  if (opening.value) return

  opening.value = true
  error.value = ''

  try {
    const product = await catalogApi.product(card.id)
    const sellable = product.variants.filter((variant) => variant.is_active)

    if (sellable.length === 1) {
      emit('pick', sellable[0]!)
      return
    }

    chosen.value = product
  } catch (err) {
    error.value = errorMessage(err, 'Tovarni ochib bo‘lmadi.')
  } finally {
    opening.value = false
  }
}

const sizes = computed(() => {
  const seen = new Map<number | null, string>()

  for (const variant of chosen.value?.variants ?? []) {
    if (!seen.has(variant.size)) seen.set(variant.size, variant.size_name ?? '—')
  }

  return [...seen].map(([id, name]) => ({ id, name }))
})

const colors = computed(() => {
  const seen = new Map<number | null, string>()

  for (const variant of chosen.value?.variants ?? []) {
    if (!seen.has(variant.color)) seen.set(variant.color, variant.color_name ?? '—')
  }

  return [...seen].map(([id, name]) => ({ id, name }))
})

function cell(size: number | null, color: number | null) {
  return chosen.value?.variants.find(
    (variant) => variant.size === size && variant.color === color,
  )
}

/** Zalda yo'q, lekin omborda bor — kassa uni olib chiqishni taklif qiladi */
function onlyInWarehouse(variant?: CatalogVariant | Variant): boolean {
  return Boolean(variant) && shopStock(variant!) < 1 && warehouseStock(variant!) > 0
}

function cellLabel(size: string, color: string, variant?: CatalogVariant | Variant): string {
  if (!variant) return `${size} ${color}: 0 dona`

  const warehouse = warehouseStock(variant)
  const tail = warehouse ? `, omborda ${warehouse}` : ''

  return `${size} ${color}: ${shopStock(variant)} dona${tail}`
}

function take(variant: Variant | undefined) {
  if (!variant || variant.stock_quantity < 1) return

  emit('pick', variant)
  chosen.value = null
}
</script>

<template>
  <div class="picker">
    <div class="picker-filters">
      <input
        v-model="search"
        class="picker-search"
        type="search"
        autocomplete="off"
        placeholder="Tovar nomi…"
        aria-label="Tovar qidirish"
        @keydown.enter.prevent="load"
      />

      <select v-model="category" aria-label="Kategoriya">
        <option value="">Hammasi</option>
        <option v-for="item in categories" :key="item.id" :value="String(item.id)">
          {{ item.name }}
        </option>
      </select>
    </div>

    <p v-if="error" class="picker-error">{{ error }}</p>

    <div class="tiles">
      <button
        v-for="card in cards"
        :key="card.id"
        class="tile"
        type="button"
        :disabled="opening"
        @click="choose(card)"
      >
        <span class="tile-image">
          <img
            v-if="card.primary_image"
            :src="card.primary_image.thumb"
            alt=""
            loading="lazy"
            decoding="async"
            width="200"
            height="200"
          />
          <svg v-else aria-hidden="true"><use href="#i-image" /></svg>
        </span>

        <span class="tile-name">{{ card.name }}</span>
        <span class="tile-price">{{ formatMoney(card.sale_price) }}</span>
        <span class="tile-stock">
          Zalda {{ card.shop_stock ?? card.total_stock }}
          <template v-if="card.warehouse_stock"> · omborda {{ card.warehouse_stock }}</template>
        </span>
      </button>
    </div>

    <p v-if="!loading && !cards.length" class="picker-empty">
      {{ search ? 'Tovar topilmadi.' : 'Qoldig‘i bor tovar yo‘q.' }}
    </p>

    <!-- O'lcham × rang: qaysi katakda nechta qolgani ko'rinadi -->
    <div v-if="chosen" class="variant-overlay" @click.self="chosen = null">
      <div class="variant-card" role="dialog" aria-modal="true" :aria-label="chosen.name">
        <div class="variant-head">
          <h3>{{ chosen.name }}</h3>
          <button class="icon-button" type="button" aria-label="Yopish" @click="chosen = null">
            <svg><use href="#i-close" /></svg>
          </button>
        </div>

        <div class="variant-scroll">
          <table class="variant-grid">
            <thead>
              <tr>
                <th></th>
                <th v-for="color in colors" :key="String(color.id)">{{ color.name }}</th>
              </tr>
            </thead>

            <tbody>
              <tr v-for="size in sizes" :key="String(size.id)">
                <th>{{ size.name }}</th>

                <td v-for="color in colors" :key="String(color.id)">
                  <!-- Katakdagi son — zaldagi qoldiq. Zalda yo'q, lekin
                       omborda bor bo'lsa, katak baribir bosiladi: kassa
                       ombordan olib chiqishni taklif qiladi. -->
                  <button
                    class="variant-cell"
                    :class="{ 'from-warehouse': onlyInWarehouse(cell(size.id, color.id)) }"
                    type="button"
                    :disabled="!cell(size.id, color.id)?.stock_quantity"
                    :aria-label="cellLabel(size.name, color.name, cell(size.id, color.id))"
                    @click="take(cell(size.id, color.id))"
                  >
                    {{ cell(size.id, color.id) ? shopStock(cell(size.id, color.id)!) : '—' }}
                  </button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.picker {
  display: flex;
  flex-direction: column;
  gap: 8px;
  min-height: 0;
}

.picker-filters {
  display: flex;
  gap: 6px;
}

.picker-search,
.picker-filters select {
  height: 40px;
  min-width: 0;
  padding: 0 10px;
  border: 1px solid var(--border-strong);
  border-radius: var(--radius);
  background: var(--surface);
  font-size: 15px;
}

.picker-search {
  flex: 1;
}

.picker-filters select {
  flex: 0 0 110px;
}

.picker-error {
  margin: 0;
  color: var(--red);
  font-size: 14px;
}

.tiles {
  flex: 1;
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(100px, 1fr));
  align-content: start;
  gap: 8px;
  min-height: 0;
  overflow-y: auto;
}

.tile {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 6px;
  border: 1px solid var(--border);
  border-radius: var(--radius);
  background: var(--surface);
  text-align: left;
  cursor: pointer;
}

.tile:hover:not(:disabled) {
  border-color: var(--accent);
}

.tile-image {
  display: flex;
  align-items: center;
  justify-content: center;
  aspect-ratio: 1 / 1;
  margin-bottom: 4px;
  overflow: hidden;
  border-radius: var(--radius-small);
  background: var(--surface-soft);
}

.tile-image img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.tile-image svg {
  width: 40%;
  height: 40%;
  fill: none;
  stroke: var(--gray-4);
  stroke-width: 1.2;
}

.tile-name {
  display: -webkit-box;
  overflow: hidden;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
  font-size: 13px;
  line-height: 1.25;
}

.tile-price {
  font-size: 14px;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
}

.tile-stock {
  color: var(--text-muted);
  font-size: 12px;
}

.picker-empty {
  margin: 0;
  color: var(--text-muted);
  font-size: 14px;
}

/* --- O'lcham × rang katakchasi --- */

.variant-overlay {
  position: fixed;
  inset: 0;
  z-index: 55;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 16px;
  background: rgb(35 27 20 / 45%);
}

.variant-card {
  display: flex;
  flex-direction: column;
  gap: 8px;
  width: 100%;
  max-width: 520px;
  max-height: 80vh;
  padding: 16px;
  border-radius: var(--radius-card);
  background: var(--surface);
}

.variant-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.variant-head h3 {
  margin: 0;
  font-size: 17px;
}

.variant-scroll {
  overflow: auto;
}

.variant-grid {
  width: 100%;
  border-collapse: collapse;
}

.variant-grid th {
  padding: 4px 8px;
  color: var(--text-secondary);
  font-size: 13px;
  font-weight: 600;
  text-align: center;
  white-space: nowrap;
}

.variant-grid tbody th {
  text-align: right;
}

.variant-grid td {
  padding: 3px;
}

/* Barmoq uchun: katak kamida 48 px */
.variant-cell {
  width: 100%;
  min-width: 56px;
  min-height: 48px;
  border: 1px solid var(--border-strong);
  border-radius: var(--radius);
  background: var(--surface);
  color: var(--text);
  font-size: 16px;
  font-weight: 600;
  font-variant-numeric: tabular-nums;
  cursor: pointer;
}

.variant-cell:hover:not(:disabled) {
  border-color: var(--accent);
  background: var(--accent-soft);
}

/* Zalda yo'q, ombordan olib chiqiladigan katak */
.variant-cell.from-warehouse {
  border-style: dashed;
  border-color: var(--accent);
  color: var(--accent);
}

.variant-cell:disabled {
  border-style: dashed;
  background: var(--surface-soft);
  color: var(--gray-5);
  cursor: not-allowed;
}

.variant-hint {
  margin: 0;
  color: var(--text-muted);
  font-size: 13px;
}
</style>
