<script setup lang="ts">
import { onMounted, ref } from 'vue'

import api from '@/api/client'

interface CustomUnit {
  id: number
  name: string
  symbol: string
  definition: string
  definition_string: string
  description: string
}

const units = ref<CustomUnit[]>([])
const loading = ref(false)

// Konvertor
const value = ref('2 mashina')
const targetUnit = ref('m3')
const result = ref('')
const convertError = ref('')

async function load() {
  loading.value = true

  try {
    const { data } = await api.get<{ results: CustomUnit[] }>('/units/')
    units.value = data.results
  } finally {
    loading.value = false
  }
}

async function convert() {
  result.value = ''
  convertError.value = ''

  try {
    const { data } = await api.get<{ result: string }>('/units-convert/', {
      params: { value: value.value, unit: targetUnit.value },
    })
    result.value = data.result
  } catch (err: unknown) {
    const response = (err as { response?: { data?: { detail?: string } } }).response
    convertError.value = response?.data?.detail ?? 'Konversiya bajarilmadi.'
  }
}

onMounted(load)
</script>

<template>
  <section class="app-section active">
    <div class="table-card converter">
      <h3>Konvertor</h3>

      <p class="hint">
        Qiymatni o‘lchov birligiga keltiradi. Hisob <code>Decimal</code> da bajariladi —
        yaxlitlash xatosi yo‘q.
      </p>

      <div class="converter-row">
        <div class="field">
          <label>Qiymat</label>
          <input v-model="value" placeholder="2 mashina" />
        </div>

        <div class="field">
          <label>Birlik</label>
          <input v-model="targetUnit" placeholder="m3" />
        </div>

        <button class="button button-gradient" type="button" @click="convert">
          Hisoblash
        </button>
      </div>

      <p v-if="result" class="converter-result">Natija: <strong>{{ result }}</strong></p>
      <p v-if="convertError" class="converter-error">{{ convertError }}</p>
    </div>

    <div class="table-card">
      <div class="table-scroll">
        <table class="data-table">
          <thead>
            <tr>
              <th>Nomi</th>
              <th>Belgisi</th>
              <th>Ta’rifi</th>
              <th>Izoh</th>
            </tr>
          </thead>

          <tbody>
            <tr v-if="loading">
              <td colspan="4" class="empty-state">Yuklanmoqda…</td>
            </tr>

            <tr v-else-if="!units.length">
              <td colspan="4" class="empty-state">
                Tashkilotning o‘z birliklari hali yo‘q.
              </td>
            </tr>

            <tr v-for="unit in units" v-else :key="unit.id">
              <td><strong>{{ unit.name }}</strong></td>
              <td>{{ unit.symbol || '—' }}</td>
              <td><code>{{ unit.definition_string }}</code></td>
              <td>{{ unit.description || '—' }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </section>
</template>

<style scoped>
.converter {
  margin-bottom: 16px;
  padding: 20px 24px;
}

.converter h3 {
  margin-bottom: 6px;
  font-size: 16px;
}

.converter-row {
  display: flex;
  gap: 12px;
  align-items: flex-end;
  flex-wrap: wrap;
}

.converter-result {
  margin-top: 12px;
  color: var(--green);
  font-size: 14px;
}

.converter-error {
  margin-top: 12px;
  color: var(--red);
  font-size: 13px;
}

code {
  font-size: 12px;
}
</style>
