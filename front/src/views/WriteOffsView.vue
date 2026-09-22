<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'

import ScanField from '@/components/ScanField.vue'
import { catalogApi } from '@/api/catalog'
import { errorMessage } from '@/api/client'
import { inventoryApi } from '@/api/inventory'
import { formatDateTime } from '@/utils/date'
import { formatMoney } from '@/utils/money'
import { stockOfKind } from '@/utils/stock'
import type { Location, Variant, WriteOff } from '@/types'

/**
 * Hisobdan chiqarish: buzilgan yoki yo'qolgan tovar qoldiqdan yechiladi.
 *
 * Joy so'raladi: tovar omborda ham, javonda ham buzilishi mumkin, qoldiq
 * esa har joyda alohida yuritiladi.
 */

const items = ref<WriteOff[]>([])
const loading = ref(false)
const error = ref('')
const saving = ref(false)

const scanner = ref<InstanceType<typeof ScanField> | null>(null)
const variant = ref<Variant | null>(null)
const quantity = ref(1)
const reason = ref('')

const locations = ref<Location[]>([])
const location = ref<number | null>(null)

/** Tanlangan joydagi qoldiq — shundan ortig'ini yechib bo'lmaydi */
const available = computed(() => {
  if (!variant.value || location.value === null) return 0

  return (variant.value.stocks ?? [])
    .filter((stock) => stock.location === location.value)
    .reduce((sum, stock) => sum + stock.quantity, 0)
})

async function load() {
  loading.value = true

  try {
    const [page, places] = await Promise.all([
      inventoryApi.writeOffs(),
      inventoryApi.locations(),
    ])

    items.value = page.results
    locations.value = places
    location.value ??= places.find((place) => place.kind === 'shop')?.id ?? null
  } catch (err) {
    error.value = errorMessage(err, 'Ro‘yxatni yuklab bo‘lmadi.')
  } finally {
    loading.value = false
  }
}

async function onScan(code: string) {
  error.value = ''

  try {
    variant.value = await catalogApi.byBarcode(code)
  } catch (err) {
    variant.value = null
    error.value = errorMessage(err, `«${code}» — tovar topilmadi.`)
  } finally {
    scanner.value?.focus()
  }
}

async function onSave() {
  if (!variant.value || !reason.value.trim() || saving.value) return

  saving.value = true
  error.value = ''

  try {
    await inventoryApi.createWriteOff({
      variant: variant.value.id,
      quantity: quantity.value,
      reason: reason.value,
      location: location.value,
    })

    variant.value = null
    quantity.value = 1
    reason.value = ''

    await load()
  } catch (err) {
    error.value = errorMessage(err, 'Hisobdan chiqarib bo‘lmadi.')
  } finally {
    saving.value = false
    scanner.value?.focus()
  }
}

onMounted(load)
</script>

<template>
  <section class="app-section active">
    <p v-if="error" class="load-error">{{ error }}</p>

    <div class="write-offs">
      <div class="table-card">
        <div class="table-scroll">
          <table class="data-table">
            <thead>
              <tr>
                <th>Sana</th>
                <th>Mahsulot</th>
                <th>Joy</th>
                <th class="num">Soni</th>
                <th>Sababi</th>
                <th class="num">Tannarx</th>
              </tr>
            </thead>

            <tbody>
              <tr v-if="loading">
                <td colspan="6" class="empty-state">Yuklanmoqda…</td>
              </tr>

              <tr v-else-if="!items.length">
                <td colspan="6" class="empty-state">Hisobdan chiqarilgan tovar yo‘q.</td>
              </tr>

              <tr v-for="item in items" v-else :key="item.id">
                <td>{{ formatDateTime(item.created_at) }}</td>
                <td>
                  <strong>{{ item.product_name }}</strong>
                  <small class="cell-sub">{{ item.variant_label || item.sku }}</small>
                </td>
                <td>{{ item.location_name }}</td>
                <td class="num">{{ item.quantity }}</td>
                <td>{{ item.reason }}</td>
                <td class="num">{{ formatMoney(item.unit_cost) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <aside class="table-card card-padded">
        <h3>Hisobdan chiqarish</h3>

        <ScanField ref="scanner" @scan="onScan" />

        <div v-if="variant" class="picked">
          <strong>{{ variant.product_name }}</strong>
          <small class="cell-sub">
            {{ variant.label || variant.sku }} ·
            zalda {{ stockOfKind(variant, 'shop') }} ·
            omborda {{ stockOfKind(variant, 'warehouse') }}
          </small>
        </div>

        <p v-else class="empty-state small">Tovarni skanerlang.</p>

        <div class="field">
          <label>Qayerdan</label>
          <select v-model="location">
            <option v-for="place in locations" :key="place.id" :value="place.id">
              {{ place.name }}
            </option>
          </select>
        </div>

        <div class="field">
          <label>Soni</label>
          <input v-model.number="quantity" type="number" min="1" :max="available" />
          <small v-if="variant" class="field-hint">Bu joyda {{ available }} dona bor.</small>
        </div>

        <div class="field">
          <label>Sababi</label>
          <input v-model="reason" type="text" placeholder="Yaroqsiz, yo‘qolgan…" />
        </div>

        <button
          class="button button-danger"
          type="button"
          :disabled="!variant || !reason.trim() || saving"
          @click="onSave"
        >
          {{ saving ? 'Saqlanmoqda…' : 'Hisobdan chiqarish' }}
        </button>
      </aside>
    </div>
  </section>
</template>

<style scoped>
.write-offs {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 320px;
  align-items: start;
  gap: 12px;
}

@media (max-width: 1000px) {
  .write-offs {
    grid-template-columns: 1fr;
  }
}

.picked {
  display: flex;
  flex-direction: column;
  padding: 10px 12px;
  margin: 10px 0;
  border-radius: var(--radius);
  background: var(--accent-soft);
}

.empty-state.small {
  padding: 10px 0;
  font-size: 14px;
}
</style>
