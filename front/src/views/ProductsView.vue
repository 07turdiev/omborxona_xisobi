<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'

import LabelPrint from '@/components/LabelPrint.vue'
import ProductImages from '@/components/ProductImages.vue'
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
const notice = ref('')
const saving = ref(false)

const expanded = ref<number | null>(null)
const formOpen = ref(false)
const editing = ref<Product | null>(null)

const form = ref({
  category: 0,
  name: '',
  slug: '',
  brand: '',
  description: '',
  material: '',
  care: '',
  sale_price: '',
  mxik_code: '',
  package_code: '',
  size_ids: [] as number[],
  color_ids: [] as number[],
})

/** MXIK kodi yo'q mahsulotlar — fiskal chekda rad etiladi */
const withoutMxik = computed(() => products.value.filter((item) => !item.effective_mxik_code))

/** Rasmni shu ranglardan biriga biriktirish mumkin */
const formColors = computed(() => colors.value.filter((item) => form.value.color_ids.includes(item.id)))

/** Formaning ichidagi xabar — sahifadagisi ochiq oyna ortida ko'rinmaydi */
const formNotice = ref('')
const formError = ref('')

/** Yorliqqa chiqariladigan variantlar */
const labelItems = ref<{ barcode: string; name: string; label: string; price: string; quantity: number }[]>([])
const labels = ref<InstanceType<typeof LabelPrint> | null>(null)

const newCategory = ref('')
const newSize = ref('')
const newColor = ref('')
const newColorHex = ref('#808080')

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
  formNotice.value = ''
  formError.value = ''

  form.value = {
    category: categories.value[0]?.id ?? 0,
    name: '',
    slug: '',
    brand: '',
    description: '',
    material: '',
    care: '',
    sale_price: '',
    mxik_code: '',
    package_code: '',
    size_ids: [],
    color_ids: [],
  }

  formOpen.value = true
}

function openEdit(product: Product) {
  editing.value = product
  formNotice.value = ''
  formError.value = ''

  // Mavjud variantlardan o'lcham va ranglar tiklanadi
  form.value = {
    category: product.category,
    name: product.name,
    slug: product.slug,
    brand: product.brand,
    description: product.description,
    material: product.material,
    care: product.care,
    sale_price: product.sale_price,
    mxik_code: product.mxik_code,
    package_code: product.package_code,
    size_ids: [...new Set(product.variants.map((item) => item.size).filter((id): id is number => id !== null))],
    color_ids: [...new Set(product.variants.map((item) => item.color).filter((id): id is number => id !== null))],
  }

  formOpen.value = true
}

