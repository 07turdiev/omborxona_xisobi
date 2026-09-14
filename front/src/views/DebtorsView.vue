<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'

import { debtsApi } from '@/api/debts'
import { useExport } from '@/composables/useExport'
import { useAuthStore } from '@/stores/auth'
import { useWarehouseStore } from '@/stores/warehouses'
import type { Debt, DebtSummary } from '@/types'

const auth = useAuthStore()
const warehouses = useWarehouseStore()

const items = ref<Debt[]>([])
const summary = ref<DebtSummary | null>(null)
const loading = ref(false)
const error = ref('')
const expanded = ref<Set<number>>(new Set())

const filters = reactive({ search: '', status: 'active', customer_type: '', warehouse: '' })

const { exporting, exportError, onExport } = useExport(() => debtsApi.exportExcel(filters))

/** Kuzatuvchi hech narsani o'zgartira olmaydi — server ham shunday tekshiradi */
const canPay = computed(
  () => auth.can('debtors') && auth.user?.current_tenant?.role !== 'viewer',
)

async function load() {
  loading.value = true
  error.value = ''

  try {
    const [list, totals] = await Promise.all([
      debtsApi.list(filters),
      debtsApi.summary(filters),
    ])

    items.value = list.results
    summary.value = totals
  } catch {
    error.value = 'Qarzdorlarni olishda xatolik.'
  } finally {
    loading.value = false
  }
}

onMounted(async () => {
  await Promise.all([load(), warehouses.load()])
})

let searchTimer: ReturnType<typeof setTimeout> | undefined

function onSearchInput() {
  clearTimeout(searchTimer)
  searchTimer = setTimeout(load, 300)
}

function toggle(id: number) {
  const next = new Set(expanded.value)

  if (next.has(id)) next.delete(id)
  else next.add(id)

  expanded.value = next
}

// -- to'lov ----------------------------------------------------------

const payOpen = ref(false)
const payTarget = ref<Debt | null>(null)
const paying = ref(false)
const payError = ref('')
const payForm = reactive({ amount: '', method: 'cash', note: '', request_key: '' })

/**
 * Har ochilgan to'lov oynasi uchun bitta kalit: tugma ikki marta bosilsa
 * yoki tarmoq uzilib so'rov qayta ketsa, server pulni bir marta yozadi.
 *
 * `crypto.randomUUID` faqat HTTPS yoki localhost'da mavjud. Tizim ichki
 * tarmoqda oddiy `http://192.168...` orqali ochilsa u yo'q, shuning uchun
 * zaxira generator bor.
 */
function newRequestKey(): string {
  if (typeof crypto !== 'undefined' && 'randomUUID' in crypto) {
    return crypto.randomUUID()
  }

  return `${Date.now().toString(36)}-${Math.random().toString(36).slice(2)}-${Math.random().toString(36).slice(2)}`
}

function openPay(debt: Debt) {
  payTarget.value = debt
  payError.value = ''
  Object.assign(payForm, {
    amount: debt.remaining,
    method: 'cash',
    note: '',
    request_key: newRequestKey(),
  })
  payOpen.value = true
}

async function onPay() {
  if (!payTarget.value) return

  payError.value = ''
  paying.value = true

  try {
    await debtsApi.pay(payTarget.value.id, payForm)
    payOpen.value = false
    await load()
  } catch (err) {
    const data = (err as { response?: { data?: Record<string, unknown> } }).response?.data
    const first = data ? Object.values(data).flat()[0] : null
    payError.value = typeof first === 'string' ? first : 'To‘lovni qabul qilib bo‘lmadi.'
  } finally {
    paying.value = false
  }
}

// -- ko'rinish -------------------------------------------------------

function money(value: string | null | undefined): string {
  if (value == null) return '—'
  return new Intl.NumberFormat('uz-UZ', { maximumFractionDigits: 0 }).format(Number(value))
}

function dateTime(value: string): string {
  return new Intl.DateTimeFormat('uz-UZ', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  }).format(new Date(value))
}

const STATUS: Record<string, { label: string; tone: string }> = {
  active: { label: 'Faol', tone: 'orange' },
  overdue: { label: 'Muddati o‘tgan', tone: 'red' },
  paid: { label: 'To‘langan', tone: 'green' },
  cancelled: { label: 'Bekor qilingan', tone: 'grey' },
}
</script>

