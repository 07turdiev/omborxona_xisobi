<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'

import { catalogApi } from '@/api/catalog'
import { useCatalogStore } from '@/stores/catalog'
import type { AttributeDefinition, Category } from '@/types'

const store = useCatalogStore()

const selected = ref<Category | null>(null)
const inherited = ref<AttributeDefinition[]>([])
const own = ref<AttributeDefinition[]>([])

const loading = ref(false)
const saving = ref(false)
const error = ref('')

// Kategoriya oynasi
const categoryOpen = ref(false)
const editingCategory = ref<Category | null>(null)
const categoryErrors = ref<Record<string, string[]>>({})

function emptyCategory(): Partial<Category> {
  return { name: '', parent: null, default_unit: '', code_prefix: '', is_active: true }
}

const categoryForm = reactive<Partial<Category>>(emptyCategory())

// Atribut oynasi
const attributeOpen = ref(false)
const editingAttribute = ref<AttributeDefinition | null>(null)
const attributeErrors = ref<Record<string, string[]>>({})

function emptyAttribute(): Partial<AttributeDefinition> {
  return {
    key: '',
    name: '',
    value_type: 'text',
    unit: '',
    choices: [],
    default_value: '',
    is_required: false,
    is_variant_axis: false,
    uniqueness: 0,
    position: 0,
  }
}

const attributeForm = reactive<Partial<AttributeDefinition>>(emptyAttribute())
/** Tanlovlar formada bitta matn maydonida, vergul bilan. */
const choicesText = ref('')

const valueTypes = [
  { value: 'text', label: 'Matn' },
  { value: 'number', label: 'Son' },
  { value: 'choice', label: 'Ro‘yxatdan tanlash' },
  { value: 'boolean', label: 'Ha / yo‘q' },
]

async function loadCategories() {
  loading.value = true
  error.value = ''

  try {
    await store.loadCategories()

    // Tanlangan kategoriya o'chirilgan bo'lsa, tanlovni tozalaymiz
    if (selected.value && !store.categories.some((c) => c.id === selected.value?.id)) {
      selected.value = null
    }
  } catch {
    error.value = 'Kategoriyalarni olishda xatolik.'
  } finally {
    loading.value = false
  }
}

/** Tanlangan kategoriyaning atributlari: o'ziniki va meros olganlari. */
async function loadAttributes(category: Category) {
  const [all, mine] = await Promise.all([
    catalogApi.categoryAttributes(category.id),
    catalogApi.attributeDefinitions(category.id),
  ])

  const ownKeys = new Set(mine.map((d) => d.key))

  own.value = mine
  inherited.value = all.filter((d) => !ownKeys.has(d.key))
}

onMounted(loadCategories)

watch(selected, (category) => {
  if (category) {
    loadAttributes(category)
  } else {
    own.value = []
    inherited.value = []
  }
})

function asErrors(err: unknown): Record<string, string[]> {
  const data = (err as { response?: { data?: unknown } }).response?.data

  if (data && typeof data === 'object') return data as Record<string, string[]>

  return { detail: ['Kutilmagan xatolik.'] }
}

// -- kategoriya ------------------------------------------------------

function openCategoryCreate(parent: Category | null = null) {
  editingCategory.value = null
  categoryErrors.value = {}
  Object.assign(categoryForm, emptyCategory(), { parent: parent?.id ?? null })
  categoryOpen.value = true
}

function openCategoryEdit(category: Category) {
  editingCategory.value = category
  categoryErrors.value = {}
  Object.assign(categoryForm, { ...category })
  categoryOpen.value = true
}

async function onSaveCategory() {
  categoryErrors.value = {}
  saving.value = true

  try {
    if (editingCategory.value) {
      await catalogApi.updateCategory(editingCategory.value.id, categoryForm)
    } else {
      await catalogApi.createCategory(categoryForm)
    }

    categoryOpen.value = false
    store.clearAttributeCache()
    await loadCategories()
  } catch (err) {
    categoryErrors.value = asErrors(err)
  } finally {
    saving.value = false
  }
}

