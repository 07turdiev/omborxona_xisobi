<script setup lang="ts">
import { computed, nextTick, onMounted, ref, watch } from 'vue'

import { useAuthStore } from '@/stores/auth'
import { formatMoney, formatSum, suggestPrice } from '@/utils/money'
import {
  cloneModel,
  gridCell,
  gridColors,
  gridSizes,
  lineCost,
  modelTotal,
  modelUnits,
  type DraftModel,
} from '@/utils/receiving'

/**
 * Modelni qabul qilish katakchasi: ustunlar — o'lcham, qatorlar — rang.
 *
 * Do'konga tovar qutida, o'lchamlari aralash keladi. Kassir qutini
 * ochib, har o'lchamdan nechta borligini shu katakchaga yozadi —
 * Tab bilan katakdan katakka o'tadi, bo'sh katak "kelmagan" degani.
 *
 * Tannarx modelga bitta: bir kirimda bir model odatda bir narxda
 * keladi. Kerak bo'lsa alohida qatorga boshqa narx yoziladi.
 */

const props = defineProps<{ model: DraftModel }>()

const emit = defineEmits<{ save: [model: DraftModel]; close: [] }>()

const auth = useAuthStore()

/** Ota komponentning holatini bevosita o'zgartirmaymiz — nusxa ustida ishlaymiz */
const model = ref<DraftModel>(cloneModel(props.model))

const overridesOpen = ref(Object.keys(props.model.overrides).length > 0)
const root = ref<HTMLElement | null>(null)

const sizes = computed(() => gridSizes(model.value.variants))
const colors = computed(() => gridColors(model.value.variants))

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

function onSave() {
  emit('save', model.value)
}

// Katakcha ochilishi bilan birinchi katakka fokus: qo'l klaviaturada
// qoladi, sichqoncha kerak emas
onMounted(async () => {
  await nextTick()

  const first = root.value?.querySelector<HTMLInputElement>('.cell')

  first?.focus()
  first?.select()
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

      <button class="icon-button" type="button" aria-label="Yopish" @click="emit('close')">
        <svg><use href="#i-close" /></svg>
      </button>
    </div>

    <div class="model-prices">
      <label class="price-field">
        <span>Tannarx (model uchun)</span>
        <input
          v-model="model.cost"
          type="text"
          inputmode="decimal"
          aria-label="Model tannarxi"
          placeholder="0"
        />
      </label>

      <label class="price-field narrow">
        <span>Ustama %</span>
        <input v-model="model.markup" type="text" inputmode="decimal" aria-label="Ustama foizi" />
      </label>

      <label class="price-field">
        <span>Yangi sotuv narxi</span>
        <input
          v-model="model.newPrice"
          type="text"
          inputmode="decimal"
          aria-label="Yangi sotuv narxi"
          :placeholder="formatMoney(model.currentPrice)"
        />
      </label>

      <p class="price-hint">
        Narx kirim <strong>tasdiqlanganda</strong> mahsulotga yoziladi.
        Bo‘sh qoldirilsa, eski narx qoladi.
      </p>
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
                :aria-label="`${size.name} ${color.name}: nechta`"
                :value="quantity(gridCell(model.variants, size.id, color.id)!.id)"
                @input="
                  setQuantity(
                    gridCell(model.variants, size.id, color.id)!.id,
                    ($event.target as HTMLInputElement).value,
                  )
                "
                @keydown.enter.prevent="onSave"
              />

              <span v-else class="cell-missing">—</span>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

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

      <div class="model-actions">
        <button class="button button-outline" type="button" @click="emit('close')">
          Bekor qilish
        </button>

        <button class="button button-gradient" type="button" @click="onSave">Tayyor</button>
      </div>
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
            <input
              class="cart-number wide"
              type="text"
              inputmode="decimal"
              :aria-label="`${row.variant.label}: tannarx`"
              :value="model.overrides[row.variant.id] ?? ''"
              :placeholder="formatMoney(model.cost || '0')"
              @input="setOverride(row.variant.id, ($event.target as HTMLInputElement).value)"
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
  font-size: 15px;
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
  font-size: 12px;
}

.price-field input {
  text-align: right;
  font-variant-numeric: tabular-nums;
}

.price-hint {
  flex: 1;
  min-width: 200px;
  color: var(--text-muted);
  font-size: 12px;
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
  font-size: 12px;
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
  font-size: 15px;
  font-variant-numeric: tabular-nums;
}

.cell-missing {
  display: block;
  width: 62px;
  color: var(--gray-4);
  text-align: center;
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
  font-size: 15px;
  font-variant-numeric: tabular-nums;
}

.model-actions {
  display: flex;
  gap: 8px;
  margin-left: auto;
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
