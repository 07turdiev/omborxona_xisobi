<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'

import ImportModal from '@/components/ImportModal.vue'
import ProductModal from '@/components/ProductModal.vue'
import { useAuthStore } from '@/stores/auth'
import { useCatalogStore } from '@/stores/catalog'
import type { Product, Variant } from '@/types'

const store = useCatalogStore()
const auth = useAuthStore()

/** Kirim narxi — `view_purchase_price` ruxsati bilan */
const canSeePurchase = computed(() => auth.can('view_purchase_price'))

// Excel import
const importOpen = ref(false)
const canImport = computed(
  () => auth.can('products') && Boolean(auth.user?.current_tenant?.can_write),
)

async function onImported() {
  await store.loadCategories()
  await store.loadProducts()
}

const modalOpen = ref(false)
const editing = ref<Product | null>(null)
const expanded = ref<Set<number>>(new Set())

onMounted(async () => {
  await store.loadCategories()
  await store.loadProducts()
})

let searchTimer: ReturnType<typeof setTimeout> | undefined

function onSearchInput() {
  clearTimeout(searchTimer)
  searchTimer = setTimeout(() => store.loadProducts(), 300)
}

function openCreate() {
  editing.value = null
  modalOpen.value = true
}

function openEdit(product: Product) {
  editing.value = product
  modalOpen.value = true
}

async function onDelete(product: Product) {
  const ok = window.confirm(`"${product.name}" mahsulotini o‘chirasizmi?`)
  if (ok) await store.removeProduct(product.id)
}

function toggle(id: number) {
  const next = new Set(expanded.value)
  if (next.has(id)) next.delete(id)
  else next.add(id)
  expanded.value = next
}

/** Bir nechta varianti bor mahsulotlar (kiyim) alohida ko'rsatiladi. */
function hasManyVariants(product: Product): boolean {
  return product.variants.length > 1
}

function firstVariant(product: Product): Variant | undefined {
  return product.variants[0]
}

function money(value: string | null, currency = 'UZS'): string {
  if (!value) return '—'
  const formatted = new Intl.NumberFormat('uz-UZ').format(Number(value))
  return `${formatted} ${currency === 'UZS' ? "so'm" : currency}`
}

function attributeSummary(variant: Variant | undefined): string {
  if (!variant) return '—'

  const parts = Object.entries(variant.attributes)
    .filter(([, value]) => value !== null && value !== '')
    .map(([, value]) => String(value))

  return parts.length ? parts.join(' · ') : '—'
}

function packSummary(variant: Variant | undefined): string {
  if (!variant?.units.length) return '—'

  return variant.units
    .map((unit) => `${unit.unit} = ${Number(unit.factor_to_base)}`)
    .join(', ')
}

const totalVariants = computed(() =>
  store.products.reduce((sum, product) => sum + product.variants.length, 0),
)
</script>

