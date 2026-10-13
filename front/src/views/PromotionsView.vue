<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'

import { catalogApi, promotionsApi, type PromotionInput } from '@/api/catalog'
import { errorMessage } from '@/api/client'
import AmountField from '@/components/AmountField.vue'
import { useToastStore } from '@/stores/toast'
import { daysAgoIso, formatDate, todayIso } from '@/utils/date'
import { formatPercent } from '@/utils/money'
import type { Category, Product, Promotion, PromotionStatus } from '@/types'

/**
 * Aksiyalar: tanlangan tovarlar yoki butun kategoriya muddat davomida arzon.
 *
 * Narx o'zgarmaydi — aksiya uning ustidan chegirma bo'lib qo'llanadi.
 * Muddat tugaganda tovar o'z narxiga o'zi qaytadi. Kassa aksiyani
 * skanerlashda o'zi qo'yadi, kassir chegarasi unga ta'sir qilmaydi.
 */

const toast = useToastStore()

const items = ref<Promotion[]>([])
const categories = ref<Category[]>([])
const loading = ref(true)
const saving = ref(false)
const error = ref('')

/** Tahrirlanayotgan aksiya; `null` — yangisi */
const editing = ref<Promotion | null>(null)

function emptyForm(): PromotionInput {
  return {
    name: '',
    percent: '',
    starts_on: todayIso(),
    ends_on: daysAgoIso(-7),
    products: [],
    categories: [],
  }
}

const form = ref<PromotionInput>(emptyForm())

/** Tanlangan tovarlarning nomlari — shaklda ko'rinsin */
const chosenProducts = ref<{ id: number; name: string }[]>([])

const STATUS: Record<PromotionStatus, { label: string; pill: string }> = {
  running: { label: 'Amalda', pill: 'pill-green' },
  upcoming: { label: 'Boshlanmagan', pill: 'pill-grey' },
  ended: { label: 'Tugagan', pill: 'pill-grey' },
  stopped: { label: 'To‘xtatilgan', pill: 'pill-red' },
}

async function load() {
  loading.value = true
  error.value = ''

  try {
    const [list, cats] = await Promise.all([promotionsApi.list(), catalogApi.categories()])

    items.value = list
    categories.value = cats
  } catch (err) {
    error.value = errorMessage(err, 'Aksiyalarni yuklab bo‘lmadi.')
  } finally {
    loading.value = false
  }
}

// --- Tovar qidirish ----------------------------------------------------------

const search = ref('')
const found = ref<Product[]>([])
let searchTimer: ReturnType<typeof setTimeout> | undefined

watch(search, (value) => {
  clearTimeout(searchTimer)

  if (value.trim().length < 2) {
    found.value = []
    return
  }

  searchTimer = setTimeout(async () => {
    try {
      found.value = (await catalogApi.products({ search: value.trim() })).results
    } catch {
      found.value = []
    }
  }, 250)
})

function addProduct(product: Product) {
  if (!form.value.products.includes(product.id)) {
    form.value.products.push(product.id)
    chosenProducts.value.push({ id: product.id, name: product.name })
  }

  search.value = ''
}

function removeProduct(id: number) {
  form.value.products = form.value.products.filter((item) => item !== id)
  chosenProducts.value = chosenProducts.value.filter((item) => item.id !== id)
}

// --- Saqlash -----------------------------------------------------------------

const canSave = computed(
  () =>
    form.value.name.trim() !== '' &&
    Number(form.value.percent) > 0 &&
    (form.value.products.length > 0 || form.value.categories.length > 0),
)

function startNew() {
  editing.value = null
  form.value = emptyForm()
  chosenProducts.value = []
}

function startEdit(promo: Promotion) {
  editing.value = promo
  form.value = {
    name: promo.name,
    percent: formatPercent(promo.percent),
    starts_on: promo.starts_on,
    ends_on: promo.ends_on,
    products: [...promo.products],
    categories: [...promo.categories],
  }
  chosenProducts.value = promo.products.map((id, index) => ({
    id,
    name: promo.product_names[index] ?? `#${id}`,
  }))
}

