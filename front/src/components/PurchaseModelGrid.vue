<script setup lang="ts">
import { computed, nextTick, onMounted, ref, watch } from 'vue'

import AmountField from '@/components/AmountField.vue'
import { catalogApi } from '@/api/catalog'
import { errorMessage } from '@/api/client'
import { useAuthStore } from '@/stores/auth'
import { formatMoney, formatSum, suggestPrice } from '@/utils/money'
import {
  gridCell,
  gridColors,
  gridSizes,
  lineCost,
  modelTotal,
  modelUnits,
  orderAxis,
  type DraftModel,
} from '@/utils/receiving'
import type { Color, Size } from '@/types'

/**
 * Modelni qabul qilish katakchasi: ustunlar — o'lcham, qatorlar — rang.
 *
 * Do'konga tovar qutida, o'lchamlari aralash keladi. Kassir qutini
 * ochib, har o'lchamdan nechta borligini shu katakchaga yozadi —
 * Tab bilan katakdan katakka o'tadi, bo'sh katak "kelmagan" degani.
 *
 * Tannarx modelga bitta: bir kirimda bir model odatda bir narxda
 * keladi. Kerak bo'lsa alohida qatorga boshqa narx yoziladi.
 *
 * Model yangi o'lchamda yoki rangda kelishi mumkin (ko'k M va L edi,
 * qizil XL keldi). Shuning uchun katakchadan chiqmasdan variant
 * qo'shiladi: bo'sh katakdagi «+» yoki «O'lcham yoki rang» tugmasi.
 * Faqat o'sha juftlik yaratiladi — matritsa emas.
 */

const props = defineProps<{ model: DraftModel }>()

const emit = defineEmits<{ remove: [] }>()

const auth = useAuthStore()

/**
 * Katakcha ota komponentning modelini bevosita to'ldiradi: kiritilgan
 * son darhol pastdagi «Jami» ga tushadi, «Tayyor» bosish shart emas.
 */
const model = computed(() => props.model)

const overridesOpen = ref(Object.keys(props.model.overrides).length > 0)
const root = ref<HTMLElement | null>(null)

/** Do'kondagi hamma o'lcham va rang — yangi juftlik tanlash uchun */
const shopSizes = ref<Size[]>([])
const shopColors = ref<Color[]>([])

const pickerOpen = ref(false)
const pickedSize = ref<number | null>(null)
const pickedColor = ref<number | null>(null)
const adding = ref(false)
const error = ref('')

const sizes = computed(() => orderAxis(gridSizes(model.value.variants), shopSizes.value))
const colors = computed(() => orderAxis(gridColors(model.value.variants), shopColors.value))

/** Modelda o'lcham (yoki rang) ishlatilsa, yangi juftlikda ham kerak */
const needsSize = computed(() => sizes.value.some((size) => size.id !== null))
const needsColor = computed(() => colors.value.some((color) => color.id !== null))

const canAdd = computed(() => {
  if (needsSize.value && pickedSize.value === null) return false
  if (needsColor.value && pickedColor.value === null) return false

  return pickedSize.value !== null || pickedColor.value !== null
})

const units = computed(() => modelUnits(model.value))
const total = computed(() => modelTotal(model.value))

/** Yaxlitlash qadami sozlamadan: standart 1 000 so'm */
const step = computed(() => auth.shop?.price_rounding_step ?? 1000)

/** To'ldirilgan katakchalar — alohida tannarx uchun */
const filled = computed(() =>
  model.value.variants
    .filter((variant) => (model.value.quantities[variant.id] ?? 0) > 0)
    .map((variant) => ({
      variant,
      quantity: model.value.quantities[variant.id] ?? 0,
      cost: lineCost(model.value, variant.id),
    })),
)

// Ustama yozilganda sotuv narxi taklif qilinadi. Foydalanuvchi keyin
// uni qo'lda tuzatishi mumkin — keyingi o'zgarish yana taklif beradi.
watch(
  () => [model.value.cost, model.value.markup],
  () => {
    if (!model.value.markup.trim() || !model.value.cost.trim()) return

    // Bo'sh joy bilan: maydonga "54000.00" emas, "54 000" yoziladi —
    // yuborishdan oldin baribir tozalanadi (`normalizeMoneyInput`)
    model.value.newPrice = formatMoney(
      suggestPrice(model.value.cost, model.value.markup, step.value),
    )
  },
)

