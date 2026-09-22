<script setup lang="ts">
import { computed, onActivated, onMounted, ref, watch } from 'vue'
import { RouterLink, useRoute, useRouter } from 'vue-router'

import ProductForm from '@/components/ProductForm.vue'
import SizeStockLine from '@/components/SizeStockLine.vue'
import { catalogApi, type CatalogOrdering } from '@/api/catalog'
import { errorMessage } from '@/api/client'
import { useAuthStore } from '@/stores/auth'
import { formatMoney, formatSum } from '@/utils/money'
import type { CatalogCard, Category, Product } from '@/types'

/**
 * Mahsulotlar — do'kondagi hamma tovar bitta ro'yxatda.
 *
 * Ilgari uchta sahifa (katalog, mahsulotlar, qoldiq) bir xil ma'lumotni
 * uch xil ko'rsatardi. Endi qoldiq — shu ro'yxatning ustuni, tahrirlash,
 * yorliq va hisobdan chiqarish — mahsulot sahifasidagi amallar.
 */

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

const search = ref('')
const category = ref('')
const inStock = ref(false)
const lowStock = ref(false)

/** Joy filtri: '' — hammasi, 'shop' — zalda, 'warehouse' — omborda */
const place = ref('')
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
const formOpen = ref(false)

const ORDERINGS: { value: CatalogOrdering; label: string }[] = [
  { value: 'newest', label: 'Avval yangilari' },
  { value: 'name', label: 'Nomi bo‘yicha' },
  { value: '-stock', label: 'Qoldig‘i ko‘pi' },
  { value: 'stock', label: 'Qoldig‘i kami' },
]

// --- Ko'rinish: kartalar yoki ixcham jadval (faqat administrator) ---------

const VIEW_KEY = 'products-view'

function savedView(): 'grid' | 'table' {
  try {
    return localStorage.getItem(VIEW_KEY) === 'table' ? 'table' : 'grid'
  } catch {
    return 'grid'
  }
}

const view = ref<'grid' | 'table'>(savedView())

watch(view, (value) => {
  try {
    localStorage.setItem(VIEW_KEY, value)
  } catch {
    // Shaxsiy oynada saqlash yopiq bo'lishi mumkin — muhim emas
  }
})

const tableView = computed(() => auth.isAdmin && view.value === 'table')

/**
 * Telefondagi "Filtr" tugmasida nechta filtr yoqilgani ko'rinadi.
 * Kategoriya sanalmaydi — u chiplarda, ro'yxatning o'zida ko'rinib turadi.
 */
const activeFilters = computed(
  () => [inStock.value, lowStock.value, ordering.value !== 'newest'].filter(Boolean).length,
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
      location: place.value || undefined,
      ordering: ordering.value,
      page: target,
    })

    if (current !== request) return

    cards.value = more ? [...cards.value, ...data.results] : data.results
    count.value = data.count
    page.value = target
    hasMore.value = Boolean(data.next)
  } catch (err) {
    if (current === request) error.value = errorMessage(err, 'Mahsulotlarni yuklab bo‘lmadi.')
  } finally {
    if (current === request) {
      loading.value = false
      loadingMore.value = false
    }
  }
}

function open(card: CatalogCard) {
  void router.push(`/products/${card.id}`)
}

/** Enter (skaner ham oxirida Enter yuboradi) — kutmasdan qidiradi. */
async function searchNow() {
  clearTimeout(searchTimer)

  const query = search.value.trim()

  await load()

  // Yorliqdagi kod skanerlandi va aynan bitta mahsulot topildi — o'zi ochiladi
  if (/^\d{8,}$/.test(query) && cards.value.length === 1) open(cards.value[0]!)
}

function onCreated(product: Product) {
  formOpen.value = false

  // Rasm, yorliq va boshqa amallar — mahsulot sahifasida
  void router.push(`/products/${product.id}`)
}

watch(search, () => {
  clearTimeout(searchTimer)
  searchTimer = setTimeout(() => void load(), 300)
})

