<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'

import DocumentModal from '@/components/DocumentModal.vue'
import DocumentPrint from '@/components/DocumentPrint.vue'
import { documentsApi } from '@/api/documents'
import { tenantsApi } from '@/api/tenants'
import { useExport } from '@/composables/useExport'
import { useDocumentStore } from '@/stores/documents'
import { useWarehouseStore } from '@/stores/warehouses'
import type { Document, DocumentKind, TenantSettings } from '@/types'

const route = useRoute()
const store = useDocumentStore()
const warehouses = useWarehouseStore()

const kind = computed(() => (route.meta.documentKind as DocumentKind) ?? 'purchase')
const isPurchase = computed(() => kind.value === 'purchase')

const modalOpen = ref(false)
const editing = ref<Document | null>(null)

// Turi sahifadan olinadi: kirim sahifasida sotuvlar chiqmasligi kerak
const { exporting, exportError, onExport } = useExport(() =>
  documentsApi.exportExcel({ ...store.filters, kind: kind.value }),
)

// Chop etish
const printOpen = ref(false)
const printTarget = ref<Document | null>(null)
const settings = ref<TenantSettings | null>(null)
const expanded = ref<Set<number>>(new Set())
const actionError = ref('')

onMounted(async () => {
  await Promise.all([warehouses.load(), store.loadPartners()])
  await store.load(kind.value)

  // Rekvizitlar chop etiladigan hujjat sarlavhasida chiqadi
  try {
    settings.value = await tenantsApi.settings()
  } catch {
    // Sozlamalarni o'qish huquqi bo'lmasa ham chop etish ishlayveradi
  }
})

// Kirim ↔ sotuv o'tishda ro'yxat qayta yuklanadi
watch(kind, (value) => store.load(value))

let searchTimer: ReturnType<typeof setTimeout> | undefined

function onSearchInput() {
  clearTimeout(searchTimer)
  searchTimer = setTimeout(() => store.load(kind.value), 300)
}

function openCreate() {
  editing.value = null
  actionError.value = ''
  modalOpen.value = true
}

function openEdit(document: Document) {
  editing.value = document
  actionError.value = ''
  modalOpen.value = true
}

function openPrint(document: Document) {
  printTarget.value = document
  printOpen.value = true
}

function toggle(id: number) {
  const next = new Set(expanded.value)
  next.has(id) ? next.delete(id) : next.add(id)
  expanded.value = next
}

/** Server xatosini foydalanuvchiga ko'rsatiladigan matnga aylantiradi. */
function firstMessage(errors: Record<string, string[]>, fallback: string): string {
  const detail = errors.detail

  if (Array.isArray(detail) && detail.length) return detail[0] ?? fallback

  const first = Object.values(errors).flat()[0]

  return first ?? fallback
}

async function onConfirm(document: Document) {
  actionError.value = ''
  const result = await store.confirm(document)

  if (!result.ok) {
    actionError.value = firstMessage(result.errors, 'Tasdiqlab bo‘lmadi.')
  }
}

async function onCancel(document: Document) {
  const message =
    document.status === 'confirmed'
      ? `${document.number} bekor qilinsinmi? Qoldiq teskari yozuv bilan qaytariladi.`
      : `${document.number} bekor qilinsinmi?`

  if (!window.confirm(message)) return

  actionError.value = ''
  const result = await store.cancel(document)

  if (!result.ok) {
    actionError.value = firstMessage(result.errors, 'Bekor qilib bo‘lmadi.')
  }
}

async function onDelete(document: Document) {
  if (!window.confirm(`${document.number} o‘chirilsinmi?`)) return
  await store.remove(document)
}

function money(value: string | null | undefined): string {
  if (value == null) return '—'
  return new Intl.NumberFormat('uz-UZ', { maximumFractionDigits: 0 }).format(Number(value))
}

function number(value: string): string {
  return new Intl.NumberFormat('uz-UZ', { maximumFractionDigits: 3 }).format(Number(value))
}

const statusTone: Record<string, string> = {
  draft: 'grey',
  confirmed: 'green',
  cancelled: 'red',
}