function quantity(variantId: number): number | '' {
  return model.value.quantities[variantId] || ''
}

function setQuantity(variantId: number, raw: string) {
  const value = Number.parseInt(raw, 10)

  if (!raw.trim() || Number.isNaN(value) || value <= 0) {
    delete model.value.quantities[variantId]
    delete model.value.overrides[variantId]
    return
  }

  model.value.quantities[variantId] = value
}

function setOverride(variantId: number, raw: string) {
  if (!raw.trim()) delete model.value.overrides[variantId]
  else model.value.overrides[variantId] = raw
}

/** Yangi katakka fokus: qo'shilgan zahoti son yoziladi */
async function focusCell(variantId: number) {
  await nextTick()

  const cell = root.value?.querySelector<HTMLInputElement>(`[data-variant="${variantId}"]`)

  cell?.focus()
  cell?.select()
}

/**
 * Shu o'lcham × rang juftligi uchun bitta variant yaratadi.
 *
 * Server idempotent: juftlik bo'lsa, borini qaytaradi. Shuning uchun
 * ikki marta bosilsa ham ikkinchi shtrix-kod chiqmaydi.
 */
async function addVariant(size: number | null, color: number | null) {
  if (adding.value) return

  adding.value = true
  error.value = ''

  try {
    const variant = await catalogApi.addVariant(model.value.product, { size, color })

    if (!model.value.variants.some((item) => item.id === variant.id)) {
      model.value.variants.push(variant)
    }

    pickerOpen.value = false
    pickedSize.value = null
    pickedColor.value = null

    await focusCell(variant.id)
  } catch (err) {
    error.value = errorMessage(err, 'Variant qo‘shib bo‘lmadi.')
  } finally {
    adding.value = false
  }
}

function addPicked() {
  if (!canAdd.value) return

  void addVariant(pickedSize.value, pickedColor.value)
}

async function openPicker() {
  pickerOpen.value = !pickerOpen.value

  if (!pickerOpen.value || shopSizes.value.length || shopColors.value.length) return

  try {
    ;[shopSizes.value, shopColors.value] = await Promise.all([
      catalogApi.sizes(),
      catalogApi.colors(),
    ])
  } catch (err) {
    error.value = errorMessage(err, 'O‘lcham va ranglarni yuklab bo‘lmadi.')
  }
}

// Katakcha ochilishi bilan birinchi katakka fokus: qo'l klaviaturada
// qoladi, sichqoncha kerak emas
onMounted(async () => {
  await nextTick()

  const first = root.value?.querySelector<HTMLInputElement>('.cell')

  first?.focus()
  first?.select()

  // Ustunlar do'kondagi tartibda (S–M–L–XL) tursin
  try {
    ;[shopSizes.value, shopColors.value] = await Promise.all([
      catalogApi.sizes(),
      catalogApi.colors(),
    ])
  } catch {
    // Tartib — qulaylik; ro'yxat kelmasa, variantlar tartibida qoladi
  }
})
</script>

