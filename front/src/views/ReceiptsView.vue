<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { RouterLink, useRoute } from 'vue-router'

import ReceiptPrint from '@/components/ReceiptPrint.vue'
import { errorMessage } from '@/api/client'
import { salesApi } from '@/api/sales'
import { useAuthStore } from '@/stores/auth'
import { formatMoney, formatSum } from '@/utils/money'
import type { Sale } from '@/types'

const auth = useAuthStore()
const route = useRoute()

const sales = ref<Sale[]>([])
const selected = ref<Sale | null>(null)
const receipt = ref<InstanceType<typeof ReceiptPrint> | null>(null)

const loading = ref(false)
const error = ref('')
const search = ref('')

const title = computed(() =>
  auth.isAdmin ? 'Barcha cheklar' : 'Mening bugungi cheklarim',
)

async function load() {
  loading.value = true
  error.value = ''

  try {
    const page = await salesApi.list()
    sales.value = page.results
  } catch (err) {
    error.value = errorMessage(err, 'Cheklarni yuklab bo‘lmadi.')
  } finally {
    loading.value = false
  }
}

async function onSearch() {
  const number = search.value.trim()

  if (!number) return load()

  loading.value = true
  error.value = ''

  try {
    const found = await salesApi.byNumber(number)

    sales.value = found ? [found] : []

    if (!found) error.value = `«${number}» — bunday chek topilmadi.`
  } catch (err) {
    error.value = errorMessage(err, 'Chekni topib bo‘lmadi.')
  } finally {
    loading.value = false
  }
}

function open(sale: Sale) {
  selected.value = sale
}

function print() {
  receipt.value?.printReceipt()
}

async function onVoid(sale: Sale) {
  if (!window.confirm(`${sale.number} bekor qilinsinmi? Tovar omborga qaytadi.`)) return

  try {
    await salesApi.void(sale.id)
    await load()
    selected.value = null
  } catch (err) {
    error.value = errorMessage(err, 'Chekni bekor qilib bo‘lmadi.')
  }
}

function time(value: string): string {
  return new Date(value).toLocaleString('uz-UZ', {
    day: '2-digit',
    month: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}

/** Mahsulotning qoldiq tarixidan kelingan bo'lsa (`?number=SOT-…`) — o'sha chek ochiladi */
onMounted(async () => {
  const number = String(route.query.number ?? '').trim()

  if (!number) return load()

  search.value = number
  await onSearch()

  if (sales.value[0]) open(sales.value[0])
})
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
            placeholder="Chek raqami…"
            @keydown.enter.prevent="onSearch"
          />
        </div>

        <button class="button button-outline" type="button" @click="onSearch">Topish</button>
      </div>
    </div>

    <p v-if="error" class="load-error">{{ error }}</p>

    <div class="receipts">
      <div class="table-card">
        <h3 class="card-title">{{ title }}</h3>

        <div class="table-scroll">
          <table class="data-table">
            <thead>
              <tr>
                <th>Chek</th>
                <th>Vaqti</th>
                <th v-if="auth.isAdmin">Kassir</th>
                <th class="num">Summa</th>
                <th>Holati</th>
              </tr>
            </thead>

            <tbody>
              <tr v-if="loading">
                <td :colspan="auth.isAdmin ? 5 : 4" class="empty-state">Yuklanmoqda…</td>
              </tr>

              <tr v-else-if="!sales.length">
                <td :colspan="auth.isAdmin ? 5 : 4" class="empty-state">
                  Hozircha chek yo‘q.
                </td>
              </tr>

              <tr
                v-for="sale in sales"
                v-else
                :key="sale.id"
                class="clickable"
                :class="{ active: selected?.id === sale.id }"
                @click="open(sale)"
              >
                <td><strong>{{ sale.number }}</strong></td>
                <td>{{ time(sale.created_at) }}</td>
                <td v-if="auth.isAdmin">{{ sale.cashier_name ?? '—' }}</td>
                <td class="num">{{ formatMoney(sale.total) }}</td>
                <td>
                  <span class="pill" :class="sale.status === 'voided' ? 'pill-red' : 'pill-green'">
                    {{ sale.status_display }}
                  </span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <aside v-if="selected" class="table-card card-padded receipt-detail">
        <h3>{{ selected.number }}</h3>

        <table class="data-table">
          <tbody>
            <tr v-for="line in selected.lines" :key="line.id">
              <td>
                {{ line.product_name }}
                <small class="cell-sub">{{ line.variant_label || line.sku }}</small>
              </td>
              <td class="num">{{ line.quantity }} × {{ formatMoney(line.unit_price) }}</td>
              <td class="num"><strong>{{ formatMoney(line.line_total) }}</strong></td>
            </tr>
          </tbody>
        </table>

        <div class="detail-totals">
          <div><span>Chegirma</span><strong>{{ formatMoney(selected.discount_total) }}</strong></div>
          <div><span>Naqd</span><strong>{{ formatMoney(selected.cash_amount) }}</strong></div>
          <div><span>Karta</span><strong>{{ formatMoney(selected.card_amount) }}</strong></div>
          <div class="grand"><span>Jami</span><strong>{{ formatSum(selected.total) }}</strong></div>
          <div v-if="auth.isAdmin && selected.profit">
            <span>Foyda</span><strong>{{ formatMoney(selected.profit) }}</strong>
          </div>
        </div>

        <div class="detail-actions">
          <button class="button button-outline" type="button" @click="print">
            <svg><use href="#i-print" /></svg>
            <span>Chop etish</span>
          </button>

          <RouterLink
            v-if="auth.isAdmin && selected.status === 'completed'"
            class="button button-outline"
            :to="{ path: '/returns', query: { number: selected.number } }"
          >
            Qaytarish / almashtirish
          </RouterLink>

          <button
            v-if="auth.isAdmin && selected.status === 'completed'"
            class="button button-danger"
            type="button"
            @click="onVoid(selected)"
          >
            Bekor qilish
          </button>
        </div>
      </aside>
    </div>

    <ReceiptPrint ref="receipt" :sale="selected" />
  </section>
</template>

<style scoped>
.receipts {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 360px;
  align-items: start;
  gap: 12px;
}

@media (max-width: 1000px) {
  .receipts {
    grid-template-columns: 1fr;
  }
}

.card-title {
  padding: 12px 16px 0;
  font-size: 15px;
}

.clickable {
  cursor: pointer;
}

.clickable.active td {
  background: var(--accent-soft);
}

.detail-totals {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid var(--border);
}

.detail-totals > div {
  display: flex;
  justify-content: space-between;
  padding: 3px 0;
  font-size: 13px;
}

.detail-totals .grand strong {
  font-size: 18px;
}

.detail-actions {
  display: flex;
  gap: 8px;
  margin-top: 12px;
}
</style>
