<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'

import { catalogApi } from '@/api/catalog'
import { errorMessage } from '@/api/client'
import { inventoryApi, type Transfer } from '@/api/inventory'
import { formatDayMonth, formatTime } from '@/utils/date'
import { formatSum } from '@/utils/money'
import { shopStock, warehouseStock } from '@/utils/stock'
import type { CatalogCard, Location, Variant } from '@/types'

/**
 * Zalga chiqarish: ombordagi tovarni savdo zaliga ko'chirish.
 *
 * Kunlik ish: ertalab javonlar to'ldiriladi. Kassada bitta dona kerak
 * bo'lsa, u yerdan ham olib chiqish mumkin — bu ekran ko'p tovarni
 * bir yo'la chiqarish uchun.
 *
 * Ombordagi tovarlar darhol ro'yxatda turadi: ekran ochilgan zahoti
 * nima chiqarish mumkinligi ko'rinsin, xodim nom yozib qidirmasin.
 */

interface Chosen {
  product: number
  name: string
  variants: Variant[]
  quantities: Record<number, number>
}

const locations = ref<Location[]>([])
const transfers = ref<Transfer[]>([])
const chosen = ref<Chosen[]>([])

const search = ref('')

/** Omborda qoldig'i bor tovarlar */
const available = ref<CatalogCard[]>([])
const searching = ref(false)
const opening = ref(0)
const saving = ref(false)
const error = ref('')
const notice = ref('')

let timer: ReturnType<typeof setTimeout> | undefined

/** Kechikkan javob yangisining ustiga yozilmasin */
let request = 0

const warehouse = computed(() => locations.value.find((item) => item.kind === 'warehouse'))
const shop = computed(() => locations.value.find((item) => item.kind === 'shop'))

const units = computed(() =>
  chosen.value.reduce(
    (sum, item) => sum + Object.values(item.quantities).reduce((a, b) => a + (b || 0), 0),
    0,
  ),
)

async function load() {
  try {
    const [places, page] = await Promise.all([inventoryApi.locations(), inventoryApi.transfers()])

    locations.value = places
    transfers.value = page.results
  } catch (err) {
    error.value = errorMessage(err, 'Ma’lumotni yuklab bo‘lmadi.')
  }

  await loadAvailable()
}

/** Omborda qoldig'i bor tovarlar. Qidiruv shu ro'yxatni toraytiradi. */
async function loadAvailable() {
  const current = ++request

  searching.value = true

  try {
    const page = await catalogApi.catalog({
      location: 'warehouse',
      search: search.value.trim() || undefined,
      ordering: 'name',
    })

    if (current === request) available.value = page.results
  } catch (err) {
    if (current === request) {
      available.value = []
      error.value = errorMessage(err, 'Ombordagi tovarlarni yuklab bo‘lmadi.')
    }
  } finally {
    if (current === request) searching.value = false
  }
}

function onSearchInput() {
  clearTimeout(timer)
  timer = setTimeout(loadAvailable, 250)
}

/** Tanlangan tovarni pastdagi ro'yxatga qo'shadi. */
async function choose(card: CatalogCard) {
  notice.value = ''
  error.value = ''

  if (chosen.value.some((item) => item.product === card.id)) return

  opening.value = card.id

  try {
    const product = await catalogApi.product(card.id)

    // Savdodan chiqarilgan variant zalga chiqarilmaydi
    const variants = product.variants.filter(
      (variant) => variant.is_active && warehouseStock(variant) > 0,
    )

    if (!variants.length) {
      error.value = `«${product.name}» omborda qolmagan.`
      return
    }

    chosen.value.push({
      product: product.id,
      name: product.name,
      variants,
      quantities: {},
    })
  } catch (err) {
    error.value = errorMessage(err, 'Tovarni ochib bo‘lmadi.')
  } finally {
    opening.value = 0
  }
}

function setQuantity(item: Chosen, variant: Variant, value: string) {
  const wanted = Number.parseInt(value, 10)
  const limit = warehouseStock(variant)

  if (!value.trim() || Number.isNaN(wanted) || wanted <= 0) {
    delete item.quantities[variant.id]
    error.value = ''
    return
  }

  // Ombordagidan ortig'ini chiqarib bo'lmaydi — nega tuzatilgani aytiladi
  error.value =
    wanted > limit ? `${variant.label || item.name}: omborda ${limit} dona bor.` : ''

  item.quantities[variant.id] = Math.min(wanted, limit)
}