<template>
  <div ref="root" class="model-grid" data-testid="model-grid">
    <div class="model-head">
      <div>
        <strong>{{ model.name }}</strong>
        <small class="cell-sub">
          <template v-if="model.brand">{{ model.brand }} · </template>
          Do‘kondagi narxi: {{ formatSum(model.currentPrice) }}
        </small>
      </div>

      <button
        class="icon-button delete"
        type="button"
        :aria-label="`${model.name}: ro‘yxatdan olib tashlash`"
        @click="emit('remove')"
      >
        <svg><use href="#i-trash" /></svg>
      </button>
    </div>

    <div class="model-prices">
      <label class="price-field">
        <span>Tannarx (model uchun)</span>
        <AmountField v-model="model.cost" aria-label="Model tannarxi" placeholder="0" />
      </label>

      <label class="price-field narrow">
        <span>Ustama</span>
        <AmountField
          v-model="model.markup"
          suffix="%"
          :grouped="false"
          aria-label="Ustama foizi"
        />
      </label>

      <label class="price-field">
        <span>Yangi sotuv narxi</span>
        <AmountField
          v-model="model.newPrice"
          aria-label="Yangi sotuv narxi"
          :placeholder="formatMoney(model.currentPrice)"
        />
      </label>
    </div>

    <div class="grid-scroll">
      <table class="quantity-grid">
        <thead>
          <tr>
            <th></th>
            <th v-for="size in sizes" :key="String(size.id)">{{ size.name }}</th>
          </tr>
        </thead>

        <tbody>
          <tr v-for="color in colors" :key="String(color.id)">
            <th>{{ color.name }}</th>

            <td v-for="size in sizes" :key="String(size.id)">
              <input
                v-if="gridCell(model.variants, size.id, color.id)"
                class="cell"
                type="number"
                min="0"
                inputmode="numeric"
                :data-variant="gridCell(model.variants, size.id, color.id)!.id"
                :aria-label="`${size.name} ${color.name}: nechta`"
                :value="quantity(gridCell(model.variants, size.id, color.id)!.id)"
                @input="
                  setQuantity(
                    gridCell(model.variants, size.id, color.id)!.id,
                    ($event.target as HTMLInputElement).value,
                  )
                "
              />

              <!-- Bunday juftlik hali yo'q: bir bosishda yaratiladi -->
              <button
                v-else
                class="cell-add"
                type="button"
                :disabled="adding"
                :title="`${size.name} ${color.name} qo‘shish`"
                :aria-label="`${size.name} ${color.name}: variantni qo‘shish`"
                @click="addVariant(size.id, color.id)"
              >
                +
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <div class="add-variant">
      <button
        class="button button-outline"
        type="button"
        :aria-expanded="pickerOpen"
        @click="openPicker"
      >
        <svg><use href="#i-plus" /></svg>
        <span>O‘lcham yoki rang</span>
      </button>
    </div>

    <div v-if="pickerOpen" class="variant-picker">
      <div v-if="shopSizes.length" class="picker-row">
        <span class="picker-label">O‘lcham</span>

        <div class="picker-chips" role="group" aria-label="O‘lcham tanlash">
          <button
            v-for="size in shopSizes"
            :key="size.id"
            class="size-chip"
            :class="{ active: pickedSize === size.id }"
            type="button"
            :aria-pressed="pickedSize === size.id"
            @click="pickedSize = pickedSize === size.id ? null : size.id"
          >
            {{ size.name }}
          </button>
        </div>
      </div>

      <div v-if="shopColors.length" class="picker-row">
        <span class="picker-label">Rang</span>

        <div class="picker-chips" role="group" aria-label="Rang tanlash">
          <button
            v-for="color in shopColors"
            :key="color.id"
            class="swatch"
            :class="{ active: pickedColor === color.id }"
            type="button"
            :aria-pressed="pickedColor === color.id"
            :aria-label="color.name"
            @click="pickedColor = pickedColor === color.id ? null : color.id"
          >
            <span class="swatch-dot" :style="{ background: color.hex_code }" />
            <small>{{ color.name }}</small>
          </button>
        </div>
      </div>

      <div class="picker-actions">
        <button class="button button-outline" type="button" @click="pickerOpen = false">
          Bekor qilish
        </button>

        <button
          class="button button-gradient"
          type="button"
          :disabled="!canAdd || adding"
          @click="addPicked"
        >
          {{ adding ? 'Qo‘shilmoqda…' : 'Qo‘shish' }}
        </button>
      </div>
    </div>

    <p v-if="error" class="load-error">{{ error }}</p>

    <div class="model-foot">
      <button
        v-if="filled.length"
        class="button button-outline"
        type="button"
        :aria-expanded="overridesOpen"
        @click="overridesOpen = !overridesOpen"
      >
        Alohida tannarx
      </button>

      <strong class="model-total">{{ units }} dona · {{ formatSum(total) }}</strong>
    </div>

    <!-- Alohida tannarx: faqat to'ldirilgan katakchalar ko'rinadi -->
    <table v-if="overridesOpen && filled.length" class="data-table overrides">
      <thead>
        <tr>
          <th>Qator</th>
          <th class="num">Soni</th>
          <th class="num">Tannarx</th>
        </tr>
      </thead>

      <tbody>
        <tr v-for="row in filled" :key="row.variant.id">
          <td>{{ row.variant.label }}</td>
          <td class="num">{{ row.quantity }}</td>
          <td class="num">
            <AmountField
              :model-value="model.overrides[row.variant.id] ?? ''"
              :aria-label="`${row.variant.label}: tannarx`"
              :placeholder="formatMoney(model.cost || '0')"
              @update:model-value="setOverride(row.variant.id, $event)"
            />
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<style scoped>
.model-grid {
  margin: 10px 0;
  padding: 14px;
  border: 1px solid var(--border-strong);
  border-radius: var(--radius-card);
  background: var(--surface);
}

