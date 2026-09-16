<script setup lang="ts">
import { onMounted, ref } from 'vue'

import ScanField from '@/components/ScanField.vue'
import { catalogApi } from '@/api/catalog'
import { errorMessage } from '@/api/client'
import { inventoryApi } from '@/api/inventory'
import { formatDateTime } from '@/utils/date'
import { formatMoney } from '@/utils/money'
import type { Variant, WriteOff } from '@/types'

const items = ref<WriteOff[]>([])
const loading = ref(false)
const error = ref('')
const saving = ref(false)

const scanner = ref<InstanceType<typeof ScanField> | null>(null)
const variant = ref<Variant | null>(null)
const quantity = ref(1)
const reason = ref('')

async function load() {
  loading.value = true

  try {
    const page = await inventoryApi.writeOffs()
    items.value = page.results
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
                <th class="num">Soni</th>
                <th>Sababi</th>
                <th class="num">Tannarx</th>
              </tr>
            </thead>

            <tbody>
              <tr v-if="loading">
                <td colspan="5" class="empty-state">Yuklanmoqda…</td>
              </tr>

              <tr v-else-if="!items.length">
                <td colspan="5" class="empty-state">Hisobdan chiqarilgan tovar yo‘q.</td>
              </tr>

              <tr v-for="item in items" v-else :key="item.id">
                <td>{{ formatDateTime(item.created_at) }}</td>
                <td>
                  <strong>{{ item.product_name }}</strong>
                  <small class="cell-sub">{{ item.variant_label || item.sku }}</small>
                </td>
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
            {{ variant.label || variant.sku }} · qoldiq {{ variant.stock_quantity }}
          </small>
        </div>

        <p v-else class="empty-state small">Tovarni skanerlang.</p>

        <div class="field">
          <label>Soni</label>
          <input v-model.number="quantity" type="number" min="1" :max="variant?.stock_quantity" />
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
  font-size: 13px;
}
</style>
