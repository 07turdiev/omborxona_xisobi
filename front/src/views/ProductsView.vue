<script setup lang="ts">
import { onMounted, ref } from 'vue'

import LabelPrint from '@/components/LabelPrint.vue'
import { catalogApi, type ProductInput } from '@/api/catalog'
import { errorMessage } from '@/api/client'
import { useAuthStore } from '@/stores/auth'
import { formatMoney, normalizeMoneyInput } from '@/utils/money'
import type { Category, Color, Product, Size, Variant } from '@/types'

const auth = useAuthStore()

const tab = ref<'products' | 'attributes'>('products')

const products = ref<Product[]>([])
const categories = ref<Category[]>([])
const sizes = ref<Size[]>([])
const colors = ref<Color[]>([])

const search = ref('')
const category = ref('')
const loading = ref(false)
const error = ref('')
const saving = ref(false)

const expanded = ref<number | null>(null)
const formOpen = ref(false)
const editing = ref<Product | null>(null)

const form = ref({
  category: 0,
  name: '',
  brand: '',
  sale_price: '',
  size_ids: [] as number[],
  color_ids: [] as number[],
})

/** Yorliqqa chiqariladigan variantlar */
const labelItems = ref<{ barcode: string; name: string; label: string; price: string; quantity: number }[]>([])
const labels = ref<InstanceType<typeof LabelPrint> | null>(null)

const newCategory = ref('')
const newSize = ref('')
const newColor = ref('')

async function load() {
  loading.value = true
  error.value = ''

  try {
    const page = await catalogApi.products({
      search: search.value || undefined,
      category: category.value || undefined,
    })

    products.value = page.results
  } catch (err) {
    error.value = errorMessage(err, 'Mahsulotlarni yuklab bo‘lmadi.')
  } finally {
    loading.value = false
  }
}

async function loadAttributes() {
  ;[categories.value, sizes.value, colors.value] = await Promise.all([
    catalogApi.categories(),
    catalogApi.sizes(),
    catalogApi.colors(),
  ])
}

function openCreate() {
  editing.value = null
  form.value = {
    category: categories.value[0]?.id ?? 0,
    name: '',
    brand: '',
    sale_price: '',
    size_ids: [],
    color_ids: [],
  }

  formOpen.value = true
}

function openEdit(product: Product) {
  editing.value = product

  // Mavjud variantlardan o'lcham va ranglar tiklanadi
  form.value = {
    category: product.category,
    name: product.name,
    brand: product.brand,
    sale_price: product.sale_price,
    size_ids: [...new Set(product.variants.map((item) => item.size).filter((id): id is number => id !== null))],
    color_ids: [...new Set(product.variants.map((item) => item.color).filter((id): id is number => id !== null))],
  }

  formOpen.value = true
}

async function onSave() {
  if (!form.value.name.trim() || saving.value) return

  saving.value = true
  error.value = ''

  const payload: ProductInput = {
    category: form.value.category,
    name: form.value.name,
    brand: form.value.brand,
    sale_price: normalizeMoneyInput(form.value.sale_price || '0'),
    size_ids: form.value.size_ids,
    color_ids: form.value.color_ids,
  }

  try {
    if (editing.value) {
      await catalogApi.updateProduct(editing.value.id, payload)
    } else {
      await catalogApi.createProduct(payload)
    }

    formOpen.value = false
    await load()
  } catch (err) {
    error.value = errorMessage(err, 'Saqlab bo‘lmadi.')
  } finally {
    saving.value = false
  }
}

function toggle(list: number[], id: number) {
  const index = list.indexOf(id)

  if (index === -1) list.push(id)
  else list.splice(index, 1)
}

/** Tanlangan variantlar uchun yorliq chop etadi. */
function printLabels(product: Product, variant?: Variant) {
  const rows = variant ? [variant] : product.variants

  labelItems.value = rows
    .filter((item) => item.barcode)
    .map((item) => ({
      barcode: item.barcode,
      name: product.name,
      label: item.label,
      price: item.price,
      quantity: 1,
    }))

  // Ro'yxat DOM'ga chiqishi uchun keyingi kadrda chop etamiz
  setTimeout(() => labels.value?.printLabels(), 50)
}

async function addCategory() {
  if (!newCategory.value.trim()) return

  await catalogApi.createCategory(newCategory.value.trim())
  newCategory.value = ''
  await loadAttributes()
}

async function addSize() {
  if (!newSize.value.trim()) return

  await catalogApi.createSize({ name: newSize.value.trim(), position: sizes.value.length + 1 })
  newSize.value = ''
  await loadAttributes()
}

async function addColor() {
  if (!newColor.value.trim()) return

  await catalogApi.createColor(newColor.value.trim())
  newColor.value = ''
  await loadAttributes()
}

async function removeAttribute(kind: 'category' | 'size' | 'color', id: number) {
  if (!window.confirm('O‘chirilsinmi?')) return

  try {
    if (kind === 'category') await catalogApi.removeCategory(id)
    if (kind === 'size') await catalogApi.removeSize(id)
    if (kind === 'color') await catalogApi.removeColor(id)

    await loadAttributes()
  } catch (err) {
    error.value = errorMessage(err, 'O‘chirib bo‘lmadi — bog‘liq tovarlar bor.')
  }
}

