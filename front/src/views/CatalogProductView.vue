<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import ImageGallery from '@/components/ImageGallery.vue'
import LabelPrint from '@/components/LabelPrint.vue'
import type { LabelItem } from '@/api/agent'
import { catalogApi } from '@/api/catalog'
import { errorMessage } from '@/api/client'
import { useAuthStore } from '@/stores/auth'
import {
  colorStock,
  findVariant,
  galleryImages,
  initialColor,
  sizeOptions,
  type SizeOption,
} from '@/utils/catalog'
import { formatSum } from '@/utils/money'
import type { CatalogProduct } from '@/types'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

const product = ref<CatalogProduct | null>(null)
const loading = ref(true)
const error = ref('')

const colorId = ref<number | null>(null)
const sizeId = ref<number | null>(null)

const labelItems = ref<LabelItem[]>([])
const labels = ref<InstanceType<typeof LabelPrint> | null>(null)

async function load() {
  const id = Number(route.params.id)

  // Boshqa sahifaga o'tilganda parametr yo'qoladi — so'rov yuborilmaydi
  if (!id) return

  loading.value = true
  error.value = ''

  try {
    const data = await catalogApi.catalogProduct(id)

    product.value = data
    colorId.value = initialColor(data)
    sizeId.value = null
  } catch (err) {
    error.value = errorMessage(err, 'Mahsulotni yuklab bo‘lmadi.')
  } finally {
    loading.value = false
  }
}

watch(() => route.params.id, load, { immediate: true })

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

function goBack() {
  // Katalogdan kelingan bo'lsa — o'sha joyga, havola orqali ochilgan bo'lsa — ro'yxatga
  if (window.history.state?.back) router.back()
  else void router.push('/catalog')
}

/** Tanlangan variantga yoki tanlangan rangning hamma variantlariga yorliq. */
function printLabels() {
  const data = product.value

  if (!data) return

  const rows = variant.value
    ? [variant.value]
    : data.variants.filter((item) => colorId.value === null || item.color === colorId.value)

  labelItems.value = rows.map((item) => ({
    barcode: item.barcode,
    name: data.name,
    label: [item.size_name, item.color_name].filter(Boolean).join(' / '),
    price: item.price,
    quantity: 1,
  }))

  // Ro'yxat DOM ga chiqishi uchun keyingi kadrda
  setTimeout(() => labels.value?.printLabels(), 50)
}
</script>

<template>
  <section class="app-section active product-page">
    <button class="back-link" type="button" @click="goBack">‹ Katalog</button>

    <p v-if="error" class="load-error">{{ error }}</p>
    <p v-else-if="loading && !product" class="empty-state">Yuklanmoqda…</p>

    <div v-if="product" class="product-layout">
      <ImageGallery :images="gallery" :alt="product.name" />

      <div class="product-info">
        <p class="info-meta">
          {{ product.category_name }}<template v-if="product.brand"> · {{ product.brand }}</template>
        </p>

        <h2 class="info-name">{{ product.name }}</h2>

        <p class="info-price">{{ formatSum(variant?.price ?? product.sale_price) }}</p>

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
          <template v-if="product.size_stock.length">
            <span
              v-for="entry in product.size_stock"
              :key="entry.size_id"
              class="all-size"
              :class="{ zero: !entry.quantity }"
            >
              {{ entry.size_name }}&nbsp;{{ entry.quantity }}
            </span>
          </template>
          <strong class="all-total">jami {{ product.total_stock }} dona</strong>
        </p>

        <dl v-if="variant" class="variant-box">
          <div>
            <dt>Shtrix-kod</dt>
            <dd class="barcode-text">{{ variant.barcode }}</dd>
          </div>

          <div>
            <dt>Qoldiq</dt>
            <dd>{{ variant.stock_quantity }} dona</dd>
          </div>
        </dl>

        <p v-else-if="product.sizes.length" class="hint">
          Shtrix-kodni ko‘rish uchun o‘lcham tanlang.
        </p>

        <button
          v-if="auth.isAdmin"
          class="button button-outline label-button"
          type="button"
          @click="printLabels"
        >
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
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
}

.product-layout {
  display: grid;
  grid-template-columns: minmax(0, 440px) minmax(0, 1fr);
  align-items: start;
  gap: 24px;
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
  font-size: 13px;
}

.info-name {
  margin: 0;
  font-size: 22px;
  line-height: 1.25;
}

.info-price {
  margin: 0;
  font-size: 22px;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
}

.option-label {
  margin: 0 0 8px;
  color: var(--text-secondary);
  font-size: 13px;
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
  font-size: 14px;
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
  font-size: 15px;
  font-weight: 600;
}

.size-button small {
  color: var(--text-muted);
  font-size: 11px;
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
  font-size: 13px;
  font-variant-numeric: tabular-nums;
}

.all-size {
  white-space: nowrap;
}

.all-size + .all-size::before {
  content: '·';
  margin: 0 5px;
  color: var(--text-muted);
}

.all-size.zero {
  color: var(--gray-5);
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
  border-radius: var(--radius);
}

.variant-box dt,
.details dt {
  color: var(--text-muted);
  font-size: 12px;
}

.variant-box dd,
.details dd {
  margin: 2px 0 0;
  font-size: 14px;
}

.barcode-text {
  font-family: ui-monospace, Consolas, monospace;
  font-size: 16px;
  letter-spacing: 0.04em;
}

.hint {
  margin: 0;
  color: var(--text-muted);
  font-size: 13px;
}

.label-button {
  align-self: flex-start;
}

.details {
  display: grid;
  gap: 10px;
  margin: 0;
}

.description {
  margin: 0;
  font-size: 14px;
  line-height: 1.6;
  white-space: pre-line;
}

@media (max-width: 760px) {
  .product-layout {
    grid-template-columns: 1fr;
    gap: 16px;
  }

  .label-button {
    align-self: stretch;
    min-height: 44px;
  }
}
</style>
