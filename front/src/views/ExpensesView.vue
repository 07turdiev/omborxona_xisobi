<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'

import { errorMessage } from '@/api/client'
import { expensesApi } from '@/api/reports'
import { addMoney, formatMoney, formatSum, normalizeMoneyInput } from '@/utils/money'
import { formatDate, monthStartIso, todayIso } from '@/utils/date'
import type { Expense } from '@/types'

const CATEGORIES = [
  { value: 'rent', label: 'Ijara' },
  { value: 'salary', label: 'Ish haqi' },
  { value: 'utilities', label: 'Kommunal' },
  { value: 'other', label: 'Boshqa' },
]

const items = ref<Expense[]>([])
const loading = ref(false)
const error = ref('')
const saving = ref(false)

const dateFrom = ref(monthStartIso())
const dateTo = ref(todayIso())

const form = ref({ date: todayIso(), category: 'other', amount: '', note: '' })

const total = computed(() => items.value.reduce((sum, item) => addMoney(sum, item.amount), '0'))

async function load() {
  loading.value = true
  error.value = ''

  try {
    const page = await expensesApi.list({ date_from: dateFrom.value, date_to: dateTo.value })
    items.value = page.results
  } catch (err) {
    error.value = errorMessage(err, 'Xarajatlarni yuklab bo‘lmadi.')
  } finally {
    loading.value = false
  }
}

async function onSave() {
  if (!form.value.amount.trim() || saving.value) return

  saving.value = true
  error.value = ''

  try {
    await expensesApi.create({
      date: form.value.date,
      category: form.value.category,
      amount: normalizeMoneyInput(form.value.amount),
      note: form.value.note,
    })

    form.value = { date: todayIso(), category: 'other', amount: '', note: '' }
    await load()
  } catch (err) {
    error.value = errorMessage(err, 'Xarajatni saqlab bo‘lmadi.')
  } finally {
    saving.value = false
  }
}

async function onRemove(item: Expense) {
  if (!window.confirm('Xarajat o‘chirilsinmi?')) return

  try {
    await expensesApi.remove(item.id)
    await load()
  } catch (err) {
    error.value = errorMessage(err, 'O‘chirib bo‘lmadi.')
  }
}

onMounted(load)
</script>

<template>
  <section class="app-section active">
    <div class="section-toolbar">
      <div class="filters">
        <input v-model="dateFrom" type="date" />
        <input v-model="dateTo" type="date" />
        <button class="button button-outline" type="button" @click="load">Ko‘rsatish</button>
      </div>

      <div class="total-badge">Jami: <strong>{{ formatSum(total) }}</strong></div>
    </div>

    <p v-if="error" class="load-error">{{ error }}</p>

    <div class="expenses">
      <div class="table-card">
        <div class="table-scroll">
          <table class="data-table">
            <thead>
              <tr>
                <th>Sana</th>
                <th>Turi</th>
                <th>Izoh</th>
                <th class="num">Summa</th>
                <th></th>
              </tr>
            </thead>

            <tbody>
              <tr v-if="loading">
                <td colspan="5" class="empty-state">Yuklanmoqda…</td>
              </tr>

              <tr v-else-if="!items.length">
                <td colspan="5" class="empty-state">Bu davrda xarajat yo‘q.</td>
              </tr>

              <tr v-for="item in items" v-else :key="item.id">
                <td>{{ formatDate(item.date) }}</td>
                <td>{{ item.category_display }}</td>
                <td>{{ item.note || '—' }}</td>
                <td class="num">{{ formatMoney(item.amount) }}</td>
                <td class="num">
                  <button class="icon-button delete" type="button" @click="onRemove(item)">
                    <svg><use href="#i-trash" /></svg>
                  </button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <aside class="table-card card-padded">
        <h3>Yangi xarajat</h3>

        <div class="field">
          <label>Sana</label>
          <input v-model="form.date" type="date" />
        </div>

        <div class="field">
          <label>Turi</label>
          <select v-model="form.category">
            <option v-for="item in CATEGORIES" :key="item.value" :value="item.value">
              {{ item.label }}
            </option>
          </select>
        </div>

        <div class="field">
          <label>Summa</label>
          <input v-model="form.amount" type="text" inputmode="decimal" placeholder="0" />
        </div>

        <div class="field">
          <label>Izoh</label>
          <input v-model="form.note" type="text" />
        </div>

        <button class="button button-gradient" type="button" :disabled="saving" @click="onSave">
          {{ saving ? 'Saqlanmoqda…' : 'Saqlash' }}
        </button>
      </aside>
    </div>
  </section>
</template>

<style scoped>
.expenses {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 300px;
  align-items: start;
  gap: 12px;
}

@media (max-width: 1000px) {
  .expenses {
    grid-template-columns: 1fr;
  }
}

.total-badge {
  font-size: 13px;
}

.total-badge strong {
  font-size: 16px;
}
</style>