onMounted(async () => {
  await loadAttributes()
  await load()
})
</script>

<template>
  <section class="app-section active">
    <div class="tabs">
      <button
        class="tab"
        :class="{ active: tab === 'products' }"
        type="button"
        @click="tab = 'products'"
      >
        Mahsulotlar
      </button>

      <button
        v-if="auth.isAdmin"
        class="tab"
        :class="{ active: tab === 'attributes' }"
        type="button"
        @click="tab = 'attributes'"
      >
        Kategoriya, o‘lcham, rang
      </button>
    </div>

    <p v-if="error" class="load-error">{{ error }}</p>

    <template v-if="tab === 'products'">
      <div class="section-toolbar">
        <div class="filters">
          <div class="search-field">
            <svg><use href="#i-search" /></svg>
            <input
              v-model="search"
              type="search"
              placeholder="Mahsulot nomi…"
              @keydown.enter.prevent="load"
            />
          </div>

          <select v-model="category" @change="load">
            <option value="">Barcha kategoriya</option>
            <option v-for="item in categories" :key="item.id" :value="item.id">
              {{ item.name }}
            </option>
          </select>

          <button class="button button-outline" type="button" @click="load">Qidirish</button>
        </div>

        <button v-if="auth.isAdmin" class="button button-gradient" type="button" @click="openCreate">
          <svg><use href="#i-plus" /></svg>
          <span>Yangi mahsulot</span>
        </button>
      </div>

      <div class="table-card">
        <div class="table-scroll">
          <table class="data-table">
            <thead>
              <tr>
                <th>Nomi</th>
                <th>Kategoriya</th>
                <th>Brend</th>
                <th class="num">Narxi</th>
                <th class="num">Variantlar</th>
                <th></th>
              </tr>
            </thead>

            <tbody>
              <tr v-if="loading">
                <td colspan="6" class="empty-state">Yuklanmoqda…</td>
              </tr>

              <tr v-else-if="!products.length">
                <td colspan="6" class="empty-state">Mahsulot topilmadi.</td>
              </tr>

              <template v-for="product in products" v-else :key="product.id">
                <tr class="clickable" @click="expanded = expanded === product.id ? null : product.id">
                  <td><strong>{{ product.name }}</strong></td>
                  <td>{{ product.category_name }}</td>
                  <td>{{ product.brand || '—' }}</td>
                  <td class="num">{{ formatMoney(product.sale_price) }}</td>
                  <td class="num">{{ product.variants.length }}</td>
                  <td class="num row-actions">
                    <button
                      v-if="auth.isAdmin"
                      class="button button-outline"
                      type="button"
                      @click.stop="openEdit(product)"
                    >
                      Tahrirlash
                    </button>

                    <button
                      class="button button-outline"
                      type="button"
                      @click.stop="printLabels(product)"
                    >
                      Yorliqlar
                    </button>
                  </td>
                </tr>

                <tr v-if="expanded === product.id" :key="`v-${product.id}`">
                  <td colspan="6" class="variants-cell">
                    <table class="data-table">
                      <thead>
                        <tr>
                          <th>Variant</th>
                          <th>SKU</th>
                          <th>Shtrix-kod</th>
                          <th class="num">Qoldiq</th>
                          <th class="num">Narx</th>
                          <th></th>
                        </tr>
                      </thead>

                      <tbody>
                        <tr v-for="variant in product.variants" :key="variant.id">
                          <td>{{ variant.label || '—' }}</td>
                          <td>{{ variant.sku }}</td>
                          <td>{{ variant.barcode }}</td>
                          <td class="num">{{ variant.stock_quantity }}</td>
                          <td class="num">{{ formatMoney(variant.price) }}</td>
                          <td class="num">
                            <button
                              class="button button-outline"
                              type="button"
                              @click="printLabels(product, variant)"
                            >
                              <svg><use href="#i-print" /></svg>
                              <span>Yorliq</span>
                            </button>
                          </td>
                        </tr>
                      </tbody>
                    </table>
                  </td>
                </tr>
              </template>
            </tbody>
          </table>
        </div>
      </div>
    </template>

    <div v-else class="attributes">
      <div class="table-card card-padded">
        <h3>Kategoriyalar</h3>

        <div class="add-row">
          <input v-model="newCategory" type="text" placeholder="Yangi kategoriya" @keydown.enter="addCategory" />
          <button class="button button-outline" type="button" @click="addCategory">Qo‘shish</button>
        </div>

        <ul class="attribute-list">
          <li v-for="item in categories" :key="item.id">
            <span>{{ item.name }}</span>
            <button class="icon-button delete" type="button" @click="removeAttribute('category', item.id)">
              <svg><use href="#i-trash" /></svg>
            </button>
          </li>
        </ul>
      </div>

      <div class="table-card card-padded">
        <h3>O‘lchamlar</h3>

        <div class="add-row">
          <input v-model="newSize" type="text" placeholder="S, M, L, 42…" @keydown.enter="addSize" />
          <button class="button button-outline" type="button" @click="addSize">Qo‘shish</button>
        </div>

        <ul class="attribute-list">
          <li v-for="item in sizes" :key="item.id">
            <span>{{ item.name }}</span>
            <button class="icon-button delete" type="button" @click="removeAttribute('size', item.id)">
              <svg><use href="#i-trash" /></svg>
            </button>
          </li>
        </ul>
      </div>

      <div class="table-card card-padded">
        <h3>Ranglar</h3>

        <div class="add-row">
          <input v-model="newColor" type="text" placeholder="Qora, oq…" @keydown.enter="addColor" />
          <button class="button button-outline" type="button" @click="addColor">Qo‘shish</button>
        </div>

        <ul class="attribute-list">
          <li v-for="item in colors" :key="item.id">
            <span>{{ item.name }}</span>
            <button class="icon-button delete" type="button" @click="removeAttribute('color', item.id)">
              <svg><use href="#i-trash" /></svg>
            </button>
          </li>
        </ul>
      </div>
    </div>

    <!-- Mahsulot formasi -->
    <div v-if="formOpen" class="overlay" @click.self="formOpen = false">
      <div class="overlay-card">
        <h3>{{ editing ? 'Mahsulotni tahrirlash' : 'Yangi mahsulot' }}</h3>

        <div class="field">
          <label>Kategoriya</label>
          <select v-model.number="form.category">
            <option v-for="item in categories" :key="item.id" :value="item.id">{{ item.name }}</option>
          </select>
        </div>

        <div class="field">
          <label>Nomi</label>
          <input v-model="form.name" type="text" />
        </div>

        <div class="field">
          <label>Brend</label>
          <input v-model="form.brand" type="text" />
        </div>

        <div class="field">
          <label>Sotuv narxi</label>
          <input v-model="form.sale_price" type="text" inputmode="decimal" />
        </div>

        <div class="field">
          <label>O‘lchamlar</label>

          <div class="chips">
            <button
              v-for="item in sizes"
              :key="item.id"
              class="chip"
              :class="{ active: form.size_ids.includes(item.id) }"
              type="button"
              @click="toggle(form.size_ids, item.id)"
            >
              {{ item.name }}
            </button>
          </div>
        </div>

        <div class="field">
          <label>Ranglar</label>

          <div class="chips">
            <button
              v-for="item in colors"
              :key="item.id"
              class="chip"
              :class="{ active: form.color_ids.includes(item.id) }"
              type="button"
              @click="toggle(form.color_ids, item.id)"
            >
              {{ item.name }}
            </button>
          </div>
        </div>

        <p class="field-hint">
          Har o‘lcham va rang juftligi uchun alohida variant va shtrix-kod yaratiladi.
        </p>

        <div class="form-actions">
          <button class="button button-outline" type="button" @click="formOpen = false">
            Bekor qilish
          </button>

          <button class="button button-gradient" type="button" :disabled="saving" @click="onSave">
            {{ saving ? 'Saqlanmoqda…' : 'Saqlash' }}
          </button>
        </div>
      </div>
    </div>

    <LabelPrint ref="labels" :items="labelItems" />
  </section>
