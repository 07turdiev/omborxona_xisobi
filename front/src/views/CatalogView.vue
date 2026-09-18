<script setup lang="ts">
import { computed, onActivated, onMounted, ref, watch } from 'vue'
import { RouterLink, useRouter } from 'vue-router'

import { catalogApi, type CatalogOrdering } from '@/api/catalog'
import { errorMessage } from '@/api/client'
import { formatSum } from '@/utils/money'
import type { CatalogCard, Category } from '@/types'

const router = useRouter()

const search = ref('')
const category = ref('')
const inStock = ref(false)
const lowStock = ref(false)
const ordering = ref<CatalogOrdering>('newest')

const cards = ref<CatalogCard[]>([])
const categories = ref<Category[]>([])
const count = ref(0)
const page = ref(1)
const hasMore = ref(false)
const loading = ref(false)
const loadingMore = ref(false)
const error = ref('')
const filtersOpen = ref(false)

const ORDERINGS: { value: CatalogOrdering; label: string }[] = [
  { value: 'newest', label: 'Avval yangilari' },
  { value: 'name', label: 'Nomi bo‘yicha' },
  { value: '-stock', label: 'Qoldig‘i ko‘pi' },
  { value: 'stock', label: 'Qoldig‘i kami' },
]

/** Telefondagi "Filtr" tugmasida nechta filtr yoqilgani ko'rinadi */
const activeFilters = computed(
  () =>
    [category.value !== '', inStock.value, lowStock.value, ordering.value !== 'newest'].filter(
      Boolean,
    ).length,
)

/** Tez yozilganda eskirgan javob yangisining ustiga yozilmasin */
let request = 0
let searchTimer: ReturnType<typeof setTimeout> | undefined

async function load(more = false) {
  const current = ++request
  const target = more ? page.value + 1 : 1

  if (more) loadingMore.value = true
  else loading.value = true

  error.value = ''

  try {
    const data = await catalogApi.catalog({
      search: search.value.trim() || undefined,
      category: category.value || undefined,
      in_stock: inStock.value ? 'true' : undefined,
      low_stock: lowStock.value ? 'true' : undefined,
      ordering: ordering.value,
      page: target,
    })

    if (current !== request) return

    cards.value = more ? [...cards.value, ...data.results] : data.results
    count.value = data.count
    page.value = target
    hasMore.value = Boolean(data.next)
  } catch (err) {
    if (current === request) error.value = errorMessage(err, 'Katalogni yuklab bo‘lmadi.')
  } finally {
    if (current === request) {
      loading.value = false
      loadingMore.value = false
    }
  }
}

/** Enter (skaner ham oxirida Enter yuboradi) — kutmasdan qidiradi. */
async function searchNow() {
  clearTimeout(searchTimer)

  const query = search.value.trim()

  await load()

  // Yorliqdagi kod skanerlandi va aynan bitta mahsulot topildi — o'zi ochiladi
  if (/^\d{8,}$/.test(query) && cards.value.length === 1) {
    await router.push(`/catalog/${cards.value[0]!.id}`)
  }
}

watch(search, () => {
  clearTimeout(searchTimer)
  searchTimer = setTimeout(() => void load(), 300)
})

watch([category, inStock, lowStock, ordering], () => void load())

onMounted(async () => {
  try {
    categories.value = await catalogApi.categories()
  } catch {
    // Kategoriya filtrisiz ham ishlaydi
  }
})

/**
 * Sahifa saqlanib turadi (`App.vue`, KeepAlive). Mahsulotni ochib orqaga
 * qaytilgan bo'lsa ro'yxat va joy o'zgarmaydi; boshqa bo'limdan
 * kelinganda esa qoldiq eskirgan bo'lishi mumkin — qayta yuklanadi.
 */
onActivated(() => {
  const forward = String(window.history.state?.forward ?? '')

  if (!forward.startsWith('/catalog/') || !cards.value.length) void load()
})
</script>