async function onDeleteCategory(category: Category) {
  const children = store.categories.filter((c) => c.parent === category.id)

  if (children.length) {
    error.value =
      `"${category.name}" ichida ${children.length} ta ostki kategoriya bor. ` +
      'Avval ularni o‘chiring yoki boshqa joyga ko‘chiring.'
    return
  }

  if (category.product_count > 0) {
    error.value =
      `"${category.name}" da ${category.product_count} ta mahsulot bor. ` +
      'Kategoriyani o‘chirish uchun avval mahsulotlarni ko‘chiring.'
    return
  }

  if (!window.confirm(`"${category.name}" o‘chirilsinmi?`)) return

  error.value = ''

  try {
    await catalogApi.removeCategory(category.id)

    if (selected.value?.id === category.id) selected.value = null

    store.clearAttributeCache()
    await loadCategories()
  } catch (err) {
    error.value = Object.values(asErrors(err)).flat()[0] ?? 'O‘chirib bo‘lmadi.'
  }
}

// -- atribut ---------------------------------------------------------

function openAttributeCreate() {
  editingAttribute.value = null
  attributeErrors.value = {}
  Object.assign(attributeForm, emptyAttribute())
  choicesText.value = ''
  attributeOpen.value = true
}

function openAttributeEdit(definition: AttributeDefinition) {
  editingAttribute.value = definition
  attributeErrors.value = {}
  Object.assign(attributeForm, { ...definition })
  choicesText.value = (definition.choices ?? []).join(', ')
  attributeOpen.value = true
}

async function onSaveAttribute() {
  if (!selected.value) return

  attributeErrors.value = {}
  saving.value = true

  try {
    const payload = {
      ...attributeForm,
      category: selected.value.id,
      choices: choicesText.value
        .split(',')
        .map((item) => item.trim())
        .filter(Boolean),
    }

    if (editingAttribute.value) {
      await catalogApi.updateAttributeDefinition(editingAttribute.value.id, payload)
    } else {
      await catalogApi.createAttributeDefinition(payload)
    }

    attributeOpen.value = false
    store.clearAttributeCache()
    await loadAttributes(selected.value)
  } catch (err) {
    attributeErrors.value = asErrors(err)
  } finally {
    saving.value = false
  }
}

async function onDeleteAttribute(definition: AttributeDefinition) {
  const ok = window.confirm(
    `"${definition.name}" atributi o‘chirilsinmi?\n\n` +
      'Mahsulotlardagi qiymatlar bazada qoladi, lekin interfeysda ' +
      'ko‘rinmay qoladi.',
  )

  if (!ok || !selected.value) return

  await catalogApi.removeAttributeDefinition(definition.id)
  store.clearAttributeCache()
  await loadAttributes(selected.value)
}

const categoryError = (field: string) => categoryErrors.value[field]?.[0] ?? ''
const attributeError = (field: string) => attributeErrors.value[field]?.[0] ?? ''

/** Formada faqat tegishli maydonlar ko'rinsin. */
const isNumberType = computed(() => attributeForm.value_type === 'number')
const isChoiceType = computed(() => attributeForm.value_type === 'choice')
</script>

