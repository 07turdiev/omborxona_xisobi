<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'

import { reportsApi, type ReportPeriod } from '@/api/reports'
import { useExport } from '@/composables/useExport'
import { useAuthStore } from '@/stores/auth'
import { useWarehouseStore } from '@/stores/warehouses'
import type { ReportBundle } from '@/types'

const warehouses = useWarehouseStore()
const auth = useAuthStore()

// Server ruxsatsiz javobda bu qiymatlarni `null` qiladi; bu yerda faqat
// bo'sh kartalar va "—" ustunlar ko'rinmasin
const canSeeProfit = computed(() => auth.can('view_profit'))
const canSeePurchase = computed(() => auth.can('view_purchase_price'))

const data = ref<ReportBundle | null>(null)
const loading = ref(false)
const error = ref('')

const period = ref<ReportPeriod>({ date_from: '', date_to: '', warehouse: '' })

/** Tez tanlash tugmalari — dizayndagi davr presetlari. */
const presets = [
  { label: 'Bugun', days: 0 },
  { label: '7 kun', days: 7 },
  { label: '30 kun', days: 30 },
  { label: '90 kun', days: 90 },
  { label: 'Butun davr', days: null },
]

const activePreset = ref<string>('30 kun')

// Ekrandagi davr bilan bir xil — raqamlar mos kelishi kerak
const { exporting, exportError, onExport } = useExport(() =>
  reportsApi.exportExcel(period.value),
)

function iso(date: Date): string {
  return date.toISOString().slice(0, 10)
}

function applyPreset(preset: (typeof presets)[number]) {
  activePreset.value = preset.label

  if (preset.days === null) {
    period.value.date_from = ''
    period.value.date_to = ''
  } else {
    const to = new Date()
    const from = new Date()
    from.setDate(from.getDate() - preset.days)

    period.value.date_from = iso(from)
    period.value.date_to = iso(to)
  }

  load()
}

async function load() {
  loading.value = true
  error.value = ''

  try {
    data.value = await reportsApi.bundle(period.value)
  } catch {
    error.value = 'Hisobotni olishda xatolik.'
  } finally {
    loading.value = false
  }
}

onMounted(async () => {
  await warehouses.load()
  applyPreset(presets[2]!)
})

function money(value: string | null | undefined): string {
  if (value == null) return '—'
  return new Intl.NumberFormat('uz-UZ', { maximumFractionDigits: 0 }).format(Number(value))
}

function number(value: string | null | undefined): string {
  if (value == null) return '—'
  return new Intl.NumberFormat('uz-UZ', { maximumFractionDigits: 3 }).format(Number(value))
}

/** Diagramma ustuni balandligi — eng katta qiymatga nisbatan. */
const categoryMax = computed(() =>
  Math.max(1, ...(data.value?.by_category ?? []).map((row) => Number(row.revenue))),
)

const dailyMax = computed(() =>
  Math.max(1, ...(data.value?.daily_sales ?? []).map((row) => Number(row.revenue))),
)

function onPrint() {
  window.print()
}
</script>

