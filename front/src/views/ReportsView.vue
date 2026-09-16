<script setup lang="ts">
import { onMounted, ref } from 'vue'

import { errorMessage } from '@/api/client'
import { reportsApi } from '@/api/reports'
import { useExport } from '@/composables/useExport'
import { daysAgoIso, monthStartIso, todayIso } from '@/utils/date'
import { formatMoney } from '@/utils/money'
import type { SalesReport, TopProduct } from '@/types'

const report = ref<SalesReport | null>(null)
const top = ref<TopProduct[]>([])

const dateFrom = ref(monthStartIso())
const dateTo = ref(todayIso())

const loading = ref(false)
const error = ref('')

const { exporting, exportError, onExport } = useExport(() =>
  reportsApi.exportSales({ date_from: dateFrom.value, date_to: dateTo.value }),
)

async function load() {
  loading.value = true
  error.value = ''

  const period = { date_from: dateFrom.value, date_to: dateTo.value }

  try {
    ;[report.value, top.value] = await Promise.all([
      reportsApi.sales(period),
      reportsApi.topProducts(period),
    ])
  } catch (err) {
    error.value = errorMessage(err, 'Hisobotni yuklab bo‘lmadi.')
  } finally {
    loading.value = false
  }
}

function preset(kind: 'today' | 'week' | 'month') {
  if (kind === 'today') {
    dateFrom.value = todayIso()
  } else if (kind === 'week') {
    dateFrom.value = daysAgoIso(6)
  } else {
    dateFrom.value = monthStartIso()
  }

  dateTo.value = todayIso()

  return load()
}

onMounted(load)
</script>