watch([category, inStock, lowStock, place, ordering], () => void load())

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
  // Boshqaruv panelidagi "tugayotganlar" havolasi: ?low_stock=true
  if (route.query.low_stock === 'true') {
    void router.replace({ query: {} })

    if (!lowStock.value) {
      lowStock.value = true // kuzatuvchi o'zi yuklaydi
      return
    }
  }

  const forward = String(window.history.state?.forward ?? '')

  if (!forward.startsWith('/products/') || !cards.value.length) void load()
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
          placeholder="Nomi, brend, SKU yoki shtrix-kod"
          aria-label="Mahsulot qidirish"
          @keydown.enter.prevent="searchNow"
        />
      </div>

      <button
        class="filter-toggle"
        type="button"
        :aria-expanded="filtersOpen"
        aria-controls="product-filters"
        @click="filtersOpen = !filtersOpen"
      >
        Filtr
        <span v-if="activeFilters" class="filter-count">{{ activeFilters }}</span>
      </button>

      <div id="product-filters" class="catalog-filters" :class="{ open: filtersOpen }">
        <select v-model="ordering" aria-label="Tartib">
          <option v-for="item in ORDERINGS" :key="item.value" :value="item.value">
            {{ item.label }}
          </option>
        </select>

        <!-- Qoldiq ikki joyda alohida: ro'yxatni ham ajratib ko'rish mumkin -->
        <select v-model="place" aria-label="Joy">
          <option value="">Hamma joy</option>
          <option value="shop">Zalda bor</option>
          <option value="warehouse">Omborda bor</option>
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

      <div v-if="auth.isAdmin" class="admin-tools">
        <div class="view-toggle" role="group" aria-label="Ko‘rinish">
          <button
            type="button"
            :class="{ active: view === 'grid' }"
            :aria-pressed="view === 'grid'"
            @click="view = 'grid'"
          >
            Kartalar
          </button>
          <button
            type="button"
            :class="{ active: view === 'table' }"
            :aria-pressed="view === 'table'"
            @click="view = 'table'"
          >
            Jadval
          </button>
        </div>

        <button class="button button-gradient" type="button" @click="formOpen = true">
          <svg><use href="#i-plus" /></svg>
          <span>Yangi mahsulot</span>
        </button>
      </div>
    </div>

    <p v-if="error" class="load-error">{{ error }}</p>

    <!-- Kategoriya chiplari: bo'lim bir bosishda almashadi -->
    <div v-if="categories.length" class="category-chips" role="group" aria-label="Kategoriya">
      <button
        type="button"
        :class="{ selected: !category }"
        :aria-pressed="!category"
        @click="category = ''"
      >
        Hammasi
      </button>

      <button
        v-for="item in categories"
        :key="item.id"
        type="button"
        :class="{ selected: category === String(item.id) }"
        :aria-pressed="category === String(item.id)"
        @click="category = String(item.id)"
      >
        {{ item.name }}
      </button>
    </div>

    <p class="catalog-count" aria-live="polite">
      {{ loading ? 'Yuklanmoqda…' : `${count} ta mahsulot` }}
    </p>

    <!-- Ixcham jadval: ko'p tovarni bir qarashda ko'rish uchun -->
    <div v-if="tableView" class="table-card">
      <div class="table-scroll">
        <table class="data-table product-table">
          <thead>
            <tr>
              <th class="thumb-cell"></th>
              <th>Nomi</th>
              <th class="num">Narxi</th>
              <th>O‘lchamlar</th>
              <th class="num">Qoldiq</th>
            </tr>
          </thead>

          <tbody>
            <tr v-for="card in cards" :key="card.id" class="clickable" @click="open(card)">
              <td class="thumb-cell">
                <img
                  v-if="card.primary_image"
                  :src="card.primary_image.thumb"
                  alt=""
                  loading="lazy"
                  width="32"
                  height="40"
                />
                <span v-else class="thumb-empty" />
              </td>

              <td>
                <RouterLink class="row-link" :to="`/products/${card.id}`" @click.stop>
                  {{ card.name }}
                </RouterLink>
                <small class="cell-sub">
                  {{ card.category_name }}<template v-if="card.brand"> · {{ card.brand }}</template>
                </small>
              </td>

              <td class="num">{{ formatMoney(card.sale_price) }}</td>
              <td><SizeStockLine :entries="card.size_stock" /></td>

              <td class="num">
                <span :class="{ out: !card.total_stock }">{{ card.total_stock }}</span>
                <small class="cell-sub">
                  zal {{ card.shop_stock ?? 0 }} · ombor {{ card.warehouse_stock ?? 0 }}
                </small>
              </td>

            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <div v-else class="card-grid">
      <RouterLink
        v-for="card in cards"
        :key="card.id"
        class="product-card"
        :to="`/products/${card.id}`"
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

          <!-- Belgi zaldagi qoldiqqa qaraydi: omborda yotgan tovarni
               javondan sotib bo'lmaydi -->
          <span class="card-stock" :class="card.shop_stock ? 'in' : 'out'">
            {{ card.shop_stock ? `${card.shop_stock} dona` : 'Zalda yo‘q' }}
          </span>

          <span class="card-places">
            Zalda {{ card.shop_stock }} · omborda {{ card.warehouse_stock }}
          </span>

          <!-- "Qaysi o'lcham qoldi" — mahsulotni ochmasdan ko'rinadi -->
          <SizeStockLine v-if="card.size_stock.length" class="size-line" :entries="card.size_stock" />
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

    <ProductForm v-if="formOpen" :product="null" @saved="onCreated" @close="formOpen = false" />
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
  font-size: 15px;
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
  font-size: 14px;
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
  font-size: 14px;
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

