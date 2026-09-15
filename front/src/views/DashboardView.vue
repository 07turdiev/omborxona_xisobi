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
      <div class="hero-content">
        <span class="hero-date">{{ today }}</span>
        <h2>Xush kelibsiz, {{ firstName }}</h2>
        <p>Oxirgi 30 kun ko‘rsatkichlari.</p>
      </div>

      <div class="hero-actions">
        <button class="button button-outline" @click="router.push('/imports')">
          <svg><use href="#i-import" /></svg>
          <span>Yangi kirim</span>
        </button>

        <button class="button button-gradient" @click="router.push('/sales')">
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

        <article v-if="auth.can('view_profit')" class="kpi-card kpi-green">
          <div class="kpi-icon"><svg><use href="#i-report" /></svg></div>
          <p>Sof foyda</p>
          <strong>{{ money(data.summary.net_profit) }}</strong>
          <small>yo‘qotishlar ayirilgan</small>
        </article>

        <article v-if="auth.can('view_purchase_price')" class="kpi-card kpi-blue">
          <div class="kpi-icon"><svg><use href="#i-stock" /></svg></div>
          <p>Qoldiq qiymati</p>
          <strong>{{ money(data.valuation.cost_value) }}</strong>
          <small>{{ data.valuation.positions }} pozitsiya</small>
        </article>

        <article v-if="auth.can('view_profit')" class="kpi-card kpi-orange">
          <div class="kpi-icon"><svg><use href="#i-warehouse" /></svg></div>
          <p>Kutilayotgan foyda</p>
          <strong>{{ money(data.valuation.potential_profit) }}</strong>
          <small>{{ data.valuation.margin_percent }}%</small>
        </article>
      </div>

      <div class="dash-layout">
        <!-- Asosiy ustun: tushum va harakatlar -->
        <div class="dash-column">
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

          <div class="table-card card-padded movements-card">
            <h3>Oxirgi harakatlar</h3>

            <p v-if="!data.recent_movements.length" class="empty-state">
              Hali harakat yo‘q.
            </p>

            <ul v-else class="move-list">
              <li v-for="row in data.recent_movements" :key="row.id">
                <div class="move-main">
                  <strong>{{ row.product_name }}</strong>
                  <small>{{ row.warehouse_name }} · {{ time(row.occurred_at) }}</small>
                </div>

                <span class="pill move-reason" :class="row.is_loss ? 'pill-red' : 'pill-grey'">
                  {{ row.reason_display }}
                </span>

                <span
                  class="move-qty"
                  :class="Number(row.quantity) > 0 ? 'positive' : 'negative'"
                >
                  {{ Number(row.quantity) > 0 ? '+' : '' }}{{ number(row.quantity) }}
                </span>
              </li>
            </ul>
          </div>
        </div>

        <!-- Yon ustun: diqqat talab qiladigan qisqa ro'yxatlar -->
        <div class="dash-column">
          <div class="table-card card-padded">
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

          <div class="table-card card-padded">
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
      </div>
    </template>
  </section>
</template>

<style scoped>
/* Sarlavha yonida belgi turadi — qolgan uslub app.css dan */
.table-card h3 {
  display: flex;
  align-items: center;
  gap: 6px;
}

/* Ikki ustun: chapda asosiy ma'lumot, o'ngda qisqa ro'yxatlar.
   Ilgari kartalar juft-juft qatorlarda edi va qisqa ro'yxat
   qo'shnisining balandligiga cho'zilib, yarim ekran bo'sh quti
   bo'lib turardi. Ustunlar mustaqil — har karta o'z balandligida. */
.dash-layout {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(280px, 360px);
  align-items: start;
  gap: 12px;
}

.dash-column {
  min-width: 0;

  display: flex;
  flex-direction: column;
  gap: 12px;
}

@media (max-width: 1100px) {
  .dash-layout {
    grid-template-columns: minmax(0, 1fr);
  }
}

.count-badge {
  padding: 2px 6px;
  border-radius: 999px;
  background: var(--yellow-soft);
  color: var(--yellow);
  font-size: 12px;
}

.count-badge.danger {
  background: var(--red-soft);
  color: var(--red);
}

.mini-list,
.move-list {
  list-style: none;
}

.mini-list li {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 8px 0;
  border-bottom: 1px solid var(--border);
  font-size: 13px;
}

.mini-list li:last-child,
.move-list li:last-child {
  border-bottom: none;
}

.mini-list strong {
  display: block;
}

.mini-list small,
.move-main small {
  display: block;
  margin-top: 2px;
  color: var(--text-muted);
  font-size: 12px;
}

/* Harakatlar ro'yxati. Jadval edi — telefonda sabab yorlig'i karta
   chetidan kesilib qolardi. Endi karta tor bo'lsa, yorliq nom ostiga
   tushadi (container query: sahifa emas, kartaning o'z kengligi). */
.movements-card {
  container: movements / inline-size;
}

.move-list li {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto 72px;
  align-items: center;
  gap: 4px 12px;
  padding: 8px 0;
  border-bottom: 1px solid var(--border);
}

.move-main {
  min-width: 0;
}

.move-main strong {
  display: block;
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
  font-size: 13px;
  font-weight: 500;
}

.move-reason {
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
}

.move-qty {
  text-align: right;
  white-space: nowrap;
  font-weight: 600;
  font-variant-numeric: tabular-nums;
}

@container movements (max-width: 520px) {
  .move-list li {
    grid-template-columns: minmax(0, 1fr) auto;
  }

  .move-reason {
    grid-column: 1;
    grid-row: 2;
    justify-self: start;
  }

  .move-qty {
    grid-column: 2;
    grid-row: 1 / span 2;
  }
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
</style>
