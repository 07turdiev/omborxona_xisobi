<script setup lang="ts">
import { onMounted, reactive, ref, watch } from 'vue'

import { catalogApi } from '@/api/catalog'
import type { Barcode, ProductUnit, Variant } from '@/types'

/**
 * Variantning shtrix-kodlari va o'ram birliklari.
 *
 * Alohida komponent, chunki ikkalasi ham **variantga** tegishli, mahsulotga
 * emas: kiyimda har o'lcham-rang juftligining o'z shtrix-kodi bo'ladi.
 *
 * Ular mahsulot saqlangandan **keyin** qo'shiladi — yangi mahsulotda
 * variant hali mavjud emas.
 */
const props = defineProps<{ variant: Variant | null; baseUnit: string }>()

const units = ref<ProductUnit[]>([])
const barcodes = ref<Barcode[]>([])

const error = ref('')
const saving = ref(false)

const unitForm = reactive({ unit: '', factor_to_base: '' })
const barcodeForm = reactive({ code: '', code_type: 'ean13' })

const codeTypes = [
  { value: 'ean13', label: 'EAN-13' },
  { value: 'ean8', label: 'EAN-8' },
  { value: 'code128', label: 'Code 128' },
  { value: 'internal', label: 'Ichki kod' },
  { value: 'other', label: 'Boshqa' },
]

function load() {
  if (!props.variant) {
    units.value = []
    barcodes.value = []
    return
  }

  units.value = props.variant.units ?? []
  barcodes.value = props.variant.barcodes ?? []
}

onMounted(load)
watch(() => props.variant, load)

function asMessage(err: unknown, fallback: string): string {
  const data = (err as { response?: { data?: Record<string, string[]> } }).response?.data

  return Object.values(data ?? {}).flat()[0] ?? fallback
}

async function refresh() {
  if (!props.variant) return

  const fresh = await catalogApi.variant(props.variant.id)
  units.value = fresh.units
  barcodes.value = fresh.barcodes
}

async function onAddUnit() {
  if (!props.variant || !unitForm.unit || !unitForm.factor_to_base) return

  error.value = ''
  saving.value = true

  try {
    await catalogApi.createProductUnit({
      variant: props.variant.id,
      unit: unitForm.unit.trim(),
      factor_to_base: unitForm.factor_to_base,
    })

    unitForm.unit = ''
    unitForm.factor_to_base = ''
    await refresh()
  } catch (err) {
    error.value = asMessage(err, 'O‘ram qo‘shilmadi.')
  } finally {
    saving.value = false
  }
}

async function onRemoveUnit(unit: ProductUnit) {
  await catalogApi.removeProductUnit(unit.id)
  await refresh()
}

async function onAddBarcode() {
  if (!props.variant || !barcodeForm.code) return

  error.value = ''
  saving.value = true

  try {
    await catalogApi.createBarcode({
      variant: props.variant.id,
      code: barcodeForm.code.trim(),
      code_type: barcodeForm.code_type,
    })

    barcodeForm.code = ''
    await refresh()
  } catch (err) {
    error.value = asMessage(err, 'Kod qo‘shilmadi — u boshqa mahsulotga biriktirilgan bo‘lishi mumkin.')
  } finally {
    saving.value = false
  }
}

async function onRemoveBarcode(barcode: Barcode) {
  await catalogApi.removeBarcode(barcode.id)
  await refresh()
}
</script>

