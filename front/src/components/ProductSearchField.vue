<script setup lang="ts">
import { nextTick, ref, watch } from 'vue'

import { catalogApi } from '@/api/catalog'
import { formatMoney } from '@/utils/money'
import type { Product } from '@/types'

/**
 * Kirim ekranining qidiruv maydoni.
 *
 * Do'konga tovar shtrix-kodsiz keladi, shuning uchun maydon **nomdan**
 * boshlanadi: yozilgan harflar bo'yicha nom, brend va SKU qidiriladi,
 * model ro'yxatdan tanlanadi (sichqoncha bilan ham, o'q tugmalari
 * bilan ham).
 *
 * Skaner ham ishlayveradi — faqat raqam yozilib Enter bosilsa, kod
 * bo'yicha qidiriladi. Lekin ekran skanerni talab qilmaydi: yangi
 * tovarda yorliq hali yo'q.
 */

const emit = defineEmits<{ scan: [code: string]; pick: [product: Product] }>()

const value = ref('')
const results = ref<Product[]>([])
const highlighted = ref(0)
const open = ref(false)
const searching = ref(false)

const input = ref<HTMLInputElement | null>(null)

let timer: ReturnType<typeof setTimeout> | undefined
let request = 0

/** Skaner kodi: faqat raqam va yetarlicha uzun */
function isBarcode(text: string) {
  return /^\d{6,}$/.test(text)
}

async function search(text: string) {
  const current = ++request

  searching.value = true

  try {
    const page = await catalogApi.products({ search: text })

    if (current !== request) return

    results.value = page.results.slice(0, 8)
    highlighted.value = 0
    open.value = true
  } catch {
    // Qidiruv ishlamasa ham skaner ishlayveradi
    if (current === request) results.value = []
  } finally {
    if (current === request) searching.value = false
  }
}

watch(value, (text) => {
  clearTimeout(timer)

  const trimmed = text.trim()

  // Skanerlangan kod uchun so'rov yubormaymiz: Enter darhol keladi
  if (trimmed.length < 2 || isBarcode(trimmed)) {
    open.value = false
    results.value = []
    return
  }

  timer = setTimeout(() => search(trimmed), 250)
})

function choose(product: Product) {
  value.value = ''
  results.value = []
  open.value = false

  emit('pick', product)
}

function onEnter() {
  const text = value.value.trim()

  if (!text) return

  if (isBarcode(text)) {
    value.value = ''
    open.value = false
    emit('scan', text)
    return
  }

  const product = results.value[highlighted.value]

  if (product) choose(product)
}

function move(step: number) {
  if (!open.value || !results.value.length) return

  const last = results.value.length - 1

  highlighted.value = Math.min(last, Math.max(0, highlighted.value + step))
}

async function focus() {
  await nextTick()
  input.value?.focus()
  input.value?.select()
}

defineExpose({ focus })
</script>

<template>
  <div class="search-wrap">
    <div class="scan-field">
      <svg aria-hidden="true"><use href="#i-search" /></svg>

      <input
        ref="input"
        v-model="value"
        type="text"
        autocomplete="off"
        role="combobox"
        aria-controls="purchase-search-results"
        :aria-expanded="open"
        placeholder="Tovar nomini yozing — yoki yangi mahsulot qo‘shing"
        aria-label="Tovar nomi"
        @keydown.enter.prevent="onEnter"
        @keydown.down.prevent="move(1)"
        @keydown.up.prevent="move(-1)"
        @keydown.esc="open = false"
        @blur="open = false"
      />

      <span v-if="searching" class="search-state">Qidirilmoqda…</span>
    </div>

    <!-- `mousedown` — `blur` dan oldin ishlaydi, aks holda ro'yxat
         bosilgan zahoti yopilib, tanlov ketmay qolardi -->
    <ul
      v-if="open && results.length"
      id="purchase-search-results"
      class="results"
      role="listbox"
    >
      <li
        v-for="(product, index) in results"
        :key="product.id"
        :class="{ active: index === highlighted }"
        role="option"
        :aria-selected="index === highlighted"
        @mousedown.prevent="choose(product)"
        @mouseenter="highlighted = index"
      >
        <span class="result-name">{{ product.name }}</span>

        <span class="result-meta">
          {{ product.category_name }}<template v-if="product.brand"> · {{ product.brand }}</template>
          · {{ product.variants.length }} variant
        </span>

        <span class="result-price">{{ formatMoney(product.sale_price) }}</span>
      </li>
    </ul>

    <p v-else-if="open && !searching" class="results-empty">
      Bunday tovar yo‘q — «Yangi mahsulot» tugmasi bilan qo‘shing.
    </p>
  </div>
</template>

<style scoped>
.search-wrap {
  position: relative;
  flex: 1;
  min-width: 260px;
}

.scan-field {
  display: flex;
  align-items: center;
  gap: 8px;
  height: 44px;
  padding: 0 12px;
  border: 2px solid var(--accent);
  border-radius: var(--radius);
  background: var(--surface);
}

.scan-field svg {
  width: 18px;
  height: 18px;
  flex-shrink: 0;
  fill: none;
  stroke: var(--accent);
  stroke-width: 2;
}

.scan-field input {
  width: 100%;
  min-height: 0;
  border: 0;
  background: none;
  box-shadow: none;
  font-size: 16px;
}

.search-state {
  flex: none;
  color: var(--text-muted);
  font-size: 12px;
}

.results {
  position: absolute;
  z-index: 20;
  top: calc(100% + 4px);
  right: 0;
  left: 0;
  max-height: 280px;
  margin: 0;
  padding: 4px;
  overflow-y: auto;
  list-style: none;
  border: 1px solid var(--border);
  border-radius: var(--radius-card);
  background: var(--surface);
  box-shadow: var(--shadow-large);
}

.results li {
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 0 12px;
  padding: 8px 10px;
  border-radius: var(--radius);
  cursor: pointer;
}

.results li.active {
  background: var(--accent-soft);
}

.result-name {
  font-weight: 600;
}

.result-meta {
  grid-column: 1;
  color: var(--text-muted);
  font-size: 12px;
}

.result-price {
  grid-row: 1 / span 2;
  align-self: center;
  font-variant-numeric: tabular-nums;
  font-weight: 600;
}

.results-empty {
  position: absolute;
  z-index: 20;
  top: calc(100% + 4px);
  right: 0;
  left: 0;
  padding: 10px 12px;
  border: 1px solid var(--border);
  border-radius: var(--radius-card);
  background: var(--surface);
  box-shadow: var(--shadow-large);
  color: var(--text-muted);
  font-size: 13px;
}
</style>
