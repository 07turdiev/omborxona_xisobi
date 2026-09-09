<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'

import { catalogApi } from '@/api/catalog'
import { transfersApi, type TransferInput } from '@/api/transfers'
import { useWarehouseStore } from '@/stores/warehouses'
import type { Transfer, TransferLineInput, Variant } from '@/types'

const warehouses = useWarehouseStore()

const items = ref<Transfer[]>([])
const variants = ref<Variant[]>([])
const transitOptions = ref<{ id: number; name: string; code: string }[]>([])

const loading = ref(false)
const saving = ref(false)
const error = ref('')

const filters = reactive({ status: '', warehouse: '', search: '' })
const expanded = ref<Set<number>>(new Set())

// Yaratish oynasi
const modalOpen = ref(false)
const formErrors = ref<Record<string, string[]>>({})

// Qabul qilish oynasi
const receiveOpen = ref(false)
const receiveTarget = ref<Transfer | null>(null)
const receiveAmounts = reactive<Record<number, string>>({})

function emptyLine(): TransferLineInput {
  return { variant: null, quantity: '', unit: '' }
}

function emptyForm(): TransferInput {
  return {
    date: new Date().toISOString().slice(0, 10),
    from_warehouse: null,
    to_warehouse: null,
    transit_warehouse: transitOptions.value[0]?.id ?? null,
    note: '',
    items: [emptyLine()],
  }
}

const form = reactive<TransferInput>(emptyForm())

async function load() {
  loading.value = true
  error.value = ''

  try {
    items.value = (await transfersApi.list(filters)).results
  } catch {
    error.value = 'Ko‘chirishlarni olishda xatolik.'
  } finally {
    loading.value = false
  }
}

onMounted(async () => {
  await warehouses.load()

  const [transit, products] = await Promise.all([
    transfersApi.transitWarehouses(),
    catalogApi.products(),
  ])

  transitOptions.value = transit
  variants.value = products.results.flatMap((product) => product.variants)

  await load()
})

let searchTimer: ReturnType<typeof setTimeout> | undefined

function onSearchInput() {
  clearTimeout(searchTimer)
  searchTimer = setTimeout(load, 300)
}

function toggle(id: number) {
  const next = new Set(expanded.value)
  next.has(id) ? next.delete(id) : next.add(id)
  expanded.value = next
}

function unitsFor(variantId: number | null): string[] {
  return variants.value.find((v) => v.id === variantId)?.units.map((u) => u.unit) ?? []
}

// -- yaratish --------------------------------------------------------

function openCreate() {
  formErrors.value = {}
  Object.assign(form, emptyForm())
  modalOpen.value = true
}

function addLine() {
  form.items.push(emptyLine())
}

function removeLine(index: number) {
  form.items.splice(index, 1)
  if (!form.items.length) addLine()
}

function asErrors(err: unknown): Record<string, string[]> {
  const data = (err as { response?: { data?: unknown } }).response?.data

  if (Array.isArray(data)) return { detail: data.map(String) }
  if (data && typeof data === 'object') return data as Record<string, string[]>

  return { detail: ['Kutilmagan xatolik.'] }
}

async function onSubmit(sendAfter: boolean) {
  formErrors.value = {}
  saving.value = true

  try {
    const payload: TransferInput = {
      ...form,
      items: form.items.filter((line) => line.variant && Number(line.quantity) > 0),
    }

    if (!payload.items.length) {
      formErrors.value = { items: ['Kamida bitta qator kiritilishi kerak.'] }
      return
    }

    const created = await transfersApi.create(payload)

    if (sendAfter) {
      await transfersApi.send(created.id)
    }

    modalOpen.value = false
    await load()
  } catch (err) {
    formErrors.value = asErrors(err)
  } finally {
    saving.value = false
  }
}

// -- amallar ---------------------------------------------------------

async function onSend(transfer: Transfer) {
  error.value = ''

  try {
    await transfersApi.send(transfer.id)
    await load()
  } catch (err) {
    error.value = Object.values(asErrors(err)).flat()[0] ?? 'Jo‘natib bo‘lmadi.'
  }
}

