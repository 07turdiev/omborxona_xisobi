<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'

import { catalogApi } from '@/api/catalog'
import type { DocumentInput } from '@/api/documents'
import { useDocumentStore } from '@/stores/documents'
import { useWarehouseStore } from '@/stores/warehouses'
import type { Document, DocumentKind, DocumentLineInput, Variant } from '@/types'

const props = defineProps<{
  show: boolean
  kind: DocumentKind
  document: Document | null
}>()
const emit = defineEmits<{ close: []; saved: [] }>()

const store = useDocumentStore()
const warehouses = useWarehouseStore()

const errors = ref<Record<string, string[]>>({})
const variants = ref<Variant[]>([])

// Shtrix-kod bilan qo'shish
const scanCode = ref('')
const scanInput = ref<HTMLInputElement | null>(null)
const scanMessage = reactive({ text: '', tone: '' })
const scanning = ref(false)

const isPurchase = computed(() => props.kind === 'purchase')

/** Qator uchun tanlanishi mumkin bo'lgan o'ram birliklari.

    Bazaviy birlik ro'yxatda yo'q — u "bazaviy" varianti bilan
    (bo'sh qiymat) tanlanadi. */
function unitsFor(variantId: number | null): string[] {
  const variant = variants.value.find((v) => v.id === variantId)

  return variant ? variant.units.map((u) => u.unit) : []
}

function emptyLine(): DocumentLineInput {
  return { variant: null, quantity: '', unit_price: '', unit: '', discount_percent: '0' }
}

function emptyForm(): DocumentInput {
  return {
    kind: props.kind,
    date: new Date().toISOString().slice(0, 10),
    warehouse: null,
    partner: null,
    currency: 'UZS',
    external_number: '',
    note: '',
    items: [emptyLine()],
  }
}

const form = reactive<DocumentInput>(emptyForm())

watch(
  () => [props.show, props.document] as const,
  async ([show, document]) => {
    if (!show) return

    errors.value = {}
    Object.assign(form, emptyForm())

    if (!variants.value.length) {
      const data = await catalogApi.products()
      variants.value = data.results.flatMap((product) => product.variants)
    }

    if (document) {
      Object.assign(form, {
        kind: document.kind,
        date: document.date,
        warehouse: document.warehouse,
        partner: document.partner,
        currency: document.currency,
        external_number: document.external_number,
        note: document.note,
        items: document.lines.map((line) => ({
          variant: line.variant,
          batch: line.batch,
          unit: line.unit,
          quantity: line.quantity,
          unit_price: line.unit_price,
          discount_percent: line.discount_percent,
          note: line.note,
        })),
      })
    }
  },
  { immediate: true },
)

function addLine() {
  form.items.push(emptyLine())
}

/**
 * Shtrix-kod bo'yicha qator qo'shadi.
 *
 * Skanerlar kodni yozib, oxirida Enter yuboradi — shuning uchun forma
 * yuborilishini to'xtatib, shu funksiyani chaqiramiz. Bo'lmasa har
 * skanerlashda hujjat saqlanib ketardi.
 *
 * Bir xil mahsulot ikkinchi marta skanerlansa yangi qator qo'shilmaydi,
 * miqdor oshadi — kassada odatiy holat.
 */
async function onScan() {
  const code = scanCode.value.trim()

  if (!code) return

  scanning.value = true
  scanMessage.text = ''

  try {
    const variant = await catalogApi.byBarcode(code)

    // Ro'yxatda bo'lmasa qo'shamiz — keyingi skanerlashda topilsin
    if (!variants.value.some((v) => v.id === variant.id)) {
      variants.value = [...variants.value, variant]
    }

    const existing = form.items.find((line) => line.variant === variant.id)

    if (existing) {
      existing.quantity = String(Number(existing.quantity || 0) + 1)
      scanMessage.text = `${variant.display_name} — ${existing.quantity} ta`
    } else {
      // Bo'sh qator bo'lsa o'shanga yozamiz, aks holda yangisini qo'shamiz
      const blank = form.items.find((line) => !line.variant)
      const line = blank ?? emptyLine()

      line.variant = variant.id
      line.quantity = '1'
      line.unit = ''
      line.unit_price =
        (isPurchase.value ? variant.purchase_price : variant.sale_price) ?? ''

      if (!blank) form.items.push(line)

      scanMessage.text = `${variant.display_name} qo'shildi`
    }

    scanMessage.tone = 'ok'
  } catch (err) {
    const status = (err as { response?: { status?: number } }).response?.status

    scanMessage.text =
      status === 404
        ? `"${code}" — bunday kod topilmadi`
        : 'Qidiruvda xatolik'
    scanMessage.tone = 'error'
  } finally {
    scanning.value = false
    scanCode.value = ''
    // Keyingi skanerlash uchun fokus qaytariladi
    scanInput.value?.focus()
  }
}