<template>
  <section class="app-section active">
    <div class="section-toolbar">
      <div class="filters">
        <input v-model="dateFrom" type="date" />
        <input v-model="dateTo" type="date" />

        <button class="button button-outline" type="button" @click="load">Ko‘rsatish</button>
        <button class="button button-outline" type="button" @click="preset('today')">Bugun</button>
        <button class="button button-outline" type="button" @click="preset('week')">7 kun</button>
        <button class="button button-outline" type="button" @click="preset('month')">Shu oy</button>
      </div>

      <button class="button button-outline" type="button" :disabled="exporting" @click="onExport">
        <svg><use href="#i-download" /></svg>
        <span>{{ exporting ? 'Tayyorlanmoqda…' : 'Excel' }}</span>
      </button>
    </div>

    <p v-if="error" class="load-error">{{ error }}</p>
    <p v-if="exportError" class="load-error">{{ exportError }}</p>
    <p v-if="loading" class="empty-state">Yuklanmoqda…</p>

    <template v-else-if="report">
      <div class="kpi-row">
        <div class="kpi-card">
          <span>Sof tushum</span>
          <strong>{{ formatMoney(report.net_revenue) }}</strong>
        </div>

        <div class="kpi-card">
          <span>Cheklar</span>
          <strong>{{ report.receipts }}</strong>
        </div>

        <div class="kpi-card">
          <span>Tannarx</span>
          <strong>{{ formatMoney(report.cost) }}</strong>
        </div>

        <div class="kpi-card">
          <span>Yalpi foyda</span>
          <strong>{{ formatMoney(report.gross_profit) }}</strong>
        </div>

        <div class="kpi-card">
          <span>Sof foyda</span>
          <strong>{{ formatMoney(report.net_profit) }}</strong>
        </div>
      </div>

      <div class="secondary-row">
        <span>Chegirmalar: <strong>{{ formatMoney(report.discounts) }}</strong></span>
        <span>Qaytarishlar: <strong>{{ formatMoney(report.returns) }}</strong></span>
        <span>Yo‘qotishlar: <strong>{{ formatMoney(report.losses) }}</strong></span>
        <span>Xarajatlar: <strong>{{ formatMoney(report.expenses) }}</strong></span>
        <span>Naqd: <strong>{{ formatMoney(report.payments.cash) }}</strong></span>
        <span>Karta: <strong>{{ formatMoney(report.payments.card) }}</strong></span>
      </div>

      <div class="report-grid">
        <div class="table-card">
          <h3 class="card-title">Kategoriya bo‘yicha</h3>

          <table class="data-table">
            <thead>
              <tr>
                <th>Kategoriya</th>
                <th class="num">Dona</th>
                <th class="num">Tushum</th>
                <th class="num">Foyda</th>
              </tr>
            </thead>

            <tbody>
              <tr v-if="!report.by_category.length">
                <td colspan="4" class="empty-state">Ma’lumot yo‘q.</td>
              </tr>

              <tr v-for="row in report.by_category" v-else :key="row.name">
                <td>{{ row.name }}</td>
                <td class="num">{{ row.quantity }}</td>
                <td class="num">{{ formatMoney(row.revenue) }}</td>
                <td class="num">{{ formatMoney(row.profit) }}</td>
              </tr>
            </tbody>
          </table>
        </div>

        <div class="table-card">
          <h3 class="card-title">Kassirlar</h3>

          <table class="data-table">
            <thead>
              <tr>
                <th>Kassir</th>
                <th class="num">Cheklar</th>
                <th class="num">Tushum</th>
              </tr>
            </thead>

            <tbody>
              <tr v-if="!report.by_cashier.length">
                <td colspan="3" class="empty-state">Ma’lumot yo‘q.</td>
              </tr>

              <tr v-for="row in report.by_cashier" v-else :key="row.name ?? 'yoq'">
                <td>{{ row.name ?? '—' }}</td>
                <td class="num">{{ row.receipts }}</td>
                <td class="num">{{ formatMoney(row.revenue) }}</td>
              </tr>
            </tbody>
          </table>
        </div>

        <div class="table-card">
          <h3 class="card-title">Yo‘qotishlar</h3>

          <table class="data-table">
            <thead>
              <tr>
                <th>Sababi</th>
                <th class="num">Dona</th>
                <th class="num">Summa</th>
              </tr>
            </thead>

            <tbody>
              <tr v-if="!report.loss_rows.length">
                <td colspan="3" class="empty-state">Yo‘qotish yo‘q.</td>
              </tr>

              <tr v-for="row in report.loss_rows" v-else :key="row.reason">
                <td>{{ row.reason }}</td>
                <td class="num">{{ row.quantity }}</td>
                <td class="num">{{ formatMoney(row.amount) }}</td>
              </tr>
            </tbody>
          </table>
        </div>

        <div class="table-card">
          <h3 class="card-title">Xarajatlar</h3>

          <table class="data-table">
            <thead>
              <tr>
                <th>Turi</th>
                <th class="num">Summa</th>
              </tr>
            </thead>

            <tbody>
              <tr v-if="!report.expense_rows.length">
                <td colspan="2" class="empty-state">Xarajat yo‘q.</td>
              </tr>

              <tr v-for="row in report.expense_rows" v-else :key="row.category">
                <td>{{ row.category }}</td>
                <td class="num">{{ formatMoney(row.amount) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <div class="table-card">
        <h3 class="card-title">Eng ko‘p sotilganlar</h3>

        <div class="table-scroll">
          <table class="data-table">
            <thead>
              <tr>
                <th>Mahsulot</th>
                <th class="num">Dona</th>
                <th class="num">Tushum</th>
                <th class="num">Foyda</th>
              </tr>
            </thead>

            <tbody>
              <tr v-if="!top.length">
                <td colspan="4" class="empty-state">Sotuv bo‘lmagan.</td>
              </tr>

              <tr v-for="item in top" v-else :key="item.product_id">
                <td>
                  <strong>{{ item.name }}</strong>
                  <small class="cell-sub">
                    {{ item.variants.map((v) => `${v.size ?? ''} ${v.color ?? ''}`.trim()).join(', ') }}
                  </small>
                </td>
                <td class="num">{{ item.quantity }}</td>
                <td class="num">{{ formatMoney(item.revenue) }}</td>
                <td class="num">{{ formatMoney(item.profit) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </template>
  </section>
</template>

<style scoped>
.kpi-row {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
  gap: 12px;
  margin-bottom: 12px;
}

.kpi-card {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 12px 14px;
  border: 1px solid var(--border);
  border-radius: var(--radius);
  background: var(--surface);
}

.kpi-card span {
  color: var(--text-muted);
  font-size: 12px;
}

.kpi-card strong {
  font-size: 18px;
  font-variant-numeric: tabular-nums;
}

.secondary-row {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  margin-bottom: 12px;
  padding: 10px 14px;
  border: 1px solid var(--border);
  border-radius: var(--radius);
  background: var(--surface);
  font-size: 13px;
}

.report-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
  gap: 12px;
  margin-bottom: 12px;
}

.card-title {
  padding: 12px 16px 0;
  margin: 0;
  font-size: 14px;
}
</style>
