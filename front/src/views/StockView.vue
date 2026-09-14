<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'

import { stockApi } from '@/api/stock'
import { useExport } from '@/composables/useExport'
import { useAuthStore } from '@/stores/auth'
import { useCatalogStore } from '@/stores/catalog'
import { useStockStore } from '@/stores/stock'
import { useWarehouseStore } from '@/stores/warehouses'
import type { StockBalance } from '@/types'

const store = useStockStore()
const warehouses = useWarehouseStore()
const catalog = useCatalogStore()
const auth = useAuthStore()

/** Tannarx kirim narxidan hisoblanadi — `view_purchase_price` ruxsati bilan */
const canSeeCost = computed(() => auth.can('view_purchase_price'))

// Ekrandagi filtrlar bilan bir xil kesim yuklab olinadi
const { exporting, exportError, onExport } = useExport(() =>
  stockApi.exportBalances(store.filters),
)

// Jurnal — qoldiq qanday shakllangani. Buxgalter qoldiqni tekshirganda
// «bu son qayerdan chiqdi?» degan savolga javob shu faylda bo'ladi.
const journal = useExport(() =>
  stockApi.exportMovements({ warehouse: store.filters.warehouse }),
)

const adjustOpen = ref(false)
const target = ref<StockBalance | null>(null)
const formErrors = ref<Record<string, string[]>>({})

const adjustForm = reactive({
  mode: 'adjust' as 'adjust' | 'stocktake',
  quantity: '',
  reason: 'manual_add',
  note: '',
})

onMounted(async () => {
  await Promise.all([
    store.load(),
    store.loadReasons(),
    warehouses.load(),
    catalog.loadCategories(),
  ])
})

let searchTimer: ReturnType<typeof setTimeout> | undefined

function onSearchInput() {
  clearTimeout(searchTimer)
  searchTimer = setTimeout(() => store.load(), 300)
}

function openAdjust(row: StockBalance, mode: 'adjust' | 'stocktake') {
  target.value = row
  formErrors.value = {}

  adjustForm.mode = mode
  adjustForm.quantity = mode === 'stocktake' ? row.quantity : ''
  adjustForm.reason = 'manual_add'
  adjustForm.note = ''

  adjustOpen.value = true
}

async function onSubmitAdjust() {
  if (!target.value) return

  formErrors.value = {}

  const base = {
    variant: target.value.variant,
    warehouse: target.value.warehouse,
    batch: target.value.batch,
    note: adjustForm.note,
  }

  const result =
    adjustForm.mode === 'stocktake'
      ? await store.stocktake({ ...base, counted_quantity: adjustForm.quantity })
      : await store.adjust({
          ...base,
          quantity: adjustForm.quantity,
          reason: adjustForm.reason,
        })

  if (result.ok) {
    adjustOpen.value = false
    return
  }

  formErrors.value = result.errors
}

function number(value: string | null | undefined): string {
  if (value == null) return '—'
  return new Intl.NumberFormat('uz-UZ', { maximumFractionDigits: 3 }).format(Number(value))
}

function money(value: string | null | undefined): string {
  if (value == null) return '—'
  return `${new Intl.NumberFormat('uz-UZ', { maximumFractionDigits: 0 }).format(Number(value))} so'm`
}

/** Qatorning holati — dizayndagi rangli belgi. */
function rowState(row: StockBalance): { label: string; tone: string } | null {
  if (row.is_expired) return { label: 'Muddati o‘tgan', tone: 'red' }
  if (!row.is_sellable) return { label: 'Sotuvga chiqmaydi', tone: 'orange' }
  if (row.is_low) return { label: 'Kam qoldi', tone: 'yellow' }
  if (Number(row.reserved_quantity) > 0) return { label: 'Qisman band', tone: 'blue' }
  return null
}