<template>
  <section class="app-section active catalog">
    <div class="catalog-toolbar">
      <div class="catalog-search">
        <svg aria-hidden="true"><use href="#i-search" /></svg>
        <input
          v-model="search"
          type="search"
          inputmode="search"
          enterkeyhint="search"
          autocomplete="off"
          placeholder="Nomi yoki shtrix-kod"
          aria-label="Mahsulot qidirish"
          @keydown.enter.prevent="searchNow"
        />
      </div>

      <button
        class="filter-toggle"
        type="button"
        :aria-expanded="filtersOpen"
        aria-controls="catalog-filters"
        @click="filtersOpen = !filtersOpen"
      >
        Filtr
        <span v-if="activeFilters" class="filter-count">{{ activeFilters }}</span>
      </button>

      <div id="catalog-filters" class="catalog-filters" :class="{ open: filtersOpen }">
        <select v-model="category" aria-label="Kategoriya">
          <option value="">Barcha kategoriya</option>
          <option v-for="item in categories" :key="item.id" :value="String(item.id)">
            {{ item.name }}
          </option>
        </select>

        <select v-model="ordering" aria-label="Tartib">
          <option v-for="item in ORDERINGS" :key="item.value" :value="item.value">
            {{ item.label }}
          </option>
        </select>

        <label class="check">
          <input v-model="inStock" type="checkbox" />
          <span>Faqat qoldig‘i bor</span>
        </label>

        <label class="check">
          <input v-model="lowStock" type="checkbox" />
          <span>Tugayotganlar</span>
        </label>
      </div>
    </div>

    <p v-if="error" class="load-error">{{ error }}</p>

    <p class="catalog-count" aria-live="polite">
      {{ loading ? 'Yuklanmoqda…' : `${count} ta mahsulot` }}
    </p>

    <div class="card-grid">
      <RouterLink
        v-for="card in cards"
        :key="card.id"
        class="product-card"
        :to="`/catalog/${card.id}`"
      >
        <div class="card-image">
          <img
            v-if="card.primary_image"
            :src="card.primary_image.thumb"
            alt=""
            loading="lazy"
            decoding="async"
            width="200"
            height="250"
          />
          <svg v-else class="card-placeholder" aria-hidden="true"><use href="#i-image" /></svg>
        </div>

        <div class="card-body">
          <strong class="card-name">{{ card.name }}</strong>
          <span class="card-category">{{ card.category_name }}</span>
          <span class="card-price">{{ formatSum(card.sale_price) }}</span>

          <span class="card-stock" :class="card.total_stock ? 'in' : 'out'">
            {{ card.total_stock ? `${card.total_stock} dona` : 'Tugagan' }}
          </span>

          <!-- "Qaysi o'lcham qoldi" — mahsulotni ochmasdan ko'rinadi -->
          <p v-if="card.size_stock.length" class="size-line">
            <span
              v-for="entry in card.size_stock"
              :key="entry.size_id"
              :class="{ zero: !entry.quantity }"
            >
              {{ entry.size_name }}&nbsp;{{ entry.quantity }}
            </span>
          </p>
        </div>
      </RouterLink>
    </div>

    <p v-if="!loading && !cards.length && !error" class="empty-state">Mahsulot topilmadi.</p>

    <button
      v-if="hasMore"
      class="button button-outline load-more"
      type="button"
      :disabled="loadingMore"
      @click="load(true)"
    >
      {{ loadingMore ? 'Yuklanmoqda…' : 'Yana ko‘rsatish' }}
    </button>
  </section>
</template>

<style scoped>
/* Umumiy `sectionIn` animatsiyasi `transform` ishlatadi, `transform` esa
   ichidagi `position: fixed` ni ekranga emas, bo'limning o'ziga bog'laydi:
   telefondagi qidiruv paneli animatsiya davomida ro'yxat oxiriga tushib
   qolardi. Shu sahifada kirish faqat shaffoflik bilan. */
.catalog.app-section.active {
  animation: catalog-fade 0.25s ease;
}

@keyframes catalog-fade {
  from {
    opacity: 0;
  }
}

.catalog-toolbar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
}

.catalog-search {
  flex: 1 1 280px;
  max-width: 420px;
  height: 38px;
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 0 10px;
  border: 1px solid var(--border-strong);
  border-radius: var(--radius);
  background: var(--surface);
}

.catalog-search:focus-within {
  border-color: var(--accent);
  box-shadow: 0 0 0 3px var(--accent-soft);
}

.catalog-search svg {
  flex: none;
  width: 16px;
  height: 16px;
  fill: none;
  stroke: var(--text-muted);
  stroke-width: 2;
  stroke-linecap: round;
}

.catalog-search input {
  flex: 1;
  min-width: 0;
  height: 100%;
  border: 0;
  outline: 0;
  background: transparent;
  color: var(--text);
  font-size: 14px;
}

.filter-toggle {
  display: none;
}

.catalog-filters {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
}

.catalog-filters select {
  height: 38px;
  padding: 0 8px;
  border: 1px solid var(--border-strong);
  border-radius: var(--radius);
  background: var(--surface);
  color: var(--text-secondary);
  font-size: 13px;
}

.check {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  min-height: 38px;
  padding: 0 10px;
  border: 1px solid var(--border-strong);
  border-radius: var(--radius);
  background: var(--surface);
  font-size: 13px;
  cursor: pointer;
  user-select: none;
}