<template>
  <section class="app-section active">
    <div class="section-toolbar">
      <div class="filters">
        <RouterLink to="/products" class="button button-soft">
          <svg><use href="#i-company" /></svg>
          <span>Mahsulotlarga qaytish</span>
        </RouterLink>
      </div>

      <button class="button button-gradient" @click="openCategoryCreate(null)">
        <svg><use href="#i-plus" /></svg>
        <span>Ildiz kategoriya</span>
      </button>
    </div>

    <p v-if="error" class="load-error">{{ error }}</p>

    <div class="split">
      <!-- Daraxt -->
      <div class="table-card tree-card">
        <h3>Kategoriya daraxti</h3>

        <p v-if="loading" class="empty-state">Yuklanmoqda…</p>

        <p v-else-if="!store.categories.length" class="empty-state">
          Kategoriya yo‘q. Mahsulot qo‘shish uchun kamida bittasi kerak.
        </p>

        <ul v-else class="tree">
          <li
            v-for="category in store.categories"
            :key="category.id"
            :style="{ paddingLeft: `${(category.depth - 1) * 16}px` }"
          >
            <button
              class="tree-node"
              :class="{ active: selected?.id === category.id }"
              type="button"
              @click="selected = category"
            >
              <span class="tree-name">
                {{ category.name }}
                <small v-if="!category.is_active" class="off">faol emas</small>
              </span>

              <span class="tree-meta">
                <b v-if="category.product_count">{{ category.product_count }}</b>
                <span v-if="category.default_unit" class="unit">
                  {{ category.default_unit }}
                </span>
              </span>
            </button>
          </li>
        </ul>
      </div>

      <!-- Tanlangan kategoriya -->
      <div class="detail">
        <p v-if="!selected" class="table-card empty-state">
          Chapdan kategoriya tanlang.
        </p>

        <template v-else>
          <div class="table-card">
            <div class="detail-head">
              <div>
                <h3>{{ selected.name }}</h3>
                <p class="path">{{ selected.path }}</p>
              </div>

              <div class="detail-actions">
                <button
                  class="button button-soft"
                  type="button"
                  @click="openCategoryCreate(selected)"
                >
                  <svg><use href="#i-plus" /></svg>
                  <span>Ostki kategoriya</span>
                </button>

                <button
                  class="button button-soft"
                  type="button"
                  @click="openCategoryEdit(selected)"
                >
                  Tahrirlash
                </button>

                <button
                  class="button button-danger"
                  type="button"
                  @click="onDeleteCategory(selected)"
                >
                  <svg><use href="#i-trash" /></svg>
                </button>
              </div>
            </div>

            <div class="meta-grid">
              <div>
                <span>Daraja</span>
                <strong>{{ selected.depth }}</strong>
              </div>
              <div>
                <span>Mahsulotlar</span>
                <strong>{{ selected.product_count }}</strong>
              </div>
              <div>
                <span>Standart birlik</span>
                <strong>{{ selected.default_unit || '—' }}</strong>
              </div>
              <div>
                <span>Kod prefiksi</span>
                <strong>{{ selected.code_prefix || '—' }}</strong>
              </div>
            </div>
          </div>

          <!-- Atributlar -->
          <div class="table-card">
            <div class="detail-head">
              <h3>Atributlar</h3>

              <button
                class="button button-gradient"
                type="button"
                @click="openAttributeCreate"
              >
                <svg><use href="#i-plus" /></svg>
                <span>Atribut qo‘shish</span>
              </button>
            </div>

            <p class="hint">
              Bu yerda ta’riflangan atributlar <strong>barcha ostki
              kategoriyalarga meros o‘tadi</strong>. Mahsulot formasi shu
              ro‘yxatga qarab quriladi.
            </p>

            <table class="data-table">
              <thead>
                <tr>
                  <th>Nomi</th>
                  <th>Kalit</th>
                  <th>Turi</th>
                  <th>Birlik</th>
                  <th>Xususiyat</th>
                  <th></th>
                </tr>
              </thead>

              <tbody>
                <tr v-if="!own.length && !inherited.length">
                  <td colspan="6" class="empty-state">Atribut ta’riflanmagan.</td>
                </tr>

                <tr v-for="definition in own" :key="definition.id">
                  <td><strong>{{ definition.name }}</strong></td>
                  <td><code>{{ definition.key }}</code></td>
                  <td>{{ definition.value_type_display }}</td>
                  <td>{{ definition.unit || '—' }}</td>

                  <td class="flags">
                    <span v-if="definition.is_required" class="pill pill-red">majburiy</span>
                    <span v-if="definition.is_variant_axis" class="pill pill-purple">
                      variant o‘qi
                    </span>
                    <span v-if="definition.uniqueness" class="pill pill-blue">unikal</span>
                  </td>

                  <td class="row-actions">
                    <button
                      class="button button-soft"
                      type="button"
                      @click="openAttributeEdit(definition)"
                    >
                      Tahrirlash
                    </button>

                    <button
                      class="button button-danger"
                      type="button"
                      @click="onDeleteAttribute(definition)"
                    >
                      <svg><use href="#i-trash" /></svg>
                    </button>
                  </td>
                </tr>

                <tr v-for="definition in inherited" :key="`i-${definition.id}`" class="dim-row">
                  <td>
                    {{ definition.name }}
                    <small class="cell-sub">
                      meros: {{ definition.category_name }}
                    </small>
                  </td>
                  <td><code>{{ definition.key }}</code></td>
                  <td>{{ definition.value_type_display }}</td>
                  <td>{{ definition.unit || '—' }}</td>
                  <td class="flags">
                    <span v-if="definition.is_required" class="pill pill-red">majburiy</span>
                  </td>
                  <td></td>
                </tr>
              </tbody>
            </table>
          </div>
        </template>
      </div>
    </div>

    <!-- Kategoriya oynasi -->
    <div class="modal" :class="{ show: categoryOpen }">
      <div class="modal-backdrop" @click="categoryOpen = false"></div>

      <div class="modal-dialog">
        <div class="modal-header">
          <div>
            <span class="modal-eyebrow">KATEGORIYA</span>
            <h3>{{ editingCategory ? 'Tahrirlash' : 'Yangi kategoriya' }}</h3>
          </div>

          <button class="modal-close" type="button" @click="categoryOpen = false">
            <svg><use href="#i-close" /></svg>
          </button>
        </div>

        <form @submit.prevent="onSaveCategory">
          <div class="modal-body">
            <div class="form-grid two">
              <div class="field full">
                <label>Nomi</label>
                <input v-model="categoryForm.name" required />
                <small v-if="categoryError('name')" class="field-error">
                  {{ categoryError('name') }}
                </small>
              </div>

              <div class="field full">
                <label>Yuqori kategoriya</label>
                <select v-model="categoryForm.parent">
                  <option :value="null">— ildiz —</option>
                  <option
                    v-for="option in store.categoryOptions"
                    :key="option.id"
                    :value="option.id"
                    :disabled="option.id === editingCategory?.id"
                  >
                    {{ option.label }}
                  </option>
                </select>
                <small v-if="categoryError('parent')" class="field-error">
                  {{ categoryError('parent') }}
                </small>
              </div>

              <div class="field">
                <label>Standart birlik</label>
                <input v-model="categoryForm.default_unit" placeholder="kg, dona" />
                <small class="field-hint">Ostki kategoriyalarga meros o‘tadi</small>
              </div>

              <div class="field">
                <label>Kod prefiksi</label>
                <input v-model="categoryForm.code_prefix" placeholder="CEM" />
              </div>

              <div class="field">
                <label>Holati</label>
                <select v-model="categoryForm.is_active">
                  <option :value="true">Faol</option>
                  <option :value="false">Faol emas</option>
                </select>
              </div>
            </div>

            <p v-if="categoryError('detail')" class="form-error">
              {{ categoryError('detail') }}
            </p>
          </div>

          <div class="modal-footer">
            <button class="button button-outline" type="button" @click="categoryOpen = false">
              Bekor qilish
            </button>

            <button class="button button-gradient" type="submit" :disabled="saving">
              {{ saving ? 'Saqlanmoqda…' : 'Saqlash' }}
            </button>
          </div>
        </form>
      </div>
    </div>

    <!-- Atribut oynasi -->
    <div class="modal" :class="{ show: attributeOpen }">
      <div class="modal-backdrop" @click="attributeOpen = false"></div>

      <div class="modal-dialog">
        <div class="modal-header">
          <div>
            <span class="modal-eyebrow">ATRIBUT</span>
            <h3>{{ editingAttribute ? 'Tahrirlash' : 'Yangi atribut' }}</h3>
            <p>{{ selected?.name }} va uning barcha ostki kategoriyalari uchun</p>
          </div>

          <button class="modal-close" type="button" @click="attributeOpen = false">
            <svg><use href="#i-close" /></svg>
          </button>
        </div>

        <form @submit.prevent="onSaveAttribute">
          <div class="modal-body">
            <div class="form-grid two">
              <div class="field">
                <label>Nomi</label>
                <input v-model="attributeForm.name" required />
                <small v-if="attributeError('name')" class="field-error">
                  {{ attributeError('name') }}
                </small>
              </div>

              <div class="field">
                <label>Kalit</label>
                <input v-model="attributeForm.key" required placeholder="qalinlik" />
                <small class="field-hint">Lotin harflari va pastki chiziq</small>
                <small v-if="attributeError('key')" class="field-error">
                  {{ attributeError('key') }}
                </small>
              </div>

              <div class="field">
                <label>Turi</label>
                <select v-model="attributeForm.value_type">
                  <option v-for="type in valueTypes" :key="type.value" :value="type.value">
                    {{ type.label }}
                  </option>
                </select>
              </div>

              <div v-if="isNumberType" class="field">
                <label>O‘lchov birligi</label>
                <input v-model="attributeForm.unit" placeholder="mm, kg" />
                <small class="field-hint">
                  Qiymat shu birlikka keltiriladi — «1 sm» va «10 mm» bir xil bo‘ladi
                </small>
                <small v-if="attributeError('unit')" class="field-error">
                  {{ attributeError('unit') }}
                </small>
              </div>

              <div v-if="isChoiceType" class="field full">
                <label>Tanlovlar</label>
                <input v-model="choicesText" placeholder="M300, M400, M500" />
                <small class="field-hint">Vergul bilan ajrating</small>
                <small v-if="attributeError('choices')" class="field-error">
                  {{ attributeError('choices') }}
                </small>
              </div>

              <div class="field">
                <label>Standart qiymat</label>
                <input v-model="attributeForm.default_value" />
              </div>

              <div class="field">
                <label>Tartib</label>
                <input v-model.number="attributeForm.position" type="number" min="0" />
              </div>

              <div class="field full">
                <label>Xususiyatlar</label>

                <div class="check-row">
                  <label class="check">
                    <input v-model="attributeForm.is_required" type="checkbox" />
                    <span>Majburiy</span>
                  </label>

                  <label class="check">
                    <input v-model="attributeForm.is_variant_axis" type="checkbox" />
                    <span>Variant o‘qi</span>
                  </label>

                  <label class="check">
                    <input
                      :checked="attributeForm.uniqueness === 1"
                      type="checkbox"
                      @change="attributeForm.uniqueness = ($event.target as HTMLInputElement).checked ? 1 : 0"
                    />
                    <span>Unikal qiymat</span>
                  </label>
                </div>

                <small class="field-hint">
                  «Variant o‘qi» — shu atribut bo‘yicha alohida variantlar hosil
                  bo‘ladi (kiyimda o‘lcham va rang).
                </small>
              </div>
            </div>

            <p v-if="attributeError('detail')" class="form-error">
              {{ attributeError('detail') }}
            </p>
          </div>

          <div class="modal-footer">
            <button class="button button-outline" type="button" @click="attributeOpen = false">
              Bekor qilish
            </button>

            <button class="button button-gradient" type="submit" :disabled="saving">
              {{ saving ? 'Saqlanmoqda…' : 'Saqlash' }}
            </button>
          </div>
        </form>
      </div>
    </div>
  </section>