<template>
  <section class="app-section active">
    <div class="section-toolbar">
      <div class="filters">
        <div class="search-field">
          <svg><use href="#i-search" /></svg>
          <input
            v-model="filters.search"
            type="search"
            placeholder="Mijoz, telefon, hujjat raqami..."
            @input="onSearchInput"
          />
        </div>

        <select v-model="filters.status" @change="load()">
          <option value="">Barcha qarzlar</option>
          <option value="active">Faol</option>
          <option value="overdue">Muddati o‘tgan</option>
          <option value="paid">To‘langan</option>
          <option value="cancelled">Bekor qilingan</option>
        </select>

        <select v-model="filters.customer_type" @change="load()">
          <option value="">Barcha mijozlar</option>
          <option value="retail">Chakana</option>
          <option value="counterparty">Kontragentlar</option>
        </select>

        <select v-model="filters.warehouse" @change="load()">
          <option value="">Barcha omborlar</option>
          <option v-for="w in warehouses.items" :key="w.id" :value="w.id">{{ w.name }}</option>
        </select>
      </div>

      <div class="toolbar-actions">
        <button
          v-if="auth.can('print_reports')"
          class="button button-outline"
          type="button"
          :disabled="exporting"
          @click="onExport"
        >
          <svg><use href="#i-download" /></svg>
          <span>{{ exporting ? 'Tayyorlanmoqda…' : 'Excel' }}</span>
        </button>
      </div>
    </div>

    <p v-if="error" class="load-error">{{ error }}</p>
    <p v-if="exportError" class="load-error">{{ exportError }}</p>

    <div class="kpi-grid">
      <article class="kpi-card">
        <div class="kpi-icon"><svg><use href="#i-users" /></svg></div>
        <p>Faol qarzdorlar</p>
        <strong>{{ summary?.active_count ?? 0 }}</strong>
      </article>

      <article class="kpi-card">
        <div class="kpi-icon"><svg><use href="#i-sale" /></svg></div>
        <p>Faol qarz</p>
        <strong>{{ money(summary?.active_amount) }}</strong>
        <small>so‘m</small>
      </article>

      <article class="kpi-card">
        <div class="kpi-icon"><svg><use href="#i-calendar" /></svg></div>
        <p>Muddati o‘tgan</p>
        <strong :class="{ danger: (summary?.overdue_count ?? 0) > 0 }">
          {{ summary?.overdue_count ?? 0 }}
        </strong>
      </article>

      <article class="kpi-card">
        <div class="kpi-icon"><svg><use href="#i-report" /></svg></div>
        <p>Muddati o‘tgan summa</p>
        <strong :class="{ danger: Number(summary?.overdue_amount ?? 0) > 0 }">
          {{ money(summary?.overdue_amount) }}
        </strong>
        <small>so‘m</small>
      </article>

      <article class="kpi-card">
        <div class="kpi-icon"><svg><use href="#i-import" /></svg></div>
        <p>Undirilgan</p>
        <strong>{{ money(summary?.paid_amount) }}</strong>
        <small>so‘m</small>
      </article>
    </div>

    <div class="table-card">
      <div class="table-scroll">
        <table class="data-table">
          <thead>
            <tr>
              <th>Qarz</th>
              <th>Mijoz</th>
              <th>Ombor</th>
              <th>Muddati</th>
              <th class="num">Summa</th>
              <th class="num">To‘langan</th>
              <th class="num">Qoldiq</th>
              <th>Holat</th>
              <th></th>
            </tr>
          </thead>

          <tbody>
            <tr v-if="loading">
              <td colspan="9" class="empty-state">Yuklanmoqda…</td>
            </tr>

            <tr v-else-if="!items.length">
              <td colspan="9" class="empty-state">
                Qarz topilmadi. Qarzga sotuv «Sotuv» bo‘limida «Qarzga» belgisi bilan qilinadi.
              </td>
            </tr>

            <template v-for="debt in items" v-else :key="debt.id">
              <tr>
                <td>
                  <button class="expand-toggle" type="button" @click="toggle(debt.id)">
                    {{ expanded.has(debt.id) ? '−' : '+' }}
                  </button>
                  <strong>{{ debt.number }}</strong>
                  <small class="cell-sub">{{ debt.document_number }} · {{ debt.issued_date }}</small>
                </td>

                <td>
                  <strong>{{ debt.customer_name }}</strong>
                  <small class="cell-sub">
                    {{ debt.customer_phone || '—' }}
                    · {{ debt.customer_type === 'retail' ? 'chakana' : 'kontragent' }}
                  </small>
                </td>

                <td>{{ debt.warehouse_name }}</td>

                <td>
                  {{ debt.due_date }}
                  <small v-if="debt.is_overdue" class="cell-sub overdue">
                    {{ debt.overdue_days }} kun kechikdi
                  </small>
                </td>

                <td class="num">
                  {{ money(debt.amount) }}
                  <small v-if="Number(debt.markup_amount) > 0" class="cell-sub">
                    ustama {{ money(debt.markup_amount) }} ({{ Number(debt.markup_percent) }}%)
                  </small>
                </td>

                <td class="num">{{ money(debt.paid_amount) }}</td>
                <td class="num"><strong>{{ money(debt.remaining) }}</strong></td>

                <td>
                  <span class="pill" :class="`pill-${STATUS[debt.display_status]?.tone ?? 'grey'}`">
                    {{ STATUS[debt.display_status]?.label ?? debt.status_display }}
                  </span>
                </td>

                <td class="row-actions">
                  <button
                    v-if="canPay && debt.status === 'active'"
                    class="button button-gradient"
                    type="button"
                    @click="openPay(debt)"
                  >
                    To‘lov
                  </button>
                </td>
              </tr>

              <tr v-if="expanded.has(debt.id)" class="lines-row">
                <td colspan="9">
                  <table class="inner-table">
                    <thead>
                      <tr>
                        <th>Vaqt</th>
                        <th class="num">Summa</th>
                        <th>Usul</th>
                        <th>Qabul qildi</th>
                        <th>Izoh</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr v-if="!debt.payments.length">
                        <td colspan="5" class="empty-state">Hali to‘lov yo‘q.</td>
                      </tr>
                      <tr v-for="payment in debt.payments" :key="payment.id">
                        <td>{{ dateTime(payment.paid_at) }}</td>
                        <td class="num">{{ money(payment.amount) }}</td>
                        <td>{{ payment.method_display }}</td>
                        <td>{{ payment.created_by_name || '—' }}</td>
                        <td>{{ payment.note || '—' }}</td>
                      </tr>
                    </tbody>
                  </table>
                </td>
              </tr>
            </template>
          </tbody>
        </table>
      </div>
    </div>

    <!-- To'lov -->
    <div class="modal" :class="{ show: payOpen }">
      <div class="modal-backdrop" @click="payOpen = false"></div>

      <div class="modal-dialog">
        <div class="modal-header">
          <div>
            <span class="modal-eyebrow">TO‘LOV</span>
            <h3>{{ payTarget?.customer_name }}</h3>
            <p>
              {{ payTarget?.number }} · qoldiq
              <strong>{{ money(payTarget?.remaining) }} so‘m</strong>.
              Qisman to‘lov mumkin — qarz to‘liq yopilgunicha faol qoladi.
            </p>
          </div>

          <button class="modal-close" type="button" @click="payOpen = false">
            <svg><use href="#i-close" /></svg>
          </button>
        </div>

        <form @submit.prevent="onPay">
          <div class="modal-body">
            <div class="form-grid">
              <div class="field">
                <label>Summa</label>
                <input
                  v-model="payForm.amount"
                  type="number"
                  step="0.01"
                  min="0.01"
                  :max="payTarget?.remaining"
                  required
                />
              </div>

              <div class="field">
                <label>To‘lov usuli</label>
                <select v-model="payForm.method">
                  <option value="cash">Naqd</option>
                  <option value="card">Karta</option>
                  <option value="transfer">O‘tkazma</option>
                </select>
              </div>

              <div class="field span-2">
                <label>Izoh</label>
                <input v-model="payForm.note" maxlength="250" />
              </div>
            </div>

            <p v-if="payError" class="form-error">{{ payError }}</p>
          </div>

          <div class="modal-footer">
            <button class="button button-outline" type="button" @click="payOpen = false">
              Bekor qilish
            </button>

            <button class="button button-gradient" type="submit" :disabled="paying">
              {{ paying ? 'Qabul qilinmoqda…' : 'To‘lovni qabul qilish' }}
            </button>
          </div>
        </form>
      </div>
    </div>
  </section>
</template>

<style scoped>

.overdue {
  color: var(--red);
  font-weight: 600;
}

.kpi-card > strong.danger {
  color: var(--red);
}

</style>