.model-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 10px;
}

.model-head strong {
  font-size: 16px;
}

.model-prices {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-end;
  gap: 10px;
  margin-bottom: 12px;
}

.price-field {
  display: flex;
  flex-direction: column;
  gap: 4px;
  width: 170px;
}

.price-field.narrow {
  width: 96px;
}

.price-field span {
  color: var(--text-secondary);
  font-size: 13px;
}

.price-field input {
  text-align: right;
  font-variant-numeric: tabular-nums;
}

.price-hint {
  flex: 1;
  min-width: 200px;
  color: var(--text-muted);
  font-size: 13px;
}

.grid-scroll {
  overflow-x: auto;
}

.quantity-grid {
  border-collapse: collapse;
}

.quantity-grid th {
  padding: 4px 8px;
  color: var(--text-secondary);
  font-size: 13px;
  font-weight: 600;
  white-space: nowrap;
}

.quantity-grid tbody th {
  text-align: right;
}

.quantity-grid td {
  padding: 2px;
}

/* Katak barmoq uchun ham, klaviatura uchun ham qulay o'lchamda */
.cell {
  width: 62px;
  height: 40px;
  text-align: center;
  font-size: 16px;
  font-variant-numeric: tabular-nums;
}

/* Bunday juftlik hali yo'q — bosilsa yaratiladi */
.cell-add {
  width: 62px;
  height: 40px;
  border: 1px dashed var(--border-strong);
  border-radius: var(--radius);
  background: transparent;
  color: var(--gray-5);
  font-size: 17px;
  cursor: pointer;
}

.cell-add:hover:not(:disabled) {
  border-color: var(--accent);
  background: var(--accent-soft);
  color: var(--accent);
}

/* --- Yangi o'lcham yoki rang --- */

.add-variant {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-top: 10px;
}

.variant-picker {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-top: 10px;
  padding: 12px;
  border: 1px solid var(--border);
  border-radius: var(--radius-card);
  background: var(--surface-soft);
}

.picker-row {
  display: flex;
  align-items: flex-start;
  gap: 10px;
}

.picker-label {
  width: 64px;
  padding-top: 8px;
  color: var(--text-secondary);
  font-size: 13px;
}

.picker-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.size-chip {
  min-width: 44px;
  min-height: 34px;
  padding: 0 12px;
  border: 1px solid var(--border-strong);
  border-radius: var(--radius);
  background: var(--surface);
  color: var(--text-secondary);
  font-size: 15px;
  cursor: pointer;
}

.size-chip.active {
  border-color: var(--gray-9);
  background: var(--gray-9);
  color: #fff;
}

.swatch {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  width: 58px;
  padding: 2px;
  border: 0;
  background: none;
  cursor: pointer;
}

.swatch-dot {
  width: 26px;
  height: 26px;
  border: 1px solid var(--border-strong);
  border-radius: 50%;
}

.swatch.active .swatch-dot {
  box-shadow:
    0 0 0 2px var(--surface-soft),
    0 0 0 4px var(--accent);
}

.swatch small {
  color: var(--text-muted);
  font-size: 12px;
}

.swatch.active small {
  color: var(--text);
  font-weight: 600;
}

.picker-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}

.model-foot {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 10px;
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid var(--border);
}

.model-total {
  margin-left: auto;
  font-size: 16px;
  font-variant-numeric: tabular-nums;
}

.overrides {
  margin-top: 10px;
}

.cart-number {
  width: 80px;
  text-align: right;
}

.cart-number.wide {
  width: 120px;
}
</style>