const totals = computed(() =>
  isPurchase.value ? store.summary?.purchases : store.summary?.sales,
)
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
            placeholder="Hujjat raqami yoki kontragent..."
            @input="onSearchInput"
          />
        </div>

        <select v-model="store.filters.warehouse" @change="store.load(kind)">
          <option value="">Barcha omborlar</option>
          <option v-for="w in warehouses.items" :key="w.id" :value="w.id">
            {{ w.name }}
          </option>
        </select>

        <select v-model="store.filters.status" @change="store.load(kind)">
          <option value="">Barcha holatlar</option>
          <option value="draft">Qoralama</option>
          <option value="confirmed">Tasdiqlangan</option>
          <option value="cancelled">Bekor qilingan</option>
        </select>
      </div>

      <div class="toolbar-actions">
        <button
          class="button button-outline"
          type="button"
          :disabled="exporting"
          @click="onExport"
        >
          <svg><use href="#i-download" /></svg>
          <span>{{ exporting ? 'Tayyorlanmoqda…' : 'Excel' }}</span>
        </button>

        <button class="button button-gradient" @click="openCreate">
          <svg><use href="#i-plus" /></svg>
          <span>{{ isPurchase ? 'Yangi kirim' : 'Yangi sotuv' }}</span>
        </button>
      </div>
    </div>

    <p v-if="store.error" class="load-error">{{ store.error }}</p>
    <p v-if="actionError" class="load-error">{{ actionError }}</p>
    <p v-if="exportError" class="load-error">{{ exportError }}</p>

    <div class="kpi-grid">
      <article class="kpi-card kpi-purple">
        <div class="kpi-icon">
          <svg><use :href="isPurchase ? '#i-import' : '#i-sale'" /></svg>
        </div>
        <p>Tasdiqlangan hujjatlar</p>
        <strong>{{ totals?.count ?? 0 }}</strong>
      </article>

      <article class="kpi-card kpi-blue">
        <div class="kpi-icon"><svg><use href="#i-report" /></svg></div>
        <p>{{ isPurchase ? 'Xarid summasi' : 'Tushum' }}</p>
        <strong>{{ money(totals?.amount) }}</strong>
        <small>so‘m</small>
      </article>

      <article v-if="!isPurchase" class="kpi-card kpi-orange">
        <div class="kpi-icon"><svg><use href="#i-stock" /></svg></div>
        <p>Tannarx (FIFO)</p>
        <strong>{{ money(totals?.cost) }}</strong>
        <small>so‘m</small>
      </article>

      <article v-if="!isPurchase" class="kpi-card kpi-green">
        <div class="kpi-icon"><svg><use href="#i-report" /></svg></div>
        <p>Foyda</p>
        <strong>{{ money(totals?.profit) }}</strong>
        <small>{{ store.summary?.margin_percent ?? 0 }}%</small>
      </article>
    </div>

    <div class="table-card">
      <div class="table-scroll">
        <table class="data-table">
          <thead>
            <tr>
              <th>Hujjat</th>
              <th>Sana</th>
              <th>Ombor</th>
              <th>{{ isPurchase ? 'Yetkazib beruvchi' : 'Mijoz' }}</th>
              <th class="num">Pozitsiya</th>
              <th class="num">Summa</th>
              <th v-if="!isPurchase" class="num">Foyda</th>
              <th>Holat</th>
              <th></th>
            </tr>
          </thead>

          <tbody>
            <tr v-if="store.loading">
              <td :colspan="isPurchase ? 8 : 9" class="empty-state">Yuklanmoqda…</td>
            </tr>

            <tr v-else-if="store.isEmpty">
              <td :colspan="isPurchase ? 8 : 9" class="empty-state">
                Hujjat topilmadi.
              </td>
            </tr>

            <template v-for="document in store.items" v-else :key="document.id">
              <tr>
                <td>
                  <button class="expand-toggle" type="button" @click="toggle(document.id)">
                    {{ expanded.has(document.id) ? '−' : '+' }}
                  </button>

                  <strong>{{ document.number }}</strong>

                  <small v-if="document.external_number" class="cell-sub">
                    {{ document.external_number }}
                  </small>
                </td>

                <td>{{ document.date }}</td>
                <td>{{ document.warehouse_name }}</td>
                <td>{{ document.partner_name || '—' }}</td>
                <td class="num">{{ document.line_count }}</td>
                <td class="num"><strong>{{ money(document.total_amount) }}</strong></td>

                <td v-if="!isPurchase" class="num">
                  <span v-if="document.status === 'confirmed'" class="profit">
                    {{ money(document.profit) }}
                  </span>
                  <span v-else class="muted">—</span>
                </td>

                <td>
                  <span class="pill" :class="`pill-${statusTone[document.status]}`">
                    {{ document.status_display }}
                  </span>
                </td>

                <td class="row-actions">
                  <button
                    v-if="document.status === 'draft'"
                    class="button button-gradient"
                    type="button"
                    :disabled="store.saving"
                    @click="onConfirm(document)"
                  >
                    Tasdiqlash
                  </button>

                  <button
                    v-if="document.is_editable"
                    class="button button-soft"
                    type="button"
                    @click="openEdit(document)"
                  >
                    Tahrirlash
                  </button>

                  <button
                    class="button button-outline"
                    type="button"
                    title="Chop etish"
                    @click="openPrint(document)"
                  >
                    <svg><use href="#i-print" /></svg>
                  </button>

                  <button
                    v-if="document.status !== 'cancelled'"
                    class="button button-outline"
                    type="button"
                    @click="onCancel(document)"
                  >
                    Bekor qilish
                  </button>

                  <button
                    v-if="document.status === 'draft'"
                    class="button button-danger"
                    type="button"
                    @click="onDelete(document)"
                  >
                    <svg><use href="#i-trash" /></svg>
                  </button>
                </td>
              </tr>

              <tr v-if="expanded.has(document.id)" class="lines-row">
                <td :colspan="isPurchase ? 8 : 9">
                  <table class="inner-table">
                    <thead>
                      <tr>
                        <th>Mahsulot</th>
                        <th class="num">Miqdor</th>
                        <th class="num">Bazaviy</th>
                        <th class="num">Narx</th>
                        <th class="num">Summa</th>
                        <th v-if="!isPurchase" class="num">Tannarx</th>
                      </tr>
                    </thead>

                    <tbody>
                      <tr v-for="line in document.lines" :key="line.id">
                        <td>
                          {{ line.product_name }}
                          <small class="cell-sub">{{ line.sku }}</small>
                        </td>

                        <td class="num">{{ number(line.quantity) }} {{ line.unit }}</td>

                        <td class="num">
                          <span
                            :class="{ muted: line.unit === line.base_unit }"
                            :title="`1 ${line.unit} = ${number(line.factor)} ${line.base_unit}`"
                          >
                            {{ number(line.quantity_base) }} {{ line.base_unit }}
                          </span>
                        </td>

                        <td class="num">{{ money(line.unit_price) }}</td>
                        <td class="num">{{ money(line.line_total) }}</td>
                        <td v-if="!isPurchase" class="num">{{ money(line.line_cost) }}</td>
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

    <DocumentModal
      :show="modalOpen"
      :kind="kind"
      :document="editing"
      @close="modalOpen = false"
      @saved="store.load(kind)"
    />

    <DocumentPrint
      :show="printOpen"
      :document="printTarget"
      :settings="settings"
      @close="printOpen = false"
    />
  </section>
