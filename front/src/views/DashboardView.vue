<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'

import { reportsApi } from '@/api/reports'
import { useAuthStore } from '@/stores/auth'
import type { DashboardBundle } from '@/types'

const auth = useAuthStore()
const router = useRouter()

const data = ref<DashboardBundle | null>(null)
const loading = ref(false)

const today = computed(() =>
  new Intl.DateTimeFormat('uz-UZ', {
    day: 'numeric',
    month: 'long',
    year: 'numeric',
  }).format(new Date()),
)

const firstName = computed(() => auth.user?.first_name || auth.user?.username || '')

onMounted(async () => {
  loading.value = true

  try {
    // Oxirgi 30 kun
    const from = new Date()
    from.setDate(from.getDate() - 30)

    data.value = await reportsApi.dashboard({
      date_from: from.toISOString().slice(0, 10),
    })
  } finally {
    loading.value = false
  }
})

function money(value: string | null | undefined): string {
  if (value == null) return '—'
  return new Intl.NumberFormat('uz-UZ', { maximumFractionDigits: 0 }).format(Number(value))
}

function number(value: string | null | undefined): string {
  if (value == null) return '—'
  return new Intl.NumberFormat('uz-UZ', { maximumFractionDigits: 3 }).format(Number(value))
}

function time(value: string): string {
  return new Intl.DateTimeFormat('uz-UZ', {
    day: '2-digit',
    month: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  }).format(new Date(value))
}

const dailyMax = computed(() =>
  Math.max(1, ...(data.value?.daily_sales ?? []).map((row) => Number(row.revenue))),
)
</script>

<template>
  <section class="app-section active">
    <div class="hero-card">
      <div class="hero-orb orb-one"></div>
      <div class="hero-orb orb-two"></div>

      <div class="hero-content">
        <span class="hero-date">{{ today }}</span>
        <h2>Xush kelibsiz, {{ firstName }}</h2>
        <p>Oxirgi 30 kun ko‘rsatkichlari.</p>
      </div>

      <div class="hero-actions">
        <button class="button button-glass" @click="router.push('/imports')">
          <svg><use href="#i-import" /></svg>
          <span>Yangi kirim</span>
        </button>

        <button class="button button-white" @click="router.push('/sales')">
          <svg><use href="#i-sale" /></svg>
          <span>Yangi sotuv</span>
        </button>
      </div>
    </div>

    <p v-if="loading" class="empty-state">Yuklanmoqda…</p>

    <template v-if="data && !loading">
      <div class="kpi-grid">
        <article class="kpi-card kpi-purple">
          <div class="kpi-icon"><svg><use href="#i-sale" /></svg></div>
          <p>Tushum</p>
          <strong>{{ money(data.summary.revenue) }}</strong>
          <small>{{ data.summary.sale_count }} sotuv</small>
        </article>

        <article class="kpi-card kpi-green">
          <div class="kpi-icon"><svg><use href="#i-report" /></svg></div>
          <p>Sof foyda</p>
          <strong>{{ money(data.summary.net_profit) }}</strong>
          <small>yo‘qotishlar ayirilgan</small>
        </article>

        <article class="kpi-card kpi-blue">
          <div class="kpi-icon"><svg><use href="#i-stock" /></svg></div>
          <p>Qoldiq qiymati</p>
          <strong>{{ money(data.valuation.cost_value) }}</strong>
          <small>{{ data.valuation.positions }} pozitsiya</small>
        </article>

        <article class="kpi-card kpi-orange">
          <div class="kpi-icon"><svg><use href="#i-warehouse" /></svg></div>
          <p>Kutilayotgan foyda</p>
          <strong>{{ money(data.valuation.potential_profit) }}</strong>
          <small>{{ data.valuation.margin_percent }}%</small>
        </article>
      </div>

      <div class="dash-grid">
        <div class="table-card chart-card">
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

        <div class="table-card">
          <h3>
            Kam qolgan tovarlar
            <b v-if="data.low_stock.length" class="count-badge">
              {{ data.low_stock.length }}
            </b>
          </h3>

          <p v-if="!data.low_stock.length" class="empty-state">Hammasi yetarli.</p>

          <ul v-else class="mini-list">
            <li v-for="row in data.low_stock" :key="`${row.variant_id}-${row.warehouse_name}`">
              <div>
                <strong>{{ row.product_name }}</strong>
                <small>{{ row.warehouse_name }}</small>
              </div>
              <span class="warn">{{ number(row.quantity) }} {{ row.unit }}</span>
            </li>
          </ul>
        </div>
      </div>

      <div class="dash-grid">
        <div class="table-card">
          <h3>Oxirgi harakatlar</h3>

          <p v-if="!data.recent_movements.length" class="empty-state">
            Hali harakat yo‘q.
          </p>

          <table v-else class="data-table">
            <tbody>
              <tr v-for="row in data.recent_movements" :key="row.id">
                <td class="dim">{{ time(row.occurred_at) }}</td>
                <td>
                  {{ row.product_name }}
                  <small class="cell-sub">{{ row.warehouse_name }}</small>
                </td>
                <td>
                  <span class="pill" :class="row.is_loss ? 'pill-red' : 'pill-grey'">
                    {{ row.reason_display }}
                  </span>
                </td>
                <td class="num" :class="Number(row.quantity) > 0 ? 'positive' : 'negative'">
                  {{ Number(row.quantity) > 0 ? '+' : '' }}{{ number(row.quantity) }}
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <div class="table-card">
          <h3>
            Muddati yaqin partiyalar
            <b v-if="data.expiring.length" class="count-badge danger">
              {{ data.expiring.length }}
            </b>
          </h3>

          <p v-if="!data.expiring.length" class="empty-state">
            30 kun ichida muddati tugaydigan tovar yo‘q.
          </p>

          <ul v-else class="mini-list">
            <li v-for="row in data.expiring" :key="row.batch_code">
              <div>
                <strong>{{ row.product_name }}</strong>
                <small>{{ row.batch_code }} · {{ row.warehouse_name }}</small>
              </div>
              <span :class="row.is_expired ? 'danger' : 'warn'">
                {{ row.is_expired ? 'muddati o‘tgan' : `${row.days_left} kun` }}
              </span>
            </li>
          </ul>
        </div>
      </div>
    </template>
  </section>
