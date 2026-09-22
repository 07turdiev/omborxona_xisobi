<script setup lang="ts">
import { onMounted, ref } from 'vue'

import AmountField from '@/components/AmountField.vue'
import { errorMessage } from '@/api/client'
import { purchasesApi } from '@/api/purchases'
import { formatDate, todayIso } from '@/utils/date'
import { formatMoney, normalizeMoneyInput } from '@/utils/money'
import type { Supplier, SupplierPayment } from '@/types'

const suppliers = ref<Supplier[]>([])
const payments = ref<SupplierPayment[]>([])
const selected = ref<Supplier | null>(null)

const loading = ref(false)
const saving = ref(false)
const error = ref('')

const form = ref({ name: '', phone: '', note: '' })
const payment = ref({ date: todayIso(), amount: '', note: '' })

async function load() {
  loading.value = true
  error.value = ''

  try {
    const page = await purchasesApi.suppliers()
    suppliers.value = page.results
  } catch (err) {
    error.value = errorMessage(err, 'Ta’minotchilarni yuklab bo‘lmadi.')
  } finally {
    loading.value = false
  }
}

async function onSelect(supplier: Supplier) {
  selected.value = supplier

  const page = await purchasesApi.payments(supplier.id)
  payments.value = page.results
}

async function onCreate() {
  if (!form.value.name.trim() || saving.value) return

  saving.value = true
  error.value = ''

  try {
    await purchasesApi.createSupplier(form.value)

    form.value = { name: '', phone: '', note: '' }
    await load()
  } catch (err) {
    error.value = errorMessage(err, 'Saqlab bo‘lmadi.')
  } finally {
    saving.value = false
  }
}

async function onPay() {
  if (!selected.value || !payment.value.amount.trim() || saving.value) return

  saving.value = true
  error.value = ''

  try {
    await purchasesApi.createPayment({
      supplier: selected.value.id,
      date: payment.value.date,
      amount: normalizeMoneyInput(payment.value.amount),
      note: payment.value.note,
    })

    payment.value = { date: todayIso(), amount: '', note: '' }

    await load()
    await onSelect(selected.value)
  } catch (err) {
    error.value = errorMessage(err, 'To‘lovni saqlab bo‘lmadi.')
  } finally {
    saving.value = false
  }
}

onMounted(load)
</script>

<template>
  <section class="app-section active">
    <p v-if="error" class="load-error">{{ error }}</p>

    <div class="suppliers">
      <div class="table-card">
        <div class="table-scroll">
          <table class="data-table">
            <thead>
              <tr>
                <th>Nomi</th>
                <th>Telefon</th>
                <th class="num">Qarz</th>
              </tr>
            </thead>

            <tbody>
              <tr v-if="loading">
                <td colspan="3" class="empty-state">Yuklanmoqda…</td>
              </tr>

              <tr v-else-if="!suppliers.length">
                <td colspan="3" class="empty-state">Ta’minotchi qo‘shilmagan.</td>
              </tr>

              <tr
                v-for="supplier in suppliers"
                v-else
                :key="supplier.id"
                class="clickable"
                :class="{ active: selected?.id === supplier.id }"
                @click="onSelect(supplier)"
              >
                <td><strong>{{ supplier.name }}</strong></td>
                <td>{{ supplier.phone || '—' }}</td>
                <td class="num">{{ formatMoney(supplier.balance) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <aside class="side-column">
        <div class="table-card card-padded">
          <h3>Yangi ta’minotchi</h3>

          <div class="field">
            <label>Nomi</label>
            <input v-model="form.name" type="text" />
          </div>

          <div class="field">
            <label>Telefon</label>
            <input v-model="form.phone" type="text" placeholder="+998" />
          </div>

          <div class="field">
            <label>Izoh</label>
            <input v-model="form.note" type="text" />
          </div>

          <button class="button button-gradient" type="button" :disabled="saving" @click="onCreate">
            Qo‘shish
          </button>
        </div>

        <div v-if="selected" class="table-card card-padded">
          <h3>{{ selected.name }} — to‘lov</h3>

          <div class="field">
            <label>Sana</label>
            <input v-model="payment.date" type="date" />
          </div>

          <div class="field">
            <label>Summa</label>
            <AmountField v-model="payment.amount" />
          </div>

          <div class="field">
            <label>Izoh</label>
            <input v-model="payment.note" type="text" />
          </div>

          <button class="button button-outline" type="button" :disabled="saving" @click="onPay">
            To‘lovni saqlash
          </button>

          <table v-if="payments.length" class="data-table payments">
            <tbody>
              <tr v-for="item in payments" :key="item.id">
                <td>{{ formatDate(item.date) }}</td>
                <td class="num">{{ formatMoney(item.amount) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </aside>
    </div>
  </section>
</template>

<style scoped>
.suppliers {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 300px;
  align-items: start;
  gap: 12px;
}

@media (max-width: 1000px) {
  .suppliers {
    grid-template-columns: 1fr;
  }
}

.side-column {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.clickable {
  cursor: pointer;
}

.clickable.active td {
  background: var(--accent-soft);
}

.payments {
  margin-top: 12px;
}
</style>
