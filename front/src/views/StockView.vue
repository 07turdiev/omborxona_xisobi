<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'

import { catalogApi } from '@/api/catalog'
import { errorMessage } from '@/api/client'
import { reportsApi } from '@/api/reports'
import { useAuthStore } from '@/stores/auth'
import { useExport } from '@/composables/useExport'
import { formatMoney } from '@/utils/money'
import type { Category, StockReport, Variant } from '@/types'

const auth = useAuthStore()

const variants = ref<Variant[]>([])
const categories = ref<Category[]>([])
const summary = ref<StockReport | null>(null)

const search = ref('')
const category = ref<string>('')
const lowOnly = ref(false)
const loading = ref(false)
const error = ref('')

const { exporting, exportError, onExport } = useExport(() =>
  reportsApi.exportStock({
    category: category.value || undefined,
    low_stock: lowOnly.value ? 'true' : undefined,
  }),
)

async function load() {
  loading.value = true
  error.value = ''

  try {
    const page = await catalogApi.variants({
      search: search.value || undefined,
      category: category.value || undefined,
      low_stock: lowOnly.value ? 'true' : undefined,
    })

    variants.value = page.results

    // Tannarx va umumiy qiymat faqat administratorga ko'rinadi
    if (auth.isAdmin) {
      summary.value = await reportsApi.stock({
        category: category.value || undefined,
        low_stock: lowOnly.value ? 'true' : undefined,
      })
    }
  } catch (err) {
    error.value = errorMessage(err, 'Qoldiqni yuklab bo‘lmadi.')
  } finally {
    loading.value = false
  }
}

onMounted(async () => {
  categories.value = await catalogApi.categories()
  await load()
})

watch([category, lowOnly], load)
</script>

<template>
  <section class="app-section active">
    <div class="section-toolbar">
      <div class="filters">
        <div class="search-field">
          <svg><use href="#i-search" /></svg>
          <input
            v-model="search"
            type="search"
            placeholder="Nomi, SKU yoki shtrix-kod…"
            @keydown.enter.prevent="load"
          />
        </div>

        <select v-model="category">
          <option value="">Barcha kategoriya</option>
          <option v-for="item in categories" :key="item.id" :value="item.id">{{ item.name }}</option>
        </select>

        <label class="check">
          <input v-model="lowOnly" type="checkbox" />
          <span>Faqat kam qolganlar</span>
        </label>

        <button class="button button-outline" type="button" @click="load">Qidirish</button>
      </div>

      <button
        v-if="auth.isAdmin"
        class="button button-outline"
        type="button"
        :disabled="exporting"
        @click="onExport"
      >
        <svg><use href="#i-download" /></svg>
        <span>{{ exporting ? 'Tayyorlanmoqda…' : 'Excel' }}</span>
      </button>
    </div>

    <p v-if="error" class="load-error">{{ error }}</p>
    <p v-if="exportError" class="load-error">{{ exportError }}</p>

    <div v-if="auth.isAdmin && summary" class="kpi-row">
      <div class="kpi-card">
        <span>Pozitsiya</span>
        <strong>{{ summary.positions }}</strong>
      </div>

      <div class="kpi-card">
        <span>Jami dona</span>
        <strong>{{ summary.units }}</strong>
      </div>

      <div class="kpi-card">
        <span>Tannarx bo‘yicha</span>
        <strong>{{ formatMoney(summary.cost_value) }}</strong>
      </div>

      <div class="kpi-card">
        <span>Sotuv narxida</span>
        <strong>{{ formatMoney(summary.retail_value) }}</strong>
      </div>
    </div>

    <div class="table-card">
      <div class="table-scroll">
        <table class="data-table">
          <thead>
            <tr>
              <th>Mahsulot</th>
              <th>SKU</th>
              <th>Shtrix-kod</th>
              <th class="num">Qoldiq</th>
              <th class="num">Eng kam</th>
              <th v-if="auth.isAdmin" class="num">Tannarx</th>
              <th class="num">Narx</th>
            </tr>
          </thead>

          <tbody>
            <tr v-if="loading">
              <td :colspan="auth.isAdmin ? 7 : 6" class="empty-state">Yuklanmoqda…</td>
            </tr>

            <tr v-else-if="!variants.length">
              <td :colspan="auth.isAdmin ? 7 : 6" class="empty-state">Tovar topilmadi.</td>
            </tr>

            <tr v-for="variant in variants" v-else :key="variant.id">
              <td>
                <strong>{{ variant.product_name }}</strong>
                <small class="cell-sub">{{ variant.label }}</small>
              </td>

              <td>{{ variant.sku }}</td>
              <td>{{ variant.barcode }}</td>

              <td class="num">
                <span :class="{ low: variant.stock_quantity <= variant.min_stock }">
                  {{ variant.stock_quantity }}
                </span>
              </td>

              <td class="num">{{ variant.min_stock }}</td>
              <td v-if="auth.isAdmin" class="num">{{ formatMoney(variant.average_cost ?? null) }}</td>
              <td class="num">{{ formatMoney(variant.price) }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
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