<template>
  <section class="app-section active">
    <div class="section-toolbar">
      <div class="filters">
        <div class="period-buttons">
          <button
            v-for="preset in presets"
            :key="preset.label"
            class="period-button"
            :class="{ active: activePreset === preset.label }"
            type="button"
            @click="applyPreset(preset)"
          >
            {{ preset.label }}
          </button>
        </div>

        <input
          v-model="period.date_from"
          type="date"
          @change="activePreset = ''; load()"
        />
        <input
          v-model="period.date_to"
          type="date"
          @change="activePreset = ''; load()"
        />

        <select v-model="period.warehouse" @change="load()">
          <option value="">Barcha omborlar</option>
          <option v-for="w in warehouses.items" :key="w.id" :value="w.id">
            {{ w.name }}
          </option>
        </select>
      </div>

      <div class="toolbar-actions no-print">
        <button
          class="button button-outline"
          type="button"
          :disabled="exporting"
          @click="onExport"
        >
          <svg><use href="#i-download" /></svg>
          <span>{{ exporting ? 'Tayyorlanmoqda…' : 'Excel' }}</span>
        </button>

        <button class="button button-outline" type="button" @click="onPrint">
          <svg><use href="#i-print" /></svg>
          <span>Chop etish</span>
        </button>
      </div>
    </div>

    <p v-if="error" class="load-error">{{ error }}</p>
    <p v-if="exportError" class="load-error no-print">{{ exportError }}</p>
    <p v-if="loading" class="empty-state">Yuklanmoqda…</p>

    <template v-if="data && !loading">
      <!-- Asosiy ko'rsatkichlar -->
      <div class="kpi-grid">
        <article v-if="canSeePurchase" class="kpi-card kpi-blue">
          <div class="kpi-icon"><svg><use href="#i-import" /></svg></div>
          <p>Xarid</p>
          <strong>{{ money(data.summary.purchase_amount) }}</strong>
          <small>{{ data.summary.purchase_count }} hujjat</small>
        </article>

        <article class="kpi-card kpi-purple">
          <div class="kpi-icon"><svg><use href="#i-sale" /></svg></div>
          <p>Tushum</p>
          <strong>{{ money(data.summary.revenue) }}</strong>
          <small>{{ data.summary.sale_count }} sotuv</small>
        </article>

        <article v-if="canSeeProfit" class="kpi-card kpi-orange">
          <div class="kpi-icon"><svg><use href="#i-stock" /></svg></div>
          <p>Tannarx (FIFO)</p>
          <strong>{{ money(data.summary.cost) }}</strong>
        </article>

        <article v-if="canSeeProfit" class="kpi-card kpi-green">
          <div class="kpi-icon"><svg><use href="#i-report" /></svg></div>
          <p>Yalpi foyda</p>
          <strong>{{ money(data.summary.gross_profit) }}</strong>
          <small>{{ data.summary.margin_percent }}%</small>
        </article>
      </div>

      <!-- Yo'qotishlar va sof foyda -->
      <div v-if="canSeeProfit" class="net-row">
        <div class="net-card">
          <span>Yalpi foyda</span>
          <strong>{{ money(data.summary.gross_profit) }}</strong>
        </div>

        <div class="net-sign">−</div>

        <div class="net-card loss">
          <span>Yo‘qotishlar</span>
          <strong>{{ money(data.summary.loss_amount) }}</strong>
          <small>buzilgan, muddati o‘tgan, kamomad</small>
        </div>

        <div class="net-sign">=</div>

        <div class="net-card net">
          <span>Sof foyda</span>
          <strong>{{ money(data.summary.net_profit) }}</strong>
        </div>
      </div>

      <div class="report-grid">
        <!-- Kategoriya bo'yicha -->
        <div class="table-card card-padded">
          <h3>Kategoriya bo‘yicha sotuv</h3>

          <p v-if="!data.by_category.length" class="empty-state">
            Bu davrda sotuv bo‘lmagan.
          </p>

          <div v-for="row in data.by_category" :key="row.name" class="bar-row">
            <div class="bar-head">
              <span>{{ row.name }}</span>
              <strong>{{ money(row.revenue) }}</strong>
            </div>

            <div class="bar-track">
              <div
                class="bar-fill"
                :style="{ width: `${(Number(row.revenue) / categoryMax) * 100}%` }"
              ></div>
            </div>

            <small v-if="canSeeProfit">foyda {{ money(row.profit) }} · {{ row.margin_percent }}%</small>
          </div>
        </div>

        <!-- Kunlik tushum -->
        <div class="table-card card-padded">
          <h3>Kunlik tushum</h3>

          <p v-if="!data.daily_sales.length" class="empty-state">
            Bu davrda sotuv bo‘lmagan.
          </p>

          <div v-else class="day-chart">
            <div v-for="row in data.daily_sales" :key="row.date" class="day-column">
              <div
                class="day-bar"
                :style="{ height: `${Math.max(4, (Number(row.revenue) / dailyMax) * 100)}%` }"
                :title="`${row.date}: ${money(row.revenue)}`"
              ></div>
              <small>{{ row.date.slice(5) }}</small>
            </div>
          </div>
        </div>
      </div>

      <div class="report-grid">
        <!-- Ombor bo'yicha -->
        <div class="table-card card-padded">
          <h3>Ombor bo‘yicha</h3>

          <div class="table-scroll">
            <table class="data-table">
              <thead>
                <tr>
                  <th>Ombor</th>
                  <th class="num">Sotuv</th>
                  <th class="num">Tushum</th>
                  <th v-if="canSeeProfit" class="num">Foyda</th>
                </tr>
              </thead>
              <tbody>
                <tr v-if="!data.by_warehouse.length">
                  <td :colspan="canSeeProfit ? 4 : 3" class="empty-state">Ma’lumot yo‘q</td>
                </tr>
                <tr v-for="row in data.by_warehouse" :key="row.warehouse_id">
                  <td>{{ row.name }}</td>
                  <td class="num">{{ row.count }}</td>
                  <td class="num">{{ money(row.revenue) }}</td>
                  <td v-if="canSeeProfit" class="num profit">{{ money(row.profit) }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <!-- Yo'qotishlar -->
        <div class="table-card card-padded">
          <h3>Yo‘qotishlar</h3>

          <div class="table-scroll">
            <table class="data-table">
              <thead>
                <tr>
                  <th>Sababi</th>
                  <th class="num">Soni</th>
                  <th class="num">Miqdor</th>
                  <th v-if="canSeePurchase" class="num">Summa</th>
                </tr>
              </thead>
              <tbody>
                <tr v-if="!data.losses.by_reason.length">
                  <td :colspan="canSeePurchase ? 4 : 3" class="empty-state">Yo‘qotish yo‘q</td>
                </tr>
                <tr v-for="row in data.losses.by_reason" :key="row.reason">
                  <td>{{ row.label }}</td>
                  <td class="num">{{ row.count }}</td>
                  <td class="num">{{ number(row.quantity) }}</td>
                  <td v-if="canSeePurchase" class="num loss-amount">{{ money(row.amount) }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>

      <!-- Eng ko'p sotilganlar -->
      <div class="table-card card-padded">
        <h3>Eng ko‘p tushum keltirgan mahsulotlar</h3>

        <div class="table-scroll">
          <table class="data-table">
            <thead>
              <tr>
                <th>Mahsulot</th>
                <th>SKU</th>
                <th class="num">Miqdor</th>
                <th class="num">Tushum</th>
                <th v-if="canSeeProfit" class="num">Tannarx</th>
                <th v-if="canSeeProfit" class="num">Foyda</th>
              </tr>
            </thead>
            <tbody>
              <tr v-if="!data.top_products.length">
                <td :colspan="canSeeProfit ? 6 : 4" class="empty-state">Ma’lumot yo‘q</td>
              </tr>
              <tr v-for="row in data.top_products" :key="row.variant_id">
                <td>{{ row.name }}</td>
                <td>{{ row.sku }}</td>
                <td class="num">{{ number(row.quantity) }}</td>
                <td class="num">{{ money(row.revenue) }}</td>
                <td v-if="canSeeProfit" class="num">{{ money(row.cost) }}</td>
                <td v-if="canSeeProfit" class="num profit">{{ money(row.profit) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- Qoldiq qiymati -->
      <div class="table-card card-padded">
        <h3>Qoldiq qiymati</h3>

        <div class="valuation-grid">
          <div>
            <span>Pozitsiyalar</span>
            <strong>{{ data.valuation.positions }}</strong>
          </div>
          <div>
            <span>Umumiy miqdor</span>
            <strong>{{ number(data.valuation.units) }}</strong>
          </div>
          <div v-if="canSeePurchase">
            <span>Tannarx (FIFO)</span>
            <strong>{{ money(data.valuation.cost_value) }}</strong>
          </div>
          <div>
            <span>Chakana qiymati</span>
            <strong>{{ money(data.valuation.retail_value) }}</strong>
          </div>
          <div v-if="canSeeProfit" class="accent">
            <span>Kutilayotgan foyda</span>
            <strong>{{ money(data.valuation.potential_profit) }}</strong>
            <small>{{ data.valuation.margin_percent }}%</small>
          </div>
        </div>
      </div>
    </template>
  </section>
</template>

<style scoped>
.period-buttons {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.period-button {
  min-height: var(--control-height);
  padding: 0 12px;
  border: 1px solid var(--border-strong);
  border-radius: var(--radius);
  background: var(--surface);
  color: var(--text-secondary);
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: var(--transition);
}

.period-button:hover {
  background: var(--surface-hover);
}

.period-button.active {
  border-color: var(--accent);
  background: var(--accent-soft);
  color: var(--accent);
}

.net-row {
  display: flex;
  align-items: stretch;
  gap: 8px;
  margin-bottom: 12px;
}

.net-card {
  flex: 1;
  padding: 12px 16px;
  border: 1px solid var(--border);
  border-radius: var(--radius);
  background: var(--surface);
}

.net-card span {
  display: block;
  color: var(--text-muted);
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.4px;
}

.net-card strong {
  display: block;
  margin-top: 4px;
  font-size: 18px;
}

.net-card small {
  display: block;
  margin-top: 2px;
  color: var(--text-muted);
  font-size: 12px;
}

.net-card.loss strong {
  color: var(--red);
}

.net-card.net strong {
  color: var(--green);
}

.net-sign {
  display: flex;
  align-items: center;
  color: var(--text-muted);
  font-size: 18px;
  font-weight: 600;
}

.report-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
  gap: 12px;
  margin-bottom: 12px;
}

.bar-row {
  margin-bottom: 12px;
}

.bar-head {
  display: flex;
  justify-content: space-between;
  margin-bottom: 4px;
  font-size: 13px;
}

.bar-track {
  height: 8px;
  border-radius: 999px;
  background: var(--surface-hover);
  overflow: hidden;
}

.bar-fill {
  height: 100%;
  border-radius: 999px;
  background: var(--accent);
}

.bar-row small {
  display: block;
  margin-top: 4px;
  color: var(--text-muted);
  font-size: 12px;
}

.valuation-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(130px, 1fr));
  gap: 12px;
}

.valuation-grid span {
  display: block;
  color: var(--text-muted);
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.4px;
}

.valuation-grid strong {
  display: block;
  margin-top: 4px;
  font-size: 16px;
  font-weight: 600;
  font-variant-numeric: tabular-nums;
}

.valuation-grid small {
  color: var(--text-muted);
  font-size: 12px;
}

.valuation-grid .accent strong {
  color: var(--green);
}

.profit {
  color: var(--green);
  font-weight: 700;
}

.loss-amount {
  color: var(--red);
  font-weight: 700;
}

/* Telefonda "yalpi − yo'qotish = sof" uchta tor ustunga siqilib,
   sarlavhalar ikki-uch qatorga bo'linardi — ustma-ust qo'yiladi */
@media (max-width: 660px) {
  .net-row {
    flex-direction: column;
    gap: 4px;
  }

  .net-sign {
    justify-content: center;
    line-height: 1;
  }
}

@media print {
  .no-print,
  .period-buttons {
    display: none;
  }
}
</style>