<template>
  <section class="app-section active">
    <div class="section-toolbar">
      <div class="filters">
        <div class="search-field">
          <svg><use href="#i-search" /></svg>

          <input
            v-model="store.filters.search"
            type="search"
            placeholder="Nomi, brendi yoki SKU..."
            @input="onSearchInput"
          />
        </div>

        <select v-model="store.filters.category" @change="store.loadProducts()">
          <option value="">Barcha kategoriyalar</option>
          <option
            v-for="option in store.categoryOptions"
            :key="option.id"
            :value="option.id"
          >
            {{ option.label }}
          </option>
        </select>
      </div>

      <div class="toolbar-actions">
        <RouterLink to="/categories" class="button button-soft">
          <svg><use href="#i-settings" /></svg>
          <span>Kategoriyalar</span>
        </RouterLink>

        <button
          v-if="canImport"
          class="button button-outline"
          type="button"
          @click="importOpen = true"
        >
          <svg><use href="#i-import" /></svg>
          <span>Excel import</span>
        </button>

        <ImportModal
          :show="importOpen"
          type="products"
          title="Mahsulotlarni import qilish"
          @close="importOpen = false"
          @done="onImported"
        />

        <button class="button button-gradient" @click="openCreate">
          <svg><use href="#i-plus" /></svg>
          <span>Mahsulot qo‘shish</span>
        </button>
      </div>
    </div>

    <p v-if="store.error" class="load-error">{{ store.error }}</p>

    <div class="kpi-grid compact">
      <article class="kpi-card kpi-purple">
        <div class="kpi-icon"><svg><use href="#i-company" /></svg></div>
        <p>Mahsulotlar</p>
        <strong>{{ store.products.length }}</strong>
      </article>

      <article class="kpi-card kpi-teal">
        <div class="kpi-icon"><svg><use href="#i-stock" /></svg></div>
        <p>Variantlar</p>
        <strong>{{ totalVariants }}</strong>
      </article>

      <article class="kpi-card kpi-blue">
        <div class="kpi-icon"><svg><use href="#i-settings" /></svg></div>
        <p>Kategoriyalar</p>
        <strong>{{ store.categories.length }}</strong>
      </article>
    </div>

    <div class="table-card">
      <div class="table-scroll">
        <table class="data-table">
          <thead>
            <tr>
              <th>Mahsulot</th>
              <th>Kategoriya</th>
              <th>Atributlar</th>
              <th>Birlik</th>
              <th>O‘ram</th>
              <th v-if="canSeePurchase" class="num">Kirim narxi</th>
              <th class="num">Sotuv narxi</th>
              <th>Holat</th>
              <th></th>
            </tr>
          </thead>

          <tbody>
            <tr v-if="store.loading">
              <td :colspan="canSeePurchase ? 9 : 8" class="empty-state">Yuklanmoqda…</td>
            </tr>

            <tr v-else-if="store.isEmpty">
              <td :colspan="canSeePurchase ? 9 : 8" class="empty-state">
                Mahsulot topilmadi. «Mahsulot qo‘shish» tugmasi bilan birinchisini yarating.
              </td>
            </tr>

            <template v-for="product in store.products" v-else :key="product.id">
              <tr>
                <td>
                  <button
                    v-if="hasManyVariants(product)"
                    class="expand-toggle"
                    type="button"
                    @click="toggle(product.id)"
                  >
                    {{ expanded.has(product.id) ? '−' : '+' }}
                  </button>

                  <strong>{{ product.name }}</strong>

                  <small class="cell-sub">
                    {{ product.brand || '—' }}
                    <template v-if="hasManyVariants(product)">
                      · {{ product.variants.length }} variant
                    </template>
                    <template v-else-if="firstVariant(product)">
                      · {{ firstVariant(product)!.sku }}
                    </template>
                  </small>
                </td>

                <td>{{ product.category_name }}</td>

                <td class="attr-cell">
                  {{ hasManyVariants(product) ? '—' : attributeSummary(firstVariant(product)) }}
                </td>

                <td>{{ product.effective_unit || '—' }}</td>

                <td class="attr-cell">
                  {{ hasManyVariants(product) ? '—' : packSummary(firstVariant(product)) }}
                </td>

                <td v-if="canSeePurchase" class="num">{{ money(firstVariant(product)?.purchase_price ?? null) }}</td>
                <td class="num">{{ money(firstVariant(product)?.sale_price ?? null) }}</td>

                <td>
                  <span class="pill" :class="product.is_active ? 'pill-on' : 'pill-off'">
                    {{ product.is_active ? 'Faol' : 'Faol emas' }}
                  </span>
                </td>

                <td class="row-actions">
                  <button class="button button-soft" type="button" @click="openEdit(product)">
                    Tahrirlash
                  </button>

                  <button class="button button-danger" type="button" @click="onDelete(product)">
                    <svg><use href="#i-trash" /></svg>
                  </button>
                </td>
              </tr>

              <tr
                v-for="variant in expanded.has(product.id) ? product.variants : []"
                :key="variant.id"
                class="variant-row"
              >
                <td>
                  <span class="variant-marker"></span>
                  {{ variant.name || variant.sku }}
                  <small class="cell-sub">{{ variant.sku }}</small>
                </td>

                <td></td>
                <td class="attr-cell">{{ attributeSummary(variant) }}</td>
                <td></td>
                <td class="attr-cell">{{ packSummary(variant) }}</td>
                <td v-if="canSeePurchase" class="num">{{ money(variant.purchase_price) }}</td>
                <td class="num">{{ money(variant.sale_price) }}</td>
                <td colspan="2"></td>
              </tr>
            </template>
          </tbody>
        </table>
      </div>
    </div>

    <ProductModal
      :show="modalOpen"
      :product="editing"
      @close="modalOpen = false"
      @saved="store.loadProducts()"
    />
  </section>
</template>

<style scoped>

.kpi-grid.compact {
  margin-bottom: 16px;
}

.attr-cell {
  max-width: 220px;
  color: var(--text-secondary);
  font-size: 12px;
}

.variant-row {
  background: var(--surface-soft);
}

.variant-marker {
  display: inline-block;
  width: 14px;
  margin-right: 6px;
  border-bottom: 1px solid var(--border-strong);
  vertical-align: middle;
}

</style>
