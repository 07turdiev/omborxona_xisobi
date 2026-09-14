<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'

import { historyApi } from '@/api/history'
import { tenantsApi } from '@/api/tenants'
import { useWarehouseStore } from '@/stores/warehouses'
import type { AuditEventRow, HistoryMeta, MembershipRow } from '@/types'

const warehouses = useWarehouseStore()

const items = ref<AuditEventRow[]>([])
const meta = ref<HistoryMeta | null>(null)
const members = ref<MembershipRow[]>([])

const loading = ref(false)
const loadingMore = ref(false)
const error = ref('')
const nextPage = ref<number | null>(null)
const expanded = ref<Set<number>>(new Set())

const filters = reactive({
  search: '',
  object_type: '',
  action: '',
  warehouse: '',
  user: '',
  date_from: '',
  date_to: '',
})

/** Egasi va menejer — barcha xodimlarning amallari, qolganlar — faqat o'ziniki */
const seesAll = computed(() => meta.value?.scope === 'all')
const colCount = computed(() => (seesAll.value ? 6 : 5))

async function load(page = 1) {
  if (page === 1) loading.value = true
  else loadingMore.value = true

  error.value = ''

  try {
    const data = await historyApi.list({ ...filters, page })

    items.value = page === 1 ? data.results : [...items.value, ...data.results]
    nextPage.value = data.next ? page + 1 : null
  } catch {
    error.value = 'Tarixni olishda xatolik.'
  } finally {
    loading.value = false
    loadingMore.value = false
  }
}

onMounted(async () => {
  meta.value = await historyApi.meta()

  const jobs: Promise<unknown>[] = [load(), warehouses.load()]

  if (seesAll.value) {
    jobs.push(tenantsApi.members().then((data) => (members.value = data.results)))
  }

  await Promise.all(jobs)
})

let searchTimer: ReturnType<typeof setTimeout> | undefined

function onSearchInput() {
  clearTimeout(searchTimer)
  searchTimer = setTimeout(() => load(), 300)
}

function toggle(id: number) {
  const next = new Set(expanded.value)

  if (next.has(id)) next.delete(id)
  else next.add(id)

  expanded.value = next
}

function time(value: string): string {
  return new Intl.DateTimeFormat('uz-UZ', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  }).format(new Date(value))
}

/** O'zgarish qiymati. `null` juftlik — ruxsatsiz moliyaviy maydon. */
function changeText(pair: [unknown, unknown] | null): string {
  if (pair === null) return 'yashirin'

  const show = (value: unknown) =>
    value === null || value === '' ? '—' : Array.isArray(value) ? value.join(', ') : String(value)

  return `${show(pair[0])} → ${show(pair[1])}`
}

const ACTION_TONE: Record<string, string> = {
  create: 'green',
  confirm: 'teal',
  receive: 'teal',
  payment: 'teal',
  update: 'blue',
  delete: 'red',
  cancel: 'red',
}
</script>

<template>
  <section class="app-section active">
    <div v-if="meta" class="notice">
      <template v-if="seesAll">
        <strong>To‘liq tarix.</strong> Barcha xodimlarning amallari ko‘rinadi.
      </template>
      <template v-else>
        <strong>Sizning amallaringiz.</strong> Boshqa xodimlarning amallarini
        tashkilot egasi va menejer ko‘radi.
      </template>
    </div>

    <div class="section-toolbar">
      <div class="filters">
        <div class="search-field">
          <svg><use href="#i-search" /></svg>
          <input
            v-model="filters.search"
            type="search"
            placeholder="Hujjat, obyekt yoki xodim..."
            @input="onSearchInput"
          />
        </div>

        <select v-model="filters.object_type" @change="load()">
          <option value="">Barcha bo‘limlar</option>
          <option v-for="item in meta?.object_types" :key="item.value" :value="item.value">
            {{ item.label }}
          </option>
        </select>

        <select v-model="filters.action" @change="load()">
          <option value="">Barcha amallar</option>
          <option v-for="item in meta?.actions" :key="item.value" :value="item.value">
            {{ item.label }}
          </option>
        </select>

        <select v-model="filters.warehouse" @change="load()">
          <option value="">Barcha omborlar</option>
          <option v-for="w in warehouses.items" :key="w.id" :value="w.id">{{ w.name }}</option>
        </select>

        <select v-if="seesAll" v-model="filters.user" @change="load()">
          <option value="">Barcha xodimlar</option>
          <option v-for="m in members" :key="m.user" :value="m.user">{{ m.full_name }}</option>
        </select>

        <input v-model="filters.date_from" type="date" @change="load()" />
        <input v-model="filters.date_to" type="date" @change="load()" />
      </div>
    </div>

    <p v-if="error" class="load-error">{{ error }}</p>

    <div class="table-card">
      <div class="table-scroll">
        <table class="data-table">
          <thead>
            <tr>
              <th>Sana va vaqt</th>
              <th>Amal</th>
              <th>Obyekt</th>
              <th>Ombor</th>
              <th v-if="seesAll">Xodim</th>
              <th>Tafsilot</th>
            </tr>
          </thead>

          <tbody>
            <tr v-if="loading">
              <td :colspan="colCount" class="empty-state">Yuklanmoqda…</td>
            </tr>

            <tr v-else-if="!items.length">
              <td :colspan="colCount" class="empty-state">Bu filtrlar bo‘yicha amal topilmadi.</td>
            </tr>

            <template v-for="row in items" v-else :key="row.id">
              <tr>
                <td class="nowrap">{{ time(row.created_at) }}</td>

                <td>
                  <span class="pill" :class="`pill-${ACTION_TONE[row.action] ?? 'blue'}`">
                    {{ row.action_display }}
                  </span>
                  <small class="cell-sub">{{ row.object_type_display }}</small>
                </td>

                <td><strong>{{ row.object_repr || '—' }}</strong></td>
                <td>{{ row.warehouse_name || '—' }}</td>
                <td v-if="seesAll">{{ row.user_name || '—' }}</td>

                <td>
                  <span v-if="row.details">{{ row.details }}</span>

                  <button
                    v-if="Object.keys(row.changes).length"
                    class="access-link"
                    type="button"
                    @click="toggle(row.id)"
                  >
                    {{ Object.keys(row.changes).length }} ta o‘zgarish
                  </button>

                  <span v-if="!row.details && !Object.keys(row.changes).length" class="muted">—</span>
                </td>
              </tr>

              <tr v-if="expanded.has(row.id)" class="lines-row">
                <td :colspan="colCount">
                  <table class="inner-table">
                    <thead>
                      <tr>
                        <th>Maydon</th>
                        <th>Eski → yangi</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr v-for="(pair, field) in row.changes" :key="field">
                        <td>{{ field }}</td>
                        <td :class="{ muted: pair === null }">{{ changeText(pair) }}</td>
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

    <div v-if="nextPage" class="load-more">
      <button class="button button-outline" type="button" :disabled="loadingMore" @click="load(nextPage)">
        {{ loadingMore ? 'Yuklanmoqda…' : 'Ko‘proq ko‘rsatish' }}
      </button>
    </div>
  </section>
</template>

<style scoped>

.notice {
  margin-bottom: 12px;
}

.nowrap {
  white-space: nowrap;
}

.access-link {
  margin-left: 6px;
  border: none;
  background: none;
  cursor: pointer;
  font-size: 13px;
  text-decoration: underline;
}

.load-more {
  margin-top: 12px;
  display: flex;
  justify-content: center;
}

</style>
