<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'

import { catalogApi } from '@/api/catalog'
import { errorMessage } from '@/api/client'
import { reportsApi } from '@/api/reports'
import { useExport } from '@/composables/useExport'
import { formatMoney } from '@/utils/money'
import type { Category, StockReport } from '@/types'

/**
 * Qoldiq qiymati: ombordagi tovar tannarxda va sotuv narxida.
 *
 * Ilgari bu raqamlar "Qoldiq" sahifasining tepasida turardi. Qoldiqning
 * o'zi endi mahsulotlar ro'yxatida ko'rinadi, pul qiymati esa hisobot —
 * shuning uchun shu yerga ko'chdi.
 */

const report = ref<StockReport | null>(null)
const categories = ref<Category[]>([])

const category = ref('')
const lowOnly = ref(false)
const loading = ref(false)
const error = ref('')

const filters = () => ({
  category: category.value || undefined,
  low_stock: lowOnly.value ? ('true' as const) : undefined,
})

const { exporting, exportError, onExport } = useExport(() => reportsApi.exportStock(filters()))

async function load() {
  loading.value = true
  error.value = ''

  try {
    report.value = await reportsApi.stock(filters())
  } catch (err) {
    error.value = errorMessage(err, 'Hisobotni yuklab bo‘lmadi.')
  } finally {
    loading.value = false
  }
}

onMounted(async () => {
  try {
    categories.value = await catalogApi.categories()
  } catch {
    // Kategoriya filtrisiz ham ishlaydi
  }

  await load()
})

watch([category, lowOnly], load)
</script>

<template>
  <section class="app-section active">
    <div class="section-toolbar">
      <div class="filters">
        <select v-model="category" aria-label="Kategoriya">
          <option value="">Barcha kategoriya</option>
          <option v-for="item in categories" :key="item.id" :value="String(item.id)">
            {{ item.name }}
          </option>
        </select>

        <label class="check">
          <input v-model="lowOnly" type="checkbox" />
          <span>Faqat tugayotganlar</span>
        </label>
      </div>

      <button class="button button-outline" type="button" :disabled="exporting" @click="onExport">
        <svg><use href="#i-download" /></svg>
        <span>{{ exporting ? 'Tayyorlanmoqda…' : 'Excel' }}</span>
      </button>
    </div>

    <p v-if="error" class="load-error">{{ error }}</p>
    <p v-if="exportError" class="load-error">{{ exportError }}</p>

    <template v-if="report">
      <div class="kpi-row" data-testid="stock-value-kpis">
        <div class="kpi-card">
          <span>Pozitsiya</span>
          <strong>{{ report.positions }}</strong>
        </div>

        <div class="kpi-card">
          <span>Jami dona</span>
          <strong>{{ report.units }}</strong>
        </div>

        <div class="kpi-card">
          <span>Tannarx bo‘yicha</span>
          <strong>{{ formatMoney(report.cost_value) }}</strong>
        </div>

        <div class="kpi-card">
          <span>Sotuv narxida</span>
          <strong>{{ formatMoney(report.retail_value) }}</strong>
        </div>

        <div class="kpi-card accent">
          <span>Kutilayotgan foyda</span>
          <strong>{{ formatMoney(report.potential_profit) }}</strong>
          <small>hammasi to‘liq narxda sotilsa</small>
        </div>
      </div>

      <div class="table-card">
        <div class="table-scroll">
          <table class="data-table">
            <thead>
              <tr>
                <th>Mahsulot</th>
                <th>Kategoriya</th>
                <th>SKU</th>
                <th class="num">Qoldiq</th>
                <th class="num">Tannarx</th>
                <th class="num">Tannarx bo‘yicha</th>
                <th class="num">Sotuv narxida</th>
              </tr>
            </thead>

            <tbody>
              <tr v-if="loading">
                <td colspan="7" class="empty-state">Yuklanmoqda…</td>
              </tr>

              <tr v-else-if="!report.rows.length">
                <td colspan="7" class="empty-state">Tovar topilmadi.</td>
              </tr>

              <tr v-for="row in report.rows" v-else :key="row.variant_id">
                <td>
                  <strong>{{ row.product }}</strong>
                  <small v-if="row.label" class="cell-sub">{{ row.label }}</small>
                </td>
                <td>{{ row.category }}</td>
                <td>{{ row.sku }}</td>
                <td class="num">
                  <span :class="{ low: row.min_stock > 0 && row.quantity <= row.min_stock }">
                    {{ row.quantity }}
                  </span>
                </td>
                <td class="num">{{ formatMoney(row.average_cost) }}</td>
                <td class="num">{{ formatMoney(row.cost_value) }}</td>
                <td class="num">{{ formatMoney(row.retail_value) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </template>

    <p v-else-if="loading" class="empty-state">Yuklanmoqda…</p>
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
  border-radius: var(--radius-card);
  background: var(--surface);
}

.kpi-card span,
.kpi-card small {
  color: var(--text-muted);
  font-size: 12px;
}

.kpi-card strong {
  font-size: 18px;
  font-variant-numeric: tabular-nums;
}

.kpi-card.accent {
  border-color: var(--green);
  background: var(--green-soft);
}

.check {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  white-space: nowrap;
}

.check input {
  width: 16px;
  height: 16px;
  min-height: 0;
}

.low {
  color: var(--red);
  font-weight: 700;
}
</style>