function openReceive(transfer: Transfer) {
  receiveTarget.value = transfer
  error.value = ''

  Object.keys(receiveAmounts).forEach((key) => delete receiveAmounts[Number(key)])

  for (const line of transfer.lines) {
    receiveAmounts[line.id] = line.quantity_sent
  }

  receiveOpen.value = true
}

async function onReceive() {
  if (!receiveTarget.value) return

  saving.value = true
  error.value = ''

  try {
    await transfersApi.receive(receiveTarget.value.id, { ...receiveAmounts })
    receiveOpen.value = false
    await load()
  } catch (err) {
    error.value = Object.values(asErrors(err)).flat()[0] ?? 'Qabul qilib bo‘lmadi.'
  } finally {
    saving.value = false
  }
}

async function onCancel(transfer: Transfer) {
  const message = transfer.in_transit
    ? `${transfer.number} bekor qilinsinmi? Yo‘ldagi tovar manba omborga qaytariladi.`
    : `${transfer.number} bekor qilinsinmi?`

  if (!window.confirm(message)) return

  error.value = ''

  try {
    await transfersApi.cancel(transfer.id)
    await load()
  } catch (err) {
    error.value = Object.values(asErrors(err)).flat()[0] ?? 'Bekor qilib bo‘lmadi.'
  }
}

async function onDelete(transfer: Transfer) {
  if (!window.confirm(`${transfer.number} o‘chirilsinmi?`)) return
  await transfersApi.remove(transfer.id)
  await load()
}

function number(value: string | null): string {
  if (value == null) return '—'
  return new Intl.NumberFormat('uz-UZ', { maximumFractionDigits: 3 }).format(Number(value))
}

const statusTone: Record<string, string> = {
  draft: 'grey',
  sent: 'blue',
  received: 'green',
  cancelled: 'red',
}

/** Qabul qilish oynasidagi jonli kamomad. */
const receiveShortfall = computed(() => {
  if (!receiveTarget.value) return 0

  return receiveTarget.value.lines.reduce((sum, line) => {
    const entered = Number(receiveAmounts[line.id] ?? line.quantity_sent)
    const missing = Number(line.quantity_sent) - entered

    return sum + (missing > 0 ? missing * Number(line.factor) : 0)
  }, 0)
})