const formError = (field: string) => formErrors.value[field]?.[0] ?? ''
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
            placeholder="Mahsulot, SKU yoki partiya..."
            @input="onSearchInput"
          />
        </div>

        <select v-model="store.filters.warehouse" @change="store.load()">
          <option value="">Barcha omborlar</option>
          <option v-for="w in warehouses.items" :key="w.id" :value="w.id">
            {{ w.name }}
          </option>
        </select>

        <select v-model="store.filters.category" @change="store.load()">
          <option value="">Barcha kategoriyalar</option>
          <option v-for="c in catalog.categoryOptions" :key="c.id" :value="c.id">
            {{ c.label }}
          </option>
        </select>

        <select v-model="store.filters.status" @change="store.load()">
          <option value="">Barcha holatlar</option>
          <option value="low">Kam qolganlar</option>
          <option value="expired">Muddati o‘tganlar</option>
          <option value="reserved">Band qilinganlar</option>
          <option value="sellable">Sotuvga tayyor</option>
        </select>
      </div>

      <div class="toolbar-actions">
        <button
          class="button button-outline"
          type="button"
          :disabled="journal.exporting.value"
          @click="journal.onExport"
        >
          <svg><use href="#i-download" /></svg>
          <span>{{ journal.exporting.value ? 'Tayyorlanmoqda…' : 'Jurnal' }}</span>
        </button>

        <button
          class="button button-outline"
          type="button"
          :disabled="exporting"
          @click="onExport"
        >
          <svg><use href="#i-download" /></svg>
          <span>{{ exporting ? 'Tayyorlanmoqda…' : 'Qoldiqlar' }}</span>
        </button>
      </div>
    </div>

    <p v-if="exportError" class="load-error">{{ exportError }}</p>
    <p v-if="journal.exportError.value" class="load-error">
      {{ journal.exportError.value }}
    </p>

    <p v-if="store.error" class="load-error">{{ store.error }}</p>

    <!-- Jamlanma kartalari -->
    <div class="stock-totals">
      <div>
        <span>Pozitsiyalar</span>
        <strong>{{ store.summary?.positions ?? 0 }}</strong>
      </div>

      <div>
        <span>Umumiy miqdor</span>
        <strong>{{ number(store.summary?.units) }}</strong>
      </div>

      <div>
        <span>Band qilingan</span>
        <strong>{{ number(store.summary?.reserved) }}</strong>
      </div>

      <div v-if="canSeeCost" class="accent">
        <span>Tannarx (FIFO)</span>
        <strong>{{ money(store.summary?.cost_value) }}</strong>
      </div>

      <div>
        <span>Chakana qiymati</span>
        <strong>{{ money(store.summary?.retail_value) }}</strong>
      </div>

      <div :class="{ warn: (store.summary?.low_count ?? 0) > 0 }">
        <span>Kam qolgan</span>
        <strong>{{ store.summary?.low_count ?? 0 }}</strong>
      </div>

      <div :class="{ danger: (store.summary?.expired_count ?? 0) > 0 }">
        <span>Muddati o‘tgan</span>
        <strong>{{ store.summary?.expired_count ?? 0 }}</strong>
      </div>
    </div>

    <div class="table-card">
      <div class="table-scroll">
        <table class="data-table">
          <thead>
            <tr>
              <th>Mahsulot</th>
              <th>Ombor</th>
              <th>Partiya</th>
              <th>Muddati</th>
              <th class="num">Qoldiq</th>
              <th class="num">Band</th>
              <th class="num">Mavjud</th>
              <th v-if="canSeeCost" class="num">Tannarx</th>
              <th>Holat</th>
              <th></th>
            </tr>
          </thead>

          <tbody>
            <tr v-if="store.loading">
              <td :colspan="canSeeCost ? 10 : 9" class="empty-state">Yuklanmoqda…</td>
            </tr>

            <tr v-else-if="store.isEmpty">
              <td :colspan="canSeeCost ? 10 : 9" class="empty-state">
                Qoldiq topilmadi. Kirim qilinganidan keyin bu yerda paydo bo‘ladi.
              </td>
            </tr>

            <tr v-for="row in store.items" v-else :key="row.id">
              <td>
                <strong>{{ row.product_name }}</strong>
                <small class="cell-sub">
                  {{ row.sku }}
                  <template v-if="row.variant_name"> · {{ row.variant_name }}</template>
                </small>
              </td>

              <td>{{ row.warehouse_name }}</td>
              <td>{{ row.batch_code || '—' }}</td>

              <td>
                <span v-if="row.expiry_date" :class="{ 'expiry-bad': row.is_expired }">
                  {{ row.expiry_date }}
                </span>
                <span v-else>—</span>
              </td>

              <td class="num">{{ number(row.quantity) }} {{ row.unit }}</td>

              <td class="num">
                <span :class="{ muted: Number(row.reserved_quantity) === 0 }">
                  {{ number(row.reserved_quantity) }}
                </span>
              </td>

              <td class="num">
                <strong>{{ number(row.available_quantity) }}</strong>
              </td>

              <td v-if="canSeeCost" class="num">
                <span v-if="Number(row.cost_value) > 0">
                  {{ money(row.cost_value) }}
                  <small class="cell-sub">{{ money(row.avg_unit_cost) }} / {{ row.unit }}</small>
                </span>
                <span v-else class="muted" title="Tannarxsiz kiritilgan tovar">—</span>
              </td>

              <td>
                <span
                  v-if="rowState(row)"
                  class="pill"
                  :class="`pill-${rowState(row)!.tone}`"
                >
                  {{ rowState(row)!.label }}
                </span>
                <span v-else class="pill pill-green">Sotuvga tayyor</span>
              </td>

              <td class="row-actions">
                <button class="button button-soft" type="button" @click="openAdjust(row, 'adjust')">
                  Tuzatish
                </button>

                <button
                  class="button button-outline"
                  type="button"
                  @click="openAdjust(row, 'stocktake')"
                >
                  Sanash
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Tuzatish / inventarizatsiya oynasi -->
    <div class="modal" :class="{ show: adjustOpen }">
      <div class="modal-backdrop" @click="adjustOpen = false"></div>

      <div class="modal-dialog">
        <div class="modal-header">
          <div>
            <span class="modal-eyebrow">QOLDIQ</span>
            <h3>
              {{ adjustForm.mode === 'stocktake' ? 'Inventarizatsiya' : 'Qoldiqni tuzatish' }}
            </h3>
            <p v-if="target">{{ target.product_name }} — {{ target.warehouse_name }}</p>
          </div>

          <button class="modal-close" type="button" @click="adjustOpen = false">
            <svg><use href="#i-close" /></svg>
          </button>
        </div>

        <form @submit.prevent="onSubmitAdjust">
          <div class="modal-body">
            <p class="hint">
              <template v-if="adjustForm.mode === 'stocktake'">
                Sanab chiqilgan miqdorni kiriting. Farq «Inventarizatsiya farqi»
                sababi bilan jurnalga yoziladi va hisobotda yo‘qotish sifatida
                ko‘rinadi.
              </template>
              <template v-else>
                Qoldiq to‘g‘ridan-to‘g‘ri o‘zgartirilmaydi — jurnalga yangi
                yozuv qo‘shiladi. Chiqim uchun miqdorni manfiy kiriting.
              </template>
            </p>

            <div class="form-grid two">
              <div class="field">
                <label>
                  {{ adjustForm.mode === 'stocktake' ? 'Sanalgan miqdor' : 'Miqdor' }}
                </label>
                <input v-model="adjustForm.quantity" type="number" step="0.001" required />
              </div>

              <div v-if="adjustForm.mode === 'adjust'" class="field">
                <label>Sababi</label>
                <select v-model="adjustForm.reason">
                  <option
                    v-for="reason in store.reasons"
                    :key="reason.value"
                    :value="reason.value"
                  >
                    {{ reason.label }}
                  </option>
                </select>
              </div>

              <div class="field full">
                <label>Izoh</label>
                <input v-model="adjustForm.note" />
              </div>
            </div>

            <p v-if="formError('detail')" class="form-error">{{ formError('detail') }}</p>
          </div>

          <div class="modal-footer">
            <button class="button button-outline" type="button" @click="adjustOpen = false">
              Bekor qilish
            </button>

            <button class="button button-gradient" type="submit" :disabled="store.saving">
              {{ store.saving ? 'Saqlanmoqda…' : 'Saqlash' }}
            </button>
          </div>
        </form>
      </div>
    </div>
  </section>
</template>

<style scoped>
.stock-totals {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(130px, 1fr));
  gap: 12px;
  margin-bottom: 12px;
  padding: 16px;
  border: 1px solid var(--border);
  border-radius: var(--radius);
  background: var(--surface);
}

/* Yorliq va son KPI kartalaridagi kabi: katta harf yo'q,
   son tabular shaklda. */
.stock-totals span {
  display: block;
  color: var(--text-secondary);
  font-size: 13px;
}

.stock-totals strong {
  display: block;
  margin-top: 6px;
  font-size: 18px;
  font-weight: 600;
  font-variant-numeric: tabular-nums;
}

.stock-totals .accent strong {
  color: var(--accent);
}

.stock-totals .warn strong {
  color: var(--yellow);
}

.stock-totals .danger strong {
  color: var(--red);
}

.expiry-bad {
  color: var(--red);
  font-weight: 700;
}

</style>