.admin-tools {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-left: auto;
}

.view-toggle {
  display: inline-flex;
  overflow: hidden;
  border: 1px solid var(--border-strong);
  border-radius: var(--radius);
}

.view-toggle button {
  height: 36px;
  padding: 0 12px;
  border: 0;
  background: var(--surface);
  color: var(--text-secondary);
  font-size: 14px;
  cursor: pointer;
}

.view-toggle button + button {
  border-left: 1px solid var(--border-strong);
}

.view-toggle button.active {
  background: var(--accent-soft);
  color: var(--text);
  font-weight: 600;
}

/* --- Kategoriya chiplari --- */

.category-chips {
  display: flex;
  gap: 8px;
  margin-bottom: 10px;
  padding: 2px 0;
  overflow-x: auto;
  scrollbar-width: none;
}

.category-chips::-webkit-scrollbar {
  display: none;
}

.category-chips button {
  flex: none;
  padding: 7px 15px;
  border: 1px solid var(--border);
  border-radius: 999px;
  background: var(--surface-soft);
  color: var(--text-secondary);
  font-size: 13px;
  white-space: nowrap;
  cursor: pointer;
  transition:
    background-color 0.15s,
    color 0.15s;
}

.category-chips button:hover {
  background: var(--surface-hover);
}

.category-chips button.selected {
  border-color: var(--accent);
  background: var(--accent);
  color: var(--accent-text);
}

.catalog-count {
  margin: 0 0 10px;
  color: var(--text-muted);
  font-size: 13px;
}

/* --- Jadval --- */

.product-table .thumb-cell {
  width: 44px;
  padding-right: 0;
}

.thumb-cell img,
.thumb-empty {
  display: block;
  width: 32px;
  height: 40px;
  border-radius: var(--radius-small);
  background: var(--surface-soft);
  object-fit: cover;
}

.row-link {
  color: var(--text);
  font-weight: 600;
  text-decoration: none;
}

.row-link:hover {
  color: var(--accent);
}

.clickable {
  cursor: pointer;
}

.out {
  color: var(--red);
  font-weight: 700;
}


/* --- Kartalar --- */

.card-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(210px, 1fr));
  gap: 16px;
}

.product-card {
  display: flex;
  flex-direction: column;
  overflow: hidden;
  border: 1px solid var(--border);
  border-radius: var(--radius-card);
  background: var(--surface);
  color: inherit;
  text-decoration: none;
  transition:
    transform 0.2s,
    box-shadow 0.2s;
}

.product-card:hover {
  transform: translateY(-4px);
  box-shadow: var(--shadow-large);
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
  overflow: hidden;
  background: var(--gray-1);
}

.card-image img {
  display: block;
  width: 100%;
  height: 100%;
  object-fit: cover;
  transition: transform 0.4s;
}

.product-card:hover .card-image img {
  transform: scale(1.04);
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
  gap: 4px;
  padding: 14px 15px 15px;
}

.card-name {
  display: -webkit-box;
  overflow: hidden;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
  font-size: 16px;
  font-weight: 600;
  line-height: 1.3;
}

.card-category {
  order: -1;
  color: var(--text-muted);
  font-size: 12px;
  letter-spacing: 1.2px;
  text-transform: uppercase;
}

.card-places {
  color: var(--text-muted);
  font-size: 12px;
}

.card-price {
  color: var(--accent);
  font-size: 16px;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
}

.card-stock {
  align-self: flex-start;
  padding: 1px 8px;
  border-radius: 999px;
  font-size: 13px;
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
  margin-top: 2px;
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
    font-size: 17px;
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
    font-size: 15px;
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
    font-size: 13px;
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
    font-size: 16px;
  }

  /* Telefonda jadval va yangi mahsulot tugmasi kerak emas: tahrirlash
     kompyuterda qulayroq, ro'yxat esa kartalarda o'qiladi */
  .admin-tools {
    display: none;
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