function removeLine(index: number) {
  form.items.splice(index, 1)

  if (!form.items.length) addLine()
}

/** Variant tanlanganda narxni katalogdan oldindan to'ldiramiz. */
function onVariantChange(index: number) {
  const line = form.items[index]

  if (!line) return

  const variant = variants.value.find((v) => v.id === line.variant)

  if (!variant) return

  line.unit = ''
  line.unit_price = (isPurchase.value ? variant.purchase_price : variant.sale_price) ?? ''
}

/** Tanlangan o'ram bo'yicha narxni qayta hisoblaymiz. */
function onUnitChange(index: number) {
  const line = form.items[index]

  if (!line) return

  const variant = variants.value.find((v) => v.id === line.variant)

  if (!variant) return

  const base = (isPurchase.value ? variant.purchase_price : variant.sale_price) ?? '0'
  const pack = variant.units.find((u) => u.unit === line.unit)
  const factor = pack ? Number(pack.factor_to_base) : 1

  line.unit_price = String(Math.round(Number(base) * factor))
}

const lineTotal = (line: DocumentLineInput): number => {
  const discount = 1 - Number(line.discount_percent || 0) / 100
  return Number(line.quantity || 0) * Number(line.unit_price || 0) * discount
}

const total = computed(() =>
  form.items.reduce((sum, line) => sum + lineTotal(line), 0),
)

function money(value: number): string {
  return new Intl.NumberFormat('uz-UZ', { maximumFractionDigits: 0 }).format(value)
}

async function onSubmit(confirmAfter: boolean) {
  errors.value = {}

  const payload: DocumentInput = {
    ...form,
    items: form.items.filter((line) => line.variant && Number(line.quantity) > 0),
  }

  if (!payload.items.length) {
    errors.value = { items: ['Kamida bitta qator kiritilishi kerak.'] }
    return
  }

  const result = await store.save(payload, props.document?.id)

  if (!result.ok) {
    errors.value = result.errors
    return
  }

  if (confirmAfter && result.document) {
    const confirmed = await store.confirm(result.document)

    if (!confirmed.ok) {
      errors.value = confirmed.errors
      return
    }
  }

  emit('saved')
  emit('close')
}

const fieldError = (field: string): string => {
  const value = errors.value[field]

  if (Array.isArray(value)) return value[0] ?? ''

  return typeof value === 'string' ? value : ''
}
</script>