<template>
  <div v-if="variant" class="extras">
    <p v-if="error" class="form-error">{{ error }}</p>

    <!-- O'ram birliklari -->
    <div class="block">
      <h4>O‘ram birliklari</h4>

      <p class="hint">
        «1 qop = 50 kg» kabi konversiya. U <strong>mahsulotga bog‘liq</strong>:
        sement qopi 50 kg, gips qopi 30 kg — shuning uchun umumiy birliklar
        ro‘yxatida bo‘lolmaydi. Kirim va sotuvda shu birliklarda kiritish
        mumkin bo‘ladi.
      </p>

      <table class="mini-table">
        <thead>
          <tr>
            <th>Birlik</th>
            <th class="num">1 birlik = ? {{ baseUnit || 'bazaviy' }}</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="!units.length">
            <td colspan="3" class="empty">O‘ram qo‘shilmagan</td>
          </tr>

          <tr v-for="unit in units" :key="unit.id">
            <td><strong>{{ unit.unit }}</strong></td>
            <td class="num">{{ Number(unit.factor_to_base) }}</td>
            <td class="actions">
              <button class="button button-danger" type="button" @click="onRemoveUnit(unit)">
                <svg><use href="#i-trash" /></svg>
              </button>
            </td>
          </tr>
        </tbody>
      </table>

      <div class="add-row">
        <input v-model="unitForm.unit" placeholder="qop" />
        <input
          v-model="unitForm.factor_to_base"
          type="number"
          step="0.000001"
          min="0"
          placeholder="50"
        />
        <button
          class="button button-soft"
          type="button"
          :disabled="saving || !unitForm.unit || !unitForm.factor_to_base"
          @click="onAddUnit"
        >
          Qo‘shish
        </button>
      </div>
    </div>

    <!-- Shtrix-kodlar -->
    <div class="block">
      <h4>Shtrix-kodlar</h4>

      <p class="hint">
        Bir mahsulotga <strong>bir nechta kod</strong> biriktirish mumkin —
        eski va yangi qadoq, yetkazib beruvchi kodi, ichki kod. Qidiruvda
        bo‘shliq va registr farqi hisobga olinmaydi.
      </p>

      <table class="mini-table">
        <thead>
          <tr>
            <th>Kod</th>
            <th>Turi</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="!barcodes.length">
            <td colspan="3" class="empty">Kod biriktirilmagan</td>
          </tr>

          <tr v-for="barcode in barcodes" :key="barcode.id">
            <td><code>{{ barcode.code }}</code></td>
            <td>{{ codeTypes.find((t) => t.value === barcode.code_type)?.label ?? '—' }}</td>
            <td class="actions">
              <button
                class="button button-danger"
                type="button"
                @click="onRemoveBarcode(barcode)"
              >
                <svg><use href="#i-trash" /></svg>
              </button>
            </td>
          </tr>
        </tbody>
      </table>

      <div class="add-row">
        <input v-model="barcodeForm.code" placeholder="4780123456789" />
        <select v-model="barcodeForm.code_type">
          <option v-for="type in codeTypes" :key="type.value" :value="type.value">
            {{ type.label }}
          </option>
        </select>
        <button
          class="button button-soft"
          type="button"
          :disabled="saving || !barcodeForm.code"
          @click="onAddBarcode"
        >
          Qo‘shish
        </button>
      </div>
    </div>
  </div>

  <p v-else class="hint">
    O‘ram birliklari va shtrix-kodlar mahsulot saqlangandan keyin
    qo‘shiladi.
  </p>
</template>

<style scoped>
.extras {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 18px;
}

.block h4 {
  margin-bottom: 8px;
  font-size: 14px;
  color: var(--text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.06em;
}

.hint {
  margin-bottom: 10px;
  color: var(--text-muted);
  font-size: 12px;
  line-height: 1.6;
}

.mini-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}

.mini-table th {
  padding: 5px 7px;
  border-bottom: 1px solid var(--border);
  color: var(--text-muted);
  font-size: 12px;
  letter-spacing: 0.05em;
  text-align: left;
}

.mini-table th.num {
  text-align: right;
}

.mini-table td {
  padding: 5px 7px;
  border-bottom: 1px solid var(--border);
}

.num {
  text-align: right;
}

.empty {
  color: var(--text-muted);
  text-align: center;
  font-size: 12px;
}

.actions {
  width: 34px;
  text-align: right;
}

.add-row {
  display: flex;
  gap: 6px;
  margin-top: 10px;
}

.add-row input,
.add-row select {
  min-width: 0;
}

code {
  padding: 1px 5px;
  border-radius: var(--radius);
  background: var(--surface-hover);
  font-size: 12px;
}

.form-error {
  grid-column: 1 / -1;
  padding: 8px 12px;
  border-radius: var(--radius-small);
  background: var(--red-soft);
  color: var(--red);
  font-size: 13px;
}
</style>