const formError = (field: string): string => {
  const value = formErrors.value[field]
  return Array.isArray(value) ? (value[0] ?? '') : ''
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
            placeholder="Ko‘chirish raqami..."
            @input="onSearchInput"
          />
        </div>

        <select v-model="filters.warehouse" @change="load()">
          <option value="">Barcha omborlar</option>
          <option v-for="w in warehouses.items" :key="w.id" :value="w.id">
            {{ w.name }}
          </option>
        </select>

        <select v-model="filters.status" @change="load()">
          <option value="">Barcha holatlar</option>
          <option value="draft">Qoralama</option>
          <option value="sent">Yo‘lda</option>
          <option value="received">Qabul qilingan</option>
          <option value="cancelled">Bekor qilingan</option>
        </select>
      </div>

      <button class="button button-gradient" @click="openCreate">
        <svg><use href="#i-plus" /></svg>
        <span>Yangi ko‘chirish</span>
      </button>
    </div>

    <p v-if="error" class="load-error">{{ error }}</p>

    <div v-if="!transitOptions.length" class="notice">
      <strong>Tranzit ombor yo‘q.</strong>
      Ko‘chirish uchun vazifasi «Tranzit» bo‘lgan ombor kerak — yo‘ldagi tovar
      o‘sha yerda turadi va sotuvga chiqmaydi. Uni
      <RouterLink to="/warehouses">Omborlar</RouterLink> bo‘limida yarating.
    </div>

    <div class="table-card">
      <div class="table-scroll">
        <table class="data-table">
          <thead>
            <tr>
              <th>Hujjat</th>
              <th>Sana</th>
              <th>Qayerdan</th>
              <th>Qayerga</th>
              <th class="num">Pozitsiya</th>
              <th class="num">Kamomad</th>
              <th>Holat</th>
              <th></th>
            </tr>
          </thead>

          <tbody>
            <tr v-if="loading">
              <td colspan="8" class="empty-state">Yuklanmoqda…</td>
            </tr>

            <tr v-else-if="!items.length">
              <td colspan="8" class="empty-state">Ko‘chirish topilmadi.</td>
            </tr>

            <template v-for="transfer in items" v-else :key="transfer.id">
              <tr>
                <td>
                  <button class="expand-toggle" type="button" @click="toggle(transfer.id)">
                    {{ expanded.has(transfer.id) ? '−' : '+' }}
                  </button>
                  <strong>{{ transfer.number }}</strong>
                </td>

                <td>{{ transfer.date }}</td>
                <td>{{ transfer.from_warehouse_name }}</td>

                <td>
                  {{ transfer.to_warehouse_name }}
                  <small v-if="transfer.in_transit" class="cell-sub transit">
                    hozir: {{ transfer.transit_warehouse_name }}
                  </small>
                </td>

                <td class="num">{{ transfer.line_count }}</td>

                <td class="num">
                  <span v-if="transfer.has_shortfall" class="shortfall">
                    {{ number(transfer.total_shortfall) }}
                  </span>
                  <span v-else class="muted">—</span>
                </td>

                <td>
                  <span class="pill" :class="`pill-${statusTone[transfer.status]}`">
                    {{ transfer.status_display }}
                  </span>
                </td>

                <td class="row-actions">
                  <button
                    v-if="transfer.status === 'draft'"
                    class="button button-gradient"
                    type="button"
                    @click="onSend(transfer)"
                  >
                    Jo‘natish
                  </button>

                  <button
                    v-if="transfer.status === 'sent'"
                    class="button button-gradient"
                    type="button"
                    @click="openReceive(transfer)"
                  >
                    Qabul qilish
                  </button>

                  <button
                    v-if="transfer.status === 'draft' || transfer.status === 'sent'"
                    class="button button-outline"
                    type="button"
                    @click="onCancel(transfer)"
                  >
                    Bekor qilish
                  </button>

                  <button
                    v-if="transfer.status === 'draft'"
                    class="button button-danger"
                    type="button"
                    @click="onDelete(transfer)"
                  >
                    <svg><use href="#i-trash" /></svg>
                  </button>
                </td>
              </tr>

              <tr v-if="expanded.has(transfer.id)" class="lines-row">
                <td colspan="8">
                  <table class="inner-table">
                    <thead>
                      <tr>
                        <th>Mahsulot</th>
                        <th class="num">Jo‘natildi</th>
                        <th class="num">Qabul qilindi</th>
                        <th class="num">Kamomad</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr v-for="line in transfer.lines" :key="line.id">
                        <td>
                          {{ line.product_name }}
                          <small class="cell-sub">{{ line.sku }}</small>
                        </td>

                        <td class="num">
                          {{ number(line.quantity_sent) }} {{ line.unit }}
                          <small
                            v-if="line.unit !== line.base_unit"
                            class="cell-sub"
                          >
                            = {{ number(line.quantity_sent_base) }} {{ line.base_unit }}
                          </small>
                        </td>

                        <td class="num">
                          <span v-if="line.quantity_received != null">
                            {{ number(line.quantity_received) }} {{ line.unit }}
                          </span>
                          <span v-else class="muted">yo‘lda</span>
                        </td>

                        <td class="num">
                          <span v-if="Number(line.shortfall) > 0" class="shortfall">
                            {{ number(line.shortfall) }} {{ line.base_unit }}
                          </span>
                          <span v-else class="muted">—</span>
                        </td>
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

    <!-- Yaratish oynasi -->
    <div class="modal" :class="{ show: modalOpen }">
      <div class="modal-backdrop" @click="modalOpen = false"></div>

      <div class="modal-dialog modal-large">
        <div class="modal-header">
          <div>
            <span class="modal-eyebrow">KO‘CHIRISH</span>
            <h3>Yangi ko‘chirish</h3>
            <p>Tovar avval tranzit omborga o‘tadi, keyin qabul qilinadi.</p>
          </div>

          <button class="modal-close" type="button" @click="modalOpen = false">
            <svg><use href="#i-close" /></svg>
          </button>
        </div>

        <form @submit.prevent="onSubmit(false)">
          <div class="modal-body">
            <div class="form-grid three">
              <div class="field">
                <label>Sana</label>
                <input v-model="form.date" type="date" required />
              </div>

              <div class="field">
                <label>Qayerdan</label>
                <select v-model="form.from_warehouse" required>
                  <option :value="null" disabled>Tanlang…</option>
                  <option v-for="w in warehouses.items" :key="w.id" :value="w.id">
                    {{ w.name }}
                  </option>
                </select>
              </div>

              <div class="field">
                <label>Qayerga</label>
                <select v-model="form.to_warehouse" required>
                  <option :value="null" disabled>Tanlang…</option>
                  <option v-for="w in warehouses.items" :key="w.id" :value="w.id">
                    {{ w.name }}
                  </option>
                </select>
                <small v-if="formError('to_warehouse')" class="field-error">
                  {{ formError('to_warehouse') }}
                </small>
              </div>

              <div class="field">
                <label>Tranzit ombor</label>
                <select v-model="form.transit_warehouse" required>
                  <option :value="null" disabled>Tanlang…</option>
                  <option v-for="w in transitOptions" :key="w.id" :value="w.id">
                    {{ w.name }}
                  </option>
                </select>
                <small class="field-hint">Yo‘ldagi tovar shu yerda turadi</small>
                <small v-if="formError('transit_warehouse')" class="field-error">
                  {{ formError('transit_warehouse') }}
                </small>
              </div>

              <div class="field span-2">
                <label>Izoh</label>
                <input v-model="form.note" />
              </div>
            </div>

            <div class="lines-block">
              <div class="lines-head">
                <h4>Pozitsiyalar</h4>

                <button class="button button-soft" type="button" @click="addLine">
                  <svg><use href="#i-plus" /></svg>
                  <span>Qator qo‘shish</span>
                </button>
              </div>

              <p v-if="formError('items')" class="form-error">{{ formError('items') }}</p>

              <div class="table-scroll">
                <table class="data-table lines-table">
                  <thead>
                    <tr>
                      <th>Mahsulot</th>
                      <th>Birlik</th>
                      <th class="num">Miqdor</th>
                      <th></th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="(line, index) in form.items" :key="index">
                      <td>
                        <select v-model="line.variant">
                          <option :value="null" disabled>Tanlang…</option>
                          <option v-for="v in variants" :key="v.id" :value="v.id">
                            {{ v.display_name }} ({{ v.sku }})
                          </option>
                        </select>
                      </td>

                      <td>
                        <select v-model="line.unit">
                          <option value="">bazaviy</option>
                          <option v-for="u in unitsFor(line.variant)" :key="u" :value="u">
                            {{ u }}
                          </option>
                        </select>
                      </td>

                      <td>
                        <input v-model="line.quantity" type="number" step="0.001" min="0" />
                      </td>

                      <td>
                        <button
                          class="button button-danger"
                          type="button"
                          @click="removeLine(index)"
                        >
                          <svg><use href="#i-trash" /></svg>
                        </button>
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>

            <p v-if="formError('detail')" class="form-error">{{ formError('detail') }}</p>
          </div>

          <div class="modal-footer">
            <button class="button button-outline" type="button" @click="modalOpen = false">
              Bekor qilish
            </button>

            <button class="button button-soft" type="submit" :disabled="saving">
              Qoralama saqlash
            </button>

            <button
              class="button button-gradient"
              type="button"
              :disabled="saving"
              @click="onSubmit(true)"
            >
              {{ saving ? 'Saqlanmoqda…' : 'Saqlash va jo‘natish' }}
            </button>
          </div>
        </form>
      </div>
    </div>

    <!-- Qabul qilish oynasi -->
    <div class="modal" :class="{ show: receiveOpen }">
      <div class="modal-backdrop" @click="receiveOpen = false"></div>

      <div class="modal-dialog">
        <div class="modal-header">
          <div>
            <span class="modal-eyebrow">QABUL QILISH</span>
            <h3>{{ receiveTarget?.number }}</h3>
            <p>
              Haqiqatan yetib kelgan miqdorni kiriting. Farq kamomad sifatida
              alohida yoziladi.
            </p>
          </div>

          <button class="modal-close" type="button" @click="receiveOpen = false">
            <svg><use href="#i-close" /></svg>
          </button>
        </div>

        <div class="modal-body">
          <table class="data-table">
            <thead>
              <tr>
                <th>Mahsulot</th>
                <th class="num">Jo‘natildi</th>
                <th class="num">Qabul qilindi</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="line in receiveTarget?.lines ?? []" :key="line.id">
                <td>
                  {{ line.product_name }}
                  <small class="cell-sub">{{ line.sku }}</small>
                </td>
                <td class="num">{{ number(line.quantity_sent) }} {{ line.unit }}</td>
                <td>
                  <input
                    v-model="receiveAmounts[line.id]"
                    type="number"
                    step="0.001"
                    min="0"
                    :max="line.quantity_sent"
                  />
                </td>
              </tr>
            </tbody>
          </table>

          <p v-if="receiveShortfall > 0" class="shortfall-note">
            Kamomad: <strong>{{ number(String(receiveShortfall)) }}</strong>
            — «Yo‘lda yo‘qolgan» sababi bilan yoziladi va hisobotda
            yo‘qotish sifatida ko‘rinadi.
          </p>
        </div>

        <div class="modal-footer">
          <button class="button button-outline" type="button" @click="receiveOpen = false">
            Bekor qilish
          </button>

          <button
            class="button button-gradient"
            type="button"
            :disabled="saving"
            @click="onReceive"
          >
            {{ saving ? 'Saqlanmoqda…' : 'Qabul qilish' }}
          </button>
        </div>
      </div>
    </div>
  </section>
</template>

<style scoped>
.num {
  text-align: right;
}

.muted {
  color: var(--text-muted);
}

.shortfall {
  color: var(--red);
  font-weight: 700;
}

.transit {
  color: var(--orange);
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

.pill-blue {
  background: var(--blue-soft);
  color: var(--blue);
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

.lines-block {
  margin-top: 18px;
  padding-top: 16px;
  border-top: 1px solid var(--border);
}

.lines-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 10px;
}

.lines-head h4 {
  font-size: 14px;
  color: var(--text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.06em;
}

.lines-table input,
.lines-table select {
  min-width: 70px;
}

.lines-table td {
  padding: 6px 8px;
}

.notice {
  margin-bottom: 14px;
  padding: 12px 14px;
  border: 1px solid var(--orange);
  border-radius: var(--radius-small);
  background: var(--orange-soft);
  color: var(--text);
  font-size: 13px;
  line-height: 1.6;
}

.shortfall-note {
  margin-top: 12px;
  padding: 10px 12px;
  border-radius: var(--radius-small);
  background: var(--orange-soft);
  color: var(--orange);
  font-size: 13px;
  line-height: 1.5;
}

.field-error {
  margin-top: 4px;
  color: var(--red);
  font-size: 12px;
}

.field-hint {
  margin-top: 4px;
  color: var(--text-muted);
  font-size: 12px;
}

.form-error,
.load-error {
  margin: 12px 0;
  padding: 10px 12px;
  border-radius: var(--radius-small);
  background: var(--red-soft);
  color: var(--red);
  font-size: 13px;
}

.load-error {
  margin: 0 0 14px;
}
</style>