</template>

<style scoped>
.split {
  display: grid;
  grid-template-columns: minmax(240px, 320px) 1fr;
  gap: 14px;
  align-items: start;
}

@media (max-width: 900px) {
  .split {
    grid-template-columns: 1fr;
  }
}

.table-card {
  padding: 18px 20px;
}

.table-card h3 {
  font-size: 10px;
}

.tree-card h3 {
  margin-bottom: 12px;
}

.tree {
  list-style: none;
}

.tree-node {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  width: 100%;
  padding: 7px 9px;
  border: 1px solid transparent;
  border-radius: var(--radius-small);
  background: none;
  color: var(--text);
  text-align: left;
  cursor: pointer;
  transition: var(--transition);
}

.tree-node:hover {
  background: var(--surface-hover);
}

.tree-node.active {
  border-color: var(--purple);
  background: var(--purple-soft);
}

.tree-name {
  font-size: 8px;
  font-weight: 600;
}

.off {
  margin-left: 5px;
  color: var(--red);
  font-size: 6px;
  font-weight: 400;
}

.tree-meta {
  display: flex;
  align-items: center;
  gap: 5px;
}

.tree-meta b {
  padding: 1px 6px;
  border-radius: 999px;
  background: var(--surface-hover);
  color: var(--text-secondary);
  font-size: 6px;
}