</template>

<style scoped>
.dash-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
  gap: 14px;
  margin-bottom: 14px;
}

.table-card {
  padding: 18px 20px;
}

.table-card h3 {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 12px;
  font-size: 10px;
}

.count-badge {
  padding: 2px 7px;
  border-radius: 999px;
  background: var(--yellow-soft);
  color: var(--yellow);
  font-size: 7px;
}

.count-badge.danger {
  background: var(--red-soft);
  color: var(--red);
}

.chart-card {
  min-height: 200px;
}

.day-chart {
  display: flex;
  align-items: flex-end;
  gap: 6px;
  height: 150px;
  padding-top: 10px;
}

.day-column {
  display: flex;
  flex: 1;
  flex-direction: column;
  align-items: center;
  justify-content: flex-end;
  height: 100%;
  gap: 4px;
}

.day-bar {
  width: 100%;
  max-width: 26px;
  border-radius: 4px 4px 0 0;
  background: linear-gradient(180deg, var(--purple-2), var(--purple));
}

.day-column small {
  color: var(--text-muted);
  font-size: 6px;
}

.mini-list {
  list-style: none;
}

.mini-list li {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  padding: 8px 0;
  border-bottom: 1px solid var(--border);
  font-size: 8px;
}

.mini-list li:last-child {
  border-bottom: none;
}

.mini-list strong {
  display: block;
}

.mini-list small {
  display: block;
  margin-top: 2px;
  color: var(--text-muted);
  font-size: 7px;
}

.warn {
  color: var(--yellow);
  font-weight: 700;
  white-space: nowrap;
}

.danger {
  color: var(--red);
  font-weight: 700;
  white-space: nowrap;
}

.dim {
  color: var(--text-muted);
  font-size: 7px;
  white-space: nowrap;
}

.cell-sub {
  display: block;
  margin-top: 2px;
  color: var(--text-muted);
  font-size: 7px;
}

.num {
  text-align: right;
  font-weight: 700;
}

.positive {
  color: var(--green);
}

.negative {
  color: var(--red);
}

.pill {
  display: inline-block;
  padding: 3px 8px;
  border-radius: 999px;
  font-size: 6px;
  font-weight: 700;
  white-space: nowrap;
}

.pill-grey {
  background: var(--surface-hover);
  color: var(--text-secondary);
}

.pill-red {
  background: var(--red-soft);
  color: var(--red);
}
</style>