</template>

<style scoped>
.tabs {
  display: flex;
  gap: 4px;
  margin-bottom: 12px;
  border-bottom: 1px solid var(--border);
}

.tab {
  padding: 8px 14px;
  border: 0;
  border-bottom: 2px solid transparent;
  background: none;
  color: var(--text-muted);
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
}

.tab.active {
  border-bottom-color: var(--accent);
  color: var(--text);
}

.clickable {
  cursor: pointer;
}

.variants-cell {
  padding: 0 0 0 24px;
  background: var(--surface-hover, var(--bg));
}

.row-actions .button {
  margin-left: 6px;
}

.attributes {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
  gap: 12px;
}

.add-row {
  display: flex;
  gap: 6px;
  margin: 10px 0;
}

.attribute-list {
  margin: 0;
  padding: 0;
  list-style: none;
}

.attribute-list li {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 6px 0;
  border-bottom: 1px solid var(--border);
  font-size: 13px;
}

.overlay {
  position: fixed;
  inset: 0;
  z-index: 50;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 16px;
  background: rgb(15 23 42 / 45%);
}

.overlay-card {
  width: 100%;
  max-width: 460px;
  max-height: 90vh;
  overflow-y: auto;
  padding: 20px;
  border-radius: var(--radius);
  background: var(--surface);
}

.chips {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.chip {
  padding: 5px 10px;
  border: 1px solid var(--border);
  border-radius: 999px;
  background: var(--surface);
  color: var(--text);
  font-size: 12px;
  cursor: pointer;
}

.chip.active {
  border-color: var(--accent);
  background: var(--accent-soft);
  font-weight: 600;
}

.form-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 16px;
}
</style>