function remove(product: number) {
  chosen.value = chosen.value.filter((item) => item.product !== product)
  error.value = ''
}

async function moveToShop() {
  if (!units.value || saving.value) return

  if (!warehouse.value || !shop.value) {
    error.value = 'Joylar topilmadi.'
    return
  }

  saving.value = true
  error.value = ''
  notice.value = ''

  const lines = chosen.value.flatMap((item) =>
    Object.entries(item.quantities)
      .filter(([, quantity]) => quantity > 0)
      .map(([variant, quantity]) => ({ variant: Number(variant), quantity })),
  )

  try {
    const transfer = await inventoryApi.transfer({
      source: warehouse.value.id,
      target: shop.value.id,
      lines,
    })

    notice.value = `${transfer.number}: ${units.value} dona zalga chiqarildi.`
    chosen.value = []

    await load()
  } catch (err) {
    error.value = errorMessage(err, 'Zalga chiqarib bo‘lmadi.')
  } finally {
    saving.value = false
  }
}

onMounted(load)
</script>

<template>
  <section class="app-section active">
    <p v-if="error" class="load-error" role="alert">{{ error }}</p>
    <p v-if="notice" class="notice">{{ notice }}</p>

    <div class="table-card card-padded stage">
      <h3 class="card-title">Ombordagi tovarlar</h3>
      <p class="card-hint">Zalga chiqariladiganini bosing.</p>

      <div class="search-field">
        <svg aria-hidden="true"><use href="#i-search" /></svg>

        <input
          v-model="search"
          type="text"
          autocomplete="off"
          placeholder="Ro‘yxatni toraytirish uchun nom yozing"
          aria-label="Tovar nomi"
          @input="onSearchInput"
        />

        <span v-if="searching" class="search-state">Qidirilmoqda…</span>
      </div>

      <!-- Ombordagi tovarlar: bosilgani pastdagi ro'yxatga tushadi -->
      <ul v-if="available.length" class="available" aria-label="Ombordagi tovarlar">
        <li v-for="card in available" :key="card.id">
          <button
            type="button"
            :disabled="opening === card.id || chosen.some((item) => item.product === card.id)"
            @click="choose(card)"
          >
            <img v-if="card.primary_image" :src="card.primary_image.thumb" alt="" />
            <span v-else class="no-image"><svg><use href="#i-image" /></svg></span>

            <span class="card-text">
              <strong>{{ card.name }}</strong>
              <small>{{ card.category_name }} · {{ formatSum(card.sale_price) }}</small>
              <small class="stock">Omborda {{ card.warehouse_stock }} · zalda {{ card.shop_stock }}</small>
            </span>
          </button>
        </li>
      </ul>

      <div v-else-if="!searching" class="empty-state">
        {{ search.trim() ? 'Bunday nomli tovar omborda yo‘q.' : 'Omborda tovar qolmagan.' }}
      </div>

      <div v-for="item in chosen" :key="item.product" class="model" data-testid="transfer-model">
        <div class="model-head">
          <strong>{{ item.name }}</strong>

          <button
            class="icon-button delete"
            type="button"
            :aria-label="`${item.name}: ro‘yxatdan olib tashlash`"
            @click="remove(item.product)"
          >
            <svg><use href="#i-trash" /></svg>
          </button>
        </div>

        <table class="data-table">
          <thead>
            <tr>
              <th>Variant</th>
              <th class="num">Omborda</th>
              <th class="num">Zalda</th>
              <th class="num">Chiqariladi</th>
            </tr>
          </thead>

          <tbody>
            <tr v-for="variant in item.variants" :key="variant.id">
              <td>{{ variant.label || item.name }}</td>
              <td class="num">{{ warehouseStock(variant) }}</td>
              <td class="num">{{ shopStock(variant) }}</td>

              <td class="num">
                <input
                  class="quantity"
                  type="number"
                  min="0"
                  :max="warehouseStock(variant)"
                  :aria-label="`${variant.label || item.name}: nechta chiqariladi`"
                  :value="item.quantities[variant.id] || ''"
                  @input="setQuantity(item, variant, ($event.target as HTMLInputElement).value)"
                />
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <div v-if="chosen.length" class="stage-foot">
        <strong>Jami: {{ units }} dona</strong>

        <button
          class="button button-gradient big"
          type="button"
          :disabled="!units || saving"
          @click="moveToShop"
        >
          {{ saving ? 'Chiqarilmoqda…' : 'Zalga chiqarish' }}
        </button>
      </div>
    </div>

    <div class="table-card card-padded">
      <h3 class="card-title">Oxirgi chiqarilganlar</h3>

      <div class="table-scroll">
        <table class="data-table">
          <thead>
            <tr>
              <th>Hujjat</th>
              <th>Sana</th>
              <th>Xodim</th>
              <th>Tovar</th>
              <th class="num">Dona</th>
            </tr>
          </thead>

          <tbody>
            <tr v-if="!transfers.length">
              <td colspan="5" class="empty-state">Hali chiqarilmagan.</td>
            </tr>

            <tr v-for="transfer in transfers" v-else :key="transfer.id">
              <td>
                <strong>{{ transfer.number }}</strong>
                <small class="cell-sub">{{ transfer.source_name }} → {{ transfer.target_name }}</small>
              </td>

              <td>
                {{ formatDayMonth(transfer.date) }}
                <small class="cell-sub">{{ formatTime(transfer.created_at) }}</small>
              </td>

              <td>{{ transfer.created_by_name || '—' }}</td>

              <td>
                {{ transfer.lines[0]?.product_name }}
                <small v-if="transfer.lines.length > 1" class="cell-sub">
                  va yana {{ transfer.lines.length - 1 }} ta
                </small>
              </td>

              <td class="num">
                {{ transfer.lines.reduce((sum, line) => sum + line.quantity, 0) }}
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </section>
</template>