</template>

<style scoped>
.toolbar-actions {
  display: flex;
  gap: 8px;
}
.num {
  text-align: right;
}

.muted {
  color: var(--text-muted);
}

.profit {
  color: var(--green);
  font-weight: 700;
}

.cell-sub {
  display: block;
  margin-top: 2px;
  color: var(--text-muted);
  font-size: 12px;
}

.expand-toggle {
  width: 16px;
  height: 16px;
  margin-right: 6px;
  border: 1px solid var(--border-strong);
  border-radius: var(--radius);
  background: var(--surface);
  color: var(--text-secondary);
  font-size: 14px;
  line-height: 1;
  cursor: pointer;
}

.lines-row > td {
  padding: 0 12px 12px 34px;
  background: var(--surface-soft);
}

.inner-table {
  width: 100%;
  border-collapse: collapse;
}

.inner-table th {
  padding: 6px 8px;
  color: var(--text-muted);
  font-size: 12px;
  letter-spacing: 0.05em;
  text-align: left;
}

.inner-table th.num {
  text-align: right;
}

.inner-table td {
  padding: 6px 8px;
  border-top: 1px solid var(--border);
  font-size: 13px;
}

.pill {
  display: inline-block;
  padding: 4px 9px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 700;
}

.pill-grey {
  background: var(--surface-hover);
  color: var(--text-secondary);
}

.pill-green {
  background: var(--green-soft);
  color: var(--green);
}

.pill-red {
  background: var(--red-soft);
  color: var(--red);
}

.row-actions {
  display: flex;
  gap: 6px;
  justify-content: flex-end;
  flex-wrap: wrap;
}

.load-error {
  margin-bottom: 14px;
  padding: 10px 12px;
  border-radius: var(--radius-small);
  background: var(--red-soft);
  color: var(--red);
  font-size: 13px;
}
</style>
