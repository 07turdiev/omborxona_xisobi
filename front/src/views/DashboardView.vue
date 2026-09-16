<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'

import { errorMessage } from '@/api/client'
import { reportsApi } from '@/api/reports'
import { formatMoney } from '@/utils/money'
import type { Dashboard } from '@/types'

const data = ref<Dashboard | null>(null)
const loading = ref(true)
const error = ref('')

onMounted(async () => {
  try {
    data.value = await reportsApi.dashboard()
  } catch (err) {
    error.value = errorMessage(err, 'Ma’lumotlarni yuklab bo‘lmadi.')
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <section class="app-section active">
    <p v-if="error" class="load-error">{{ error }}</p>
    <p v-else-if="loading" class="empty-state">Yuklanmoqda…</p>

    <template v-else-if="data">
      <h3 class="block-title">Bugun</h3>

      <div class="kpi-row">
        <div class="kpi-card">
          <span>Tushum</span>
          <strong>{{ formatMoney(data.today.revenue) }}</strong>
        </div>

        <div class="kpi-card">
          <span>Cheklar</span>
          <strong>{{ data.today.receipts }}</strong>
        </div>

        <div class="kpi-card">
          <span>O‘rtacha chek</span>
          <strong>{{ formatMoney(data.today.average_receipt) }}</strong>
        </div>

        <div class="kpi-card">
          <span>Yalpi foyda</span>
          <strong>{{ formatMoney(data.today.gross_profit) }}</strong>
        </div>
      </div>

      <h3 class="block-title">Shu oy</h3>

      <div class="kpi-row">
        <div class="kpi-card">
          <span>Tushum</span>
          <strong>{{ formatMoney(data.month.revenue) }}</strong>
        </div>

        <div class="kpi-card">
          <span>Cheklar</span>
          <strong>{{ data.month.receipts }}</strong>
        </div>

        <div class="kpi-card">
          <span>O‘rtacha chek</span>
          <strong>{{ formatMoney(data.month.average_receipt) }}</strong>
        </div>

        <div class="kpi-card">
          <span>Yalpi foyda</span>
          <strong>{{ formatMoney(data.month.gross_profit) }}</strong>
        </div>
      </div>

      <div class="table-card card-padded low-stock">
        <div>
          <strong>Qoldig‘i kam tovarlar: {{ data.low_stock_count }} ta</strong>
          <small class="cell-sub">Eng kam qoldiq chegarasidan pastga tushganlari</small>
        </div>

        <RouterLink class="button button-outline" to="/stock">Qoldiqni ko‘rish</RouterLink>
      </div>
    </template>
  </section>
</template>

<style scoped>
.block-title {
  margin: 0 0 8px;
  font-size: 14px;
}

.kpi-row {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 12px;
  margin-bottom: 20px;
}

.kpi-card {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 14px 16px;
  border: 1px solid var(--border);
  border-radius: var(--radius);
  background: var(--surface);
}

.kpi-card span {
  color: var(--text-muted);
  font-size: 12px;
}

.kpi-card strong {
  font-size: 20px;
  font-variant-numeric: tabular-nums;
}

.low-stock {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}
</style>