async function onSave() {
  if (!canSave.value) return

  saving.value = true

  try {
    const payload = { ...form.value, name: form.value.name.trim() }

    if (editing.value) {
      await promotionsApi.update(editing.value.id, payload)
      toast.show('Aksiya saqlandi')
    } else {
      await promotionsApi.create(payload)
      toast.show('Aksiya yaratildi')
    }

    startNew()
    await load()
  } catch (err) {
    toast.show(errorMessage(err, 'Saqlab bo‘lmadi.'), 'error')
  } finally {
    saving.value = false
  }
}

async function onStop(promo: Promotion) {
  if (!window.confirm(`«${promo.name}» to‘xtatilsinmi? Tovarlar darhol o‘z narxiga qaytadi.`)) {
    return
  }

  try {
    await promotionsApi.stop(promo.id)
    toast.show('Aksiya to‘xtatildi')

    if (editing.value?.id === promo.id) startNew()

    await load()
  } catch (err) {
    toast.show(errorMessage(err, 'To‘xtatib bo‘lmadi.'), 'error')
  }
}

/** Nimaga tegishli: «Kurtkalar, Ko'ylaklar + 3 ta tovar» */
function target(promo: Promotion): string {
  const parts = [...promo.category_names]

  if (promo.product_names.length === 1) parts.push(promo.product_names[0]!)
  else if (promo.product_names.length > 1) parts.push(`${promo.product_names.length} ta tovar`)

  return parts.join(', ')
}

onMounted(load)
</script>

<template>
  <section class="app-section active">
    <p v-if="error" class="load-error">{{ error }}</p>

    <div class="promotions">
      <div class="table-card">
        <div class="table-scroll">
          <table class="data-table">
            <thead>
              <tr>
                <th>Aksiya</th>
                <th class="num">Chegirma</th>
                <th>Muddati</th>
                <th>Nimaga</th>
                <th>Holati</th>
                <th></th>
              </tr>
            </thead>

            <tbody>
              <tr v-if="loading">
                <td colspan="6" class="empty-state">Yuklanmoqda…</td>
              </tr>

              <tr v-else-if="!items.length">
                <td colspan="6" class="empty-state">
                  Aksiya yo‘q. O‘ng tomonda birinchisini yarating.
                </td>
              </tr>

              <tr
                v-for="promo in items"
                v-else
                :key="promo.id"
                :class="{ chosen: editing?.id === promo.id }"
              >
                <td class="promo-name">
                  <strong>{{ promo.name }}</strong>
                </td>
                <td class="num">−{{ formatPercent(promo.percent) }} %</td>
                <td>{{ formatDate(promo.starts_on) }} — {{ formatDate(promo.ends_on) }}</td>
                <td class="target">{{ target(promo) }}</td>
                <td>
                  <span class="pill" :class="STATUS[promo.status].pill">
                    {{ STATUS[promo.status].label }}
                  </span>
                </td>
                <td class="num row-actions">
                  <button
                    v-if="promo.status !== 'stopped' && promo.status !== 'ended'"
                    class="button button-outline"
                    type="button"
                    @click="startEdit(promo)"
                  >
                    Tahrirlash
                  </button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <aside class="table-card card-padded">
        <h3>{{ editing ? 'Aksiyani tahrirlash' : 'Yangi aksiya' }}</h3>

        <div class="field">
          <label for="promo-name">Nomi</label>
          <input id="promo-name" v-model="form.name" type="text" placeholder="Kuzgi aksiya" />
        </div>

        <div class="field">
          <label for="promo-percent">Chegirma</label>
          <AmountField
            id="promo-percent"
            v-model="form.percent"
            suffix="%"
            :grouped="false"
            placeholder="30"
          />
        </div>

        <div class="dates">
          <div class="field">
            <label for="promo-start">Boshlanadi</label>
            <input id="promo-start" v-model="form.starts_on" type="date" />
          </div>

          <div class="field">
            <label for="promo-end">Tugaydi</label>
            <input id="promo-end" v-model="form.ends_on" type="date" />
          </div>
        </div>

        <small class="field-hint">Ikkala kun ham kiradi. Tugagach narx o‘zi qaytadi.</small>

        <div class="field">
          <label>Butun kategoriya</label>

          <div class="checks">
            <label v-for="category in categories" :key="category.id" class="check">
              <input v-model="form.categories" type="checkbox" :value="category.id" />
              {{ category.name }}
            </label>
          </div>
        </div>

        <div class="field">
          <label for="promo-search">Yoki alohida tovarlar</label>
          <input
            id="promo-search"
            v-model="search"
            type="search"
            placeholder="Tovar nomini yozing…"
            autocomplete="off"
          />

          <ul v-if="found.length" class="found">
            <li v-for="product in found" :key="product.id">
              <button type="button" @click="addProduct(product)">{{ product.name }}</button>
            </li>
          </ul>

          <ul v-if="chosenProducts.length" class="chosen-products">
            <li v-for="product in chosenProducts" :key="product.id">
              <span>{{ product.name }}</span>
              <button
                class="icon-button delete"
                type="button"
                :aria-label="`${product.name}: olib tashlash`"
                @click="removeProduct(product.id)"
              >
                <svg><use href="#i-close" /></svg>
              </button>
            </li>
          </ul>
        </div>

        <div class="form-actions">
          <button
            class="button button-gradient"
            type="button"
            :disabled="saving || !canSave"
            @click="onSave"
          >
            {{ saving ? 'Saqlanmoqda…' : editing ? 'Saqlash' : 'Aksiyani boshlash' }}
          </button>

          <button v-if="editing" class="button button-outline" type="button" @click="startNew">
            Bekor qilish
          </button>
        </div>

        <!-- Muddatidan oldin tugatish: tovarlar darhol o'z narxiga qaytadi -->
        <button
          v-if="editing"
          class="button button-outline stop"
          type="button"
          @click="onStop(editing)"
        >
          Aksiyani to‘xtatish
        </button>
      </aside>
    </div>
  </section>