.check input {
  width: 16px;
  height: 16px;
  margin: 0;
  accent-color: var(--accent);
}

.check:has(input:checked) {
  border-color: var(--accent);
  background: var(--accent-soft);
}

.catalog-count {
  margin: 0 0 8px;
  color: var(--text-muted);
  font-size: 12px;
}

.card-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 12px;
}

.product-card {
  display: flex;
  flex-direction: column;
  overflow: hidden;
  border: 1px solid var(--border);
  border-radius: var(--radius);
  background: var(--surface);
  color: inherit;
  text-decoration: none;
  transition:
    border-color 0.15s,
    box-shadow 0.15s;
}

.product-card:hover {
  border-color: var(--border-strong);
  box-shadow: var(--shadow);
}

.product-card:focus-visible {
  outline: 2px solid var(--accent);
  outline-offset: 2px;
}

.card-image {
  aspect-ratio: 4 / 5;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--surface-soft);
}

.card-image img {
  display: block;
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.card-placeholder {
  width: 40%;
  height: 40%;
  fill: none;
  stroke: var(--gray-4);
  stroke-width: 1.2;
}

.card-body {
  display: flex;
  flex-direction: column;
  gap: 3px;
  padding: 10px;
}

.card-name {
  display: -webkit-box;
  overflow: hidden;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
  font-size: 14px;
  line-height: 1.3;
}

.card-category {
  color: var(--text-muted);
  font-size: 12px;
}

.card-price {
  font-size: 15px;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
}

.card-stock {
  align-self: flex-start;
  padding: 1px 8px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 600;
}

.card-stock.in {
  background: var(--green-soft);
  color: var(--green);
}

.card-stock.out {
  background: var(--red-soft);
  color: var(--red);
}

.size-line {
  margin: 2px 0 0;
  color: var(--text-secondary);
  font-size: 12px;
  font-variant-numeric: tabular-nums;
}

.size-line span {
  white-space: nowrap;
}

.size-line span + span::before {
  content: '·';
  margin: 0 5px;
  color: var(--text-muted);
}

.size-line .zero {
  color: var(--gray-5);
}

.load-more {
  display: flex;
  min-width: 200px;
  margin: 16px auto 0;
}

@media (max-width: 640px) {
  /* Qidiruv pastda: telefonni bir qo'lda ushlaganda bosh barmoq yetadi */
  .catalog {
    padding-bottom: 84px;
  }

  .catalog-toolbar {
    position: fixed;
    right: 0;
    bottom: 0;
    left: 0;
    z-index: 30;
    flex-wrap: nowrap;
    margin: 0;
    padding: 8px 12px calc(8px + env(safe-area-inset-bottom));
    border-top: 1px solid var(--border);
    background: var(--surface);
    box-shadow: 0 -4px 12px rgb(0 0 0 / 6%);
  }

  .catalog-search {
    flex: 1;
    max-width: none;
    height: 48px;
  }

  /* 16px dan kichik shriftda iPhone maydonni kattalashtirib yuboradi */
  .catalog-search input {
    font-size: 16px;
  }

  .filter-toggle {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    height: 48px;
    padding: 0 14px;
    border: 1px solid var(--border-strong);
    border-radius: var(--radius);
    background: var(--surface);
    color: var(--text);
    font-size: 14px;
    font-weight: 600;
  }

  .filter-count {
    display: grid;
    place-items: center;
    min-width: 20px;
    height: 20px;
    padding: 0 6px;
    border-radius: 999px;
    background: var(--accent);
    color: #fff;
    font-size: 12px;
  }

  /* Filtrlar qidiruv ustida ochiladi — bosh barmoqdan uzoqqa ketmaydi */
  .catalog-filters {
    position: absolute;
    right: 0;
    bottom: 100%;
    left: 0;
    display: none;
    flex-direction: column;
    align-items: stretch;
    padding: 12px;
    border-top: 1px solid var(--border);
    background: var(--surface);
    box-shadow: 0 -6px 16px rgb(0 0 0 / 8%);
  }

  .catalog-filters.open {
    display: flex;
  }

  .catalog-filters select,
  .check {
    min-height: 48px;
    height: 48px;
    font-size: 15px;
  }

  .card-grid {
    grid-template-columns: 1fr;
    gap: 8px;
  }

  /* Bitta ustun: rasm chapda, matn o'ngda. Butun qator bosiladi */
  .product-card {
    flex-direction: row;
    min-height: 120px;
  }

  .card-image {
    flex: 0 0 96px;
    aspect-ratio: auto;
  }

  .card-body {
    flex: 1;
    justify-content: center;
    min-width: 0;
    padding: 10px 12px;
  }
}
</style>