<style scoped>
.stage {
  margin-bottom: 12px;
}

.card-title {
  margin-bottom: 4px;
  font-family: var(--font-display);
  font-size: 23px;
  font-weight: 500;
}

/* Ko'rinishi `app.css` dagi umumiy `.search-field` dan; bu yerda
   faqat kengligi — ekranning boshlanish maydoni kengroq bo'lsin */
.card-hint {
  margin-bottom: 12px;
  color: var(--text-muted);
  font-size: 14px;
}

.search-field {
  width: 100%;
  max-width: 620px;
  margin-bottom: 14px;
  padding-right: 12px;
}

.search-state {
  flex: none;
  color: var(--text-muted);
  font-size: 13px;
}

/* Ombordagi tovarlar ro'yxati */
.available {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: 8px;
  margin: 0 0 14px;
  padding: 0;
  list-style: none;
}

.available button {
  display: flex;
  gap: 10px;
  width: 100%;
  padding: 8px;
  border: 1px solid var(--border);
  border-radius: var(--radius-card);
  background: var(--surface);
  text-align: left;
  cursor: pointer;
}

.available button:hover:not(:disabled) {
  border-color: var(--accent);
  background: var(--accent-soft);
}

.available button:disabled {
  opacity: 0.5;
  cursor: default;
}

.available img,
.available .no-image {
  flex: none;
  width: 48px;
  height: 60px;
  border-radius: var(--radius);
  object-fit: cover;
}

.available .no-image {
  display: grid;
  place-items: center;
  background: var(--surface-soft);
}

.available .no-image svg {
  width: 20px;
  height: 20px;
  fill: none;
  stroke: var(--text-muted);
  stroke-width: 1.6;
}

.card-text {
  display: flex;
  min-width: 0;
  flex-direction: column;
  gap: 2px;
}

.card-text strong {
  font-size: 15px;
}

.card-text small {
  color: var(--text-muted);
  font-size: 12px;
}

.card-text .stock {
  color: var(--accent);
  font-variant-numeric: tabular-nums;
}

.model {
  margin-bottom: 12px;
  padding: 12px 14px;
  border: 1px solid var(--border);
  border-radius: var(--radius-card);
  background: var(--surface-soft);
}

.model-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}

.model-head strong {
  font-size: 16px;
}

.quantity {
  width: 80px;
  text-align: right;
}

.stage-foot {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 12px;
  padding-top: 14px;
  border-top: 1px solid var(--border);
}

.stage-foot strong {
  font-size: 19px;
  font-variant-numeric: tabular-nums;
}

.stage-foot .button {
  margin-left: auto;
}

.big {
  min-height: 48px;
  padding: 0 24px;
  font-size: 16px;
}
</style>