</template>

<style scoped>
.promotions {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 340px;
  align-items: start;
  gap: 12px;
}

@media (max-width: 1000px) {
  .promotions {
    grid-template-columns: 1fr;
  }
}

/* Uzun nom jadvalni yon tomonga surmasin — qatorga bo'linadi */
.promo-name,
.target {
  white-space: normal;
}

.promo-name {
  min-width: 120px;
}

.target {
  max-width: 260px;
  color: var(--text-secondary);
}

tr.chosen td {
  background: var(--accent-soft);
}

.row-actions .button {
  margin-left: 6px;
}

.dates {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
}

.checks {
  display: flex;
  flex-wrap: wrap;
  gap: 6px 14px;
}

/* Maydon uslubi (40 px balandlik, to'liq en) belgilash katagiga tegmasin */
.checks input {
  width: auto;
  height: auto;
  min-height: 0;
  margin: 0;
}

.checks .check {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  margin: 0;
  font-weight: 400;
}

.dates + .field-hint {
  display: block;
  margin-bottom: 12px;
}

.stop {
  width: 100%;
  margin-top: 8px;
  color: var(--red);
}

.found,
.chosen-products {
  margin: 6px 0 0;
  padding: 0;
  list-style: none;
}

.found {
  border: 1px solid var(--border);
  border-radius: var(--radius);
  max-height: 200px;
  overflow-y: auto;
}

.found button {
  width: 100%;
  padding: 7px 10px;
  text-align: left;
  background: transparent;
  cursor: pointer;
}

.found button:hover {
  background: var(--accent-soft);
}

.chosen-products li {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 2px 0 2px 10px;
  border-bottom: 1px solid var(--border);
}

.form-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 12px;
}
</style>