.unit {
  color: var(--text-muted);
  font-size: 6px;
}

.detail {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.detail-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;
}

.detail-actions {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

.path {
  margin-top: 3px;
  color: var(--text-muted);
  font-size: 7px;
  font-family: monospace;
}

.meta-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(110px, 1fr));
  gap: 12px;
}

.meta-grid span {
  display: block;
  color: var(--text-muted);
  font-size: 7px;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.meta-grid strong {
  display: block;
  margin-top: 3px;
  font-size: 11px;
}

.hint {
  margin-bottom: 12px;
  color: var(--text-secondary);
  font-size: 8px;
  line-height: 1.6;
}

.dim-row {
  background: var(--surface-soft);
  color: var(--text-secondary);
}

.cell-sub {
  display: block;
  margin-top: 2px;
  color: var(--text-muted);
  font-size: 6px;
}

code {
  padding: 1px 5px;
  border-radius: 4px;
  background: var(--surface-hover);
  font-size: 7px;
}

.flags {
  display: flex;
  gap: 4px;
  flex-wrap: wrap;
}

.pill {
  display: inline-block;
  padding: 3px 7px;
  border-radius: 999px;
  font-size: 6px;
  font-weight: 700;
  white-space: nowrap;
}

.pill-red {
  background: var(--red-soft);
  color: var(--red);
}

.pill-purple {
  background: var(--purple-soft);
  color: var(--purple);
}

.pill-blue {
  background: var(--blue-soft);
  color: var(--blue);
}

.row-actions {
  display: flex;
  gap: 6px;
  justify-content: flex-end;
}

.check-row {
  display: flex;
  gap: 14px;
  padding-top: 6px;
  flex-wrap: wrap;
}

.check {
  display: flex;
  align-items: center;
  gap: 5px;
  font-size: 8px;
  cursor: pointer;
}

.check input {
  width: auto;
  margin: 0;
}

.field-error {
  margin-top: 4px;
  color: var(--red);
  font-size: 7px;
}

.field-hint {
  margin-top: 4px;
  color: var(--text-muted);
  font-size: 7px;
  line-height: 1.5;
}

.form-error,
.load-error {
  margin: 12px 0;
  padding: 10px 12px;
  border-radius: var(--radius-small);
  background: var(--red-soft);
  color: var(--red);
  font-size: 8px;
}

.load-error {
  margin: 0 0 14px;
}
</style>