async function onSave() {
  if (!form.value.name.trim() || saving.value) return

  saving.value = true
  formError.value = ''
  formNotice.value = ''

  const payload: ProductInput = {
    category: form.value.category,
    name: form.value.name,
    brand: form.value.brand,
    description: form.value.description,
    material: form.value.material.trim(),
    care: form.value.care.trim(),
    sale_price: normalizeMoneyInput(form.value.sale_price || '0'),
    mxik_code: form.value.mxik_code.trim(),
    package_code: form.value.package_code.trim(),
    size_ids: form.value.size_ids,
    color_ids: form.value.color_ids,
  }

  // Bo'sh bo'lsa yuborilmaydi: yangi mahsulotda nomdan yasaladi,
  // mavjudida esa o'zgarmaydi (tashqi havolalar uzilmasin)
  if (form.value.slug.trim()) payload.slug = form.value.slug.trim()

  try {
    if (editing.value) {
      await catalogApi.updateProduct(editing.value.id, payload)
      formOpen.value = false
    } else {
      // Yaratilgach forma yopilmaydi: rasmni darhol shu yerda qo'shish mumkin
      const created = await catalogApi.createProduct(payload)

      editing.value = created
      form.value.slug = created.slug
      formNotice.value = 'Saqlandi. Endi rasm qo‘shishingiz mumkin.'
    }

    await load()
  } catch (err) {
    formError.value = errorMessage(err, 'Saqlab bo‘lmadi.')
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

/** Kategoriyaning MXIK kodi — shu kategoriyadagi hamma mahsulotga tarqaladi. */
async function saveCategoryCode(item: Category, value: string) {
  error.value = ''
  notice.value = ''

  try {
    await catalogApi.updateCategory(item.id, { mxik_code: value.trim() })

    notice.value = `${item.name}: MXIK kodi saqlandi.`
    await loadAttributes()
    await load()
  } catch (err) {
    error.value = errorMessage(err, 'MXIK kodini saqlab bo‘lmadi.')
    await loadAttributes()
  }
}

async function addSize() {
  if (!newSize.value.trim()) return

  await catalogApi.createSize({ name: newSize.value.trim(), position: sizes.value.length + 1 })
  newSize.value = ''
  await loadAttributes()
}

async function addColor() {
  if (!newColor.value.trim()) return

  error.value = ''

  try {
    await catalogApi.createColor({
      name: newColor.value.trim(),
      hex_code: newColorHex.value.toUpperCase(),
    })

    newColor.value = ''
    newColorHex.value = '#808080'
    await loadAttributes()
  } catch (err) {
    error.value = errorMessage(err, 'Rangni qo‘shib bo‘lmadi.')
  }
}

/** Katalogdagi rang doirachasi shu kod bilan chiziladi */
async function saveColorHex(item: Color, value: string) {
  error.value = ''

  try {
    await catalogApi.updateColor(item.id, { hex_code: value.toUpperCase() })
    await loadAttributes()
  } catch (err) {
    error.value = errorMessage(err, 'Rang kodini saqlab bo‘lmadi.')
  }
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
    <p v-if="notice" class="notice">{{ notice }}</p>

    <template v-if="tab === 'products'">
      <!-- Fiskal chek MXIK kodisiz rad etiladi -->
      <p v-if="auth.isAdmin && withoutMxik.length" class="mxik-warning">
        <strong>{{ withoutMxik.length }} ta mahsulotda MXIK kodi yo‘q.</strong>
        Fiskal chek bunday tovarni qabul qilmaydi. Kodni kategoriyaga bir marta
        yozsangiz, ichidagi hamma mahsulotga tarqaladi —
        <button class="link-button" type="button" @click="tab = 'attributes'">
          Kategoriya bo‘limi
        </button>
      </p>

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
                <th v-if="auth.isAdmin">MXIK</th>
                <th class="num">Narxi</th>
                <th class="num">Variantlar</th>
                <th></th>
              </tr>
            </thead>

            <tbody>
              <tr v-if="loading">
                <td :colspan="auth.isAdmin ? 7 : 6" class="empty-state">Yuklanmoqda…</td>
              </tr>

              <tr v-else-if="!products.length">
                <td :colspan="auth.isAdmin ? 7 : 6" class="empty-state">Mahsulot topilmadi.</td>
              </tr>

              <template v-for="product in products" v-else :key="product.id">
                <tr class="clickable" @click="expanded = expanded === product.id ? null : product.id">
                  <td><strong>{{ product.name }}</strong></td>
                  <td>{{ product.category_name }}</td>
                  <td>{{ product.brand || '—' }}</td>

                  <td v-if="auth.isAdmin">
                    <span v-if="product.effective_mxik_code" class="mxik-code">
                      {{ product.effective_mxik_code }}
                    </span>
                    <span v-else class="pill pill-red">yo‘q</span>
                  </td>

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
                  <td :colspan="auth.isAdmin ? 7 : 6" class="variants-cell">
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
      <div class="table-card card-padded wide">
        <h3>Kategoriyalar</h3>

        <div class="add-row">
          <input v-model="newCategory" type="text" placeholder="Yangi kategoriya" @keydown.enter="addCategory" />
          <button class="button button-outline" type="button" @click="addCategory">Qo‘shish</button>
        </div>

        <p class="field-hint">
          MXIK — soliq tasnifi kodi, 17 xonali raqam. Kodni tasnif.soliq.uz dan
          oling; u shu kategoriyadagi hamma mahsulotga tarqaladi.
        </p>

        <table class="data-table">
          <thead>
            <tr>
              <th>Nomi</th>
              <th>MXIK kodi</th>
              <th></th>
            </tr>
          </thead>

          <tbody>
            <tr v-for="item in categories" :key="item.id">
              <td>{{ item.name }}</td>
              <td>
                <input
                  class="mxik-input"
                  type="text"
                  inputmode="numeric"
                  maxlength="17"
                  placeholder="17 xonali raqam"
                  :value="item.mxik_code"
                  @change="saveCategoryCode(item, ($event.target as HTMLInputElement).value)"
                />
              </td>
              <td class="num">
                <button class="icon-button delete" type="button" @click="removeAttribute('category', item.id)">
                  <svg><use href="#i-trash" /></svg>
                </button>
              </td>
            </tr>
          </tbody>
        </table>
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
          <input v-model="newColorHex" class="color-input" type="color" aria-label="Rang kodi" />
          <button class="button button-outline" type="button" @click="addColor">Qo‘shish</button>
        </div>

        <ul class="attribute-list">
          <li v-for="item in colors" :key="item.id">
            <span class="color-row">
              <input
                class="color-input"
                type="color"
                :value="item.hex_code"
                :aria-label="`${item.name} rang kodi`"
                @change="saveColorHex(item, ($event.target as HTMLInputElement).value)"
              />
              <span>{{ item.name }}</span>
              <small>{{ item.hex_code }}</small>
            </span>
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

        <p v-if="formError" class="load-error">{{ formError }}</p>
        <p v-if="formNotice" class="notice">{{ formNotice }}</p>

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
          <label>Tarkibi</label>
          <input v-model="form.material" type="text" placeholder="60% paxta, 40% polyester" />
        </div>

        <div class="field">
          <label>Parvarish</label>
          <input v-model="form.care" type="text" placeholder="30° da yuvish, past haroratda dazmollash" />
        </div>

        <div class="field">
          <label>Tavsif</label>
          <textarea v-model="form.description" rows="3" />
        </div>

        <div class="field">
          <label>Sotuv narxi</label>
          <input v-model="form.sale_price" type="text" inputmode="decimal" />
        </div>

        <div class="field">
          <label>MXIK kodi</label>
          <input
            v-model="form.mxik_code"
            type="text"
            inputmode="numeric"
            maxlength="17"
            placeholder="Bo‘sh qoldirilsa kategoriyaniki"
          />
          <small class="field-hint">
            Faqat shu mahsulotning kodi kategoriyanikidan farq qilsa to‘ldiring.
          </small>
        </div>

        <div class="field">
          <label>Manzil qismi (slug)</label>
          <input v-model="form.slug" type="text" placeholder="Nomdan avtomatik yasaladi" />
          <small class="field-hint">
            Kelajakdagi onlayn do‘kon manzili. Do‘kon ochilgach o‘zgartirmang —
            tashqi havolalar uziladi.
          </small>
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

        <div class="field">
          <ProductImages v-if="editing" :product-id="editing.id" :colors="formColors" />

          <p v-else class="field-hint">
            Rasm qo‘shish uchun avval mahsulotni saqlang — forma yopilmaydi.
          </p>
        </div>

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

.mxik-warning {
  margin: 0 0 12px;
  padding: 10px 12px;
  border: 1px solid var(--orange);
  border-radius: var(--radius);
  background: var(--orange-soft);
  font-size: 13px;
}

.link-button {
  border: 0;
  background: none;
  padding: 0;
  color: var(--accent);
  font-size: 13px;
  font-weight: 600;
  text-decoration: underline;
  cursor: pointer;
}

.mxik-code {
  font-size: 12px;
  font-variant-numeric: tabular-nums;
  color: var(--text-muted);
}

.mxik-input {
  width: 190px;
  font-variant-numeric: tabular-nums;
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

.attributes .wide {
  grid-column: 1 / -1;
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

.color-row {
  display: inline-flex;
  align-items: center;
  gap: 8px;
}

.color-row small {
  color: var(--text-muted);
  font-variant-numeric: tabular-nums;
}

.color-input {
  flex: none;
  width: 34px;
  height: 34px;
  padding: 2px;
  border: 1px solid var(--border-strong);
  border-radius: var(--radius);
  background: var(--surface);
  cursor: pointer;
}

.overlay-card {
  width: 100%;
  max-width: 560px;
  max-height: 90vh;
  overflow-y: auto;
  padding: 20px;
  border-radius: var(--radius);
  background: var(--surface);
}

.overlay-card > .field {
  margin-bottom: 12px;
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