<template>
  <div class="modal" :class="{ show }">
    <div class="modal-backdrop" @click="emit('close')"></div>

    <div class="modal-dialog modal-large">
      <div class="modal-header">
        <div>
          <span class="modal-eyebrow">{{ isPurchase ? 'KIRIM' : 'SOTUV' }}</span>
          <h3>{{ isPurchase ? 'Yangi kirim' : 'Yangi sotuv' }}</h3>
          <p>
            <template v-if="isPurchase">
              Bir hujjatga bir nechta pozitsiya kiritish mumkin.
            </template>
            <template v-else>
              Tannarx va foyda tasdiqlashda avtomatik hisoblanadi.
            </template>
          </p>
        </div>

        <button class="modal-close" type="button" @click="emit('close')">
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
              <label>Ombor</label>
              <select v-model="form.warehouse" required>
                <option :value="null" disabled>Tanlang…</option>
                <option
                  v-for="w in warehouses.items"
                  :key="w.id"
                  :value="w.id"
                  :disabled="!isPurchase && !w.is_sellable"
                >
                  {{ w.name }}
                  <template v-if="!isPurchase && !w.is_sellable">
                    (sotuvga chiqmaydi)
                  </template>
                </option>
              </select>
              <small v-if="fieldError('warehouse')" class="field-error">
                {{ fieldError('warehouse') }}
              </small>
            </div>

            <div class="field">
              <label>{{ isPurchase ? 'Yetkazib beruvchi' : 'Mijoz' }}</label>
              <select v-model="form.partner">
                <option :value="null">—</option>
                <option
                  v-for="p in isPurchase ? store.suppliers : store.customers"
                  :key="p.id"
                  :value="p.id"
                >
                  {{ p.name }}
                </option>
              </select>
            </div>

            <div v-if="isPurchase" class="field">
              <label>Tashqi hujjat raqami</label>
              <input v-model="form.external_number" placeholder="BKS-2026-1180" />
            </div>

            <div class="field span-2">
              <label>Izoh</label>
              <input v-model="form.note" />
            </div>
          </div>

          <!-- Qatorlar -->
          <div class="lines-block">
            <div class="lines-head">
              <h4>Pozitsiyalar</h4>

              <div class="lines-tools">
                <div class="scan-field" :class="scanMessage.tone">
                  <svg><use href="#i-search" /></svg>

                  <input
                    ref="scanInput"
                    v-model="scanCode"
                    type="text"
                    placeholder="Shtrix-kodni skanerlang yoki kiriting"
                    autocomplete="off"
                    :disabled="scanning"
                    @keydown.enter.prevent="onScan"
                  />
                </div>

                <button class="button button-soft" type="button" @click="addLine">
                  <svg><use href="#i-plus" /></svg>
                  <span>Qator qo‘shish</span>
                </button>
              </div>
            </div>

            <p v-if="scanMessage.text" class="scan-note" :class="scanMessage.tone">
              {{ scanMessage.text }}
            </p>

            <p v-if="fieldError('items')" class="form-error">{{ fieldError('items') }}</p>

            <div class="table-scroll">
              <table class="data-table lines-table">
                <thead>
                  <tr>
                    <th>Mahsulot</th>
                    <th>Birlik</th>
                    <th class="num">Miqdor</th>
                    <th class="num">Narx</th>
                    <th class="num">Chegirma %</th>
                    <th class="num">Summa</th>
                    <th></th>
                  </tr>
                </thead>

                <tbody>
                  <tr v-for="(line, index) in form.items" :key="index">
                    <td>
                      <select v-model="line.variant" @change="onVariantChange(index)">
                        <option :value="null" disabled>Tanlang…</option>
                        <option v-for="v in variants" :key="v.id" :value="v.id">
                          {{ v.display_name }} ({{ v.sku }})
                        </option>
                      </select>
                    </td>

                    <td>
                      <select v-model="line.unit" @change="onUnitChange(index)">
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
                      <input v-model="line.unit_price" type="number" step="0.01" min="0" />
                    </td>

                    <td>
                      <input
                        v-model="line.discount_percent"
                        type="number"
                        step="0.01"
                        min="0"
                        max="100"
                      />
                    </td>

                    <td class="num line-sum">{{ money(lineTotal(line)) }}</td>

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

            <div class="lines-total">
              <span>Jami</span>
              <strong>{{ money(total) }} so‘m</strong>
            </div>
          </div>

          <p v-if="fieldError('detail')" class="form-error">{{ fieldError('detail') }}</p>
        </div>

        <div class="modal-footer">
          <button class="button button-outline" type="button" @click="emit('close')">
            Bekor qilish
          </button>

          <button class="button button-soft" type="submit" :disabled="store.saving">
            Qoralama saqlash
          </button>

          <button
            class="button button-gradient"
            type="button"
            :disabled="store.saving"
            @click="onSubmit(true)"
          >
            {{ store.saving ? 'Saqlanmoqda…' : 'Saqlash va tasdiqlash' }}
          </button>
        </div>
      </form>
    </div>
  </div>
</template>

<style scoped>
.lines-block {
  margin-top: 18px;
  padding-top: 16px;
  border-top: 1px solid var(--border);
}

.lines-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 10px;
}

.lines-tools {
  display: flex;
  gap: 8px;
  align-items: center;
}

/* Skaner maydoni — kiritish tugagach fokus shu yerda qoladi, ya'ni
   ketma-ket skanerlash uzilmaydi. */
.scan-field {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 0 10px;
  border: 1px solid var(--border-strong);
  border-radius: var(--radius-small);
  background: var(--surface);
  transition: var(--transition);
}

.scan-field svg {
  width: 12px;
  height: 12px;
  color: var(--text-muted);
  fill: none;
  stroke: currentColor;
  stroke-width: 2;
}

.scan-field input {
  width: 210px;
  border: none;
  background: none;
  padding: 7px 0;
}

.scan-field.ok {
  border-color: var(--green);
}

.scan-field.error {
  border-color: var(--red);
}

.scan-note {
  margin-bottom: 10px;
  font-size: 13px;
  font-weight: 600;
}

.scan-note.ok {
  color: var(--green);
}

.scan-note.error {
  color: var(--red);
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

.num {
  text-align: right;
}

.line-sum {
  font-weight: 700;
  white-space: nowrap;
}

.lines-total {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  align-items: baseline;
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid var(--border);
}

.lines-total span {
  color: var(--text-muted);
  font-size: 13px;
  text-transform: uppercase;
}

.lines-total strong {
  font-size: 18px;
}

.field-error {
  margin-top: 4px;
  color: var(--red);
  font-size: 12px;
}

.form-error {
  margin: 12px 0;
  padding: 10px 12px;
  border-radius: var(--radius-small);
  background: var(--red-soft);
  color: var(--red);
  font-size: 13px;
}
</style>
