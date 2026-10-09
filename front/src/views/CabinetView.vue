<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'

import { errorMessage } from '@/api/client'
import { inventoryApi } from '@/api/inventory'
import { useAuthStore } from '@/stores/auth'
import { useToastStore } from '@/stores/toast'
import type { Cabinet, CabinetItem } from '@/types'

/**
 * Ombordagi shkaf: ustunlar harf, qatorlar raqam.
 *
 * Shkaf bitta va u kichik, shuning uchun butun jadval bitta ekranga
 * sig'adi. Katak faqat joyni ko'rsatadi: qoldiq avvalgidek butun ombor
 * bo'yicha yuritiladi. Bu sahifa bitta savolga javob beradi —
 * «tovarni qayerdan olaman?»
 */

const auth = useAuthStore()
const toast = useToastStore()

const board = ref<Cabinet | null>(null)
const selected = ref('')
const loading = ref(false)
const error = ref('')
const saving = ref(0)

const LETTERS = 'ABCDEFGHIJKL'

const columns = computed(() => board.value?.columns ?? 0)
const rows = computed(() => board.value?.rows ?? 0)

// `split` ataylab: `[...LETTERS.slice(n)]` deb yozilsa, lintning
// avtomatik tuzatishi spread'ni «keraksiz» deb olib tashlaydi va
// natija massiv emas, satr bo'lib qoladi
const headers = computed(() => LETTERS.slice(0, columns.value).split(''))

/** Jadval qatorlari: har qatorda katak nomlari */
const grid = computed(() =>
  Array.from({ length: rows.value }, (_, row) =>
    headers.value.map((letter) => `${letter}${row + 1}`),
  ),
)

/** Shkafdagi hamma katak nomi — ro'yxatlardagi tanlash uchun */
const allCells = computed(() => grid.value.flat())

const unplaced = computed(() => board.value?.unplaced ?? [])

const outside = computed(() => Object.entries(board.value?.outside ?? {}))

const inSelected = computed(() => (selected.value ? (board.value?.cells[selected.value] ?? []) : []))

function itemsIn(cell: string): CabinetItem[] {
  return board.value?.cells[cell] ?? []
}

function totalIn(cell: string): number {
  return itemsIn(cell).reduce((sum, item) => sum + item.quantity, 0)
}

async function load() {
  loading.value = true
  error.value = ''

  try {
    board.value = await inventoryApi.cabinet()

    // Tanlangan katak jadvaldan chiqib ketgan bo'lishi mumkin
    if (selected.value && !board.value.cells[selected.value]) selected.value = ''
  } catch (err) {
    error.value = errorMessage(err, 'Shkafni yuklab bo‘lmadi.')
  } finally {
    loading.value = false
  }
}

/** Tovarni katakka qo'yadi yoki joyini bo'shatadi. */
async function place(item: CabinetItem, cell: string) {
  saving.value = item.variant

  try {
    await inventoryApi.place(item.variant, cell)

    toast.show(cell ? `${item.name} — ${cell} katakka qo‘yildi` : `${item.name} — joyi bo‘shatildi`)

    await load()

    if (cell) selected.value = cell
  } catch (err) {
    toast.show(errorMessage(err, 'Joyni saqlab bo‘lmadi.'), 'error')
  } finally {
    saving.value = 0
  }
}

onMounted(load)
</script>

<template>
  <section class="app-section active">
    <p v-if="error" class="load-error">{{ error }}</p>

    <div v-if="board" class="cabinet">
      <div class="table-card card-padded board">
        <div class="card-head">
          <h3 class="card-title">Shkaf</h3>
          <span class="muted">{{ columns }} ustun × {{ rows }} qator</span>
        </div>

        <!-- Jadval Excel kabi: tepada harf, chapda raqam -->
        <div class="grid-scroll">
          <table class="grid">
            <thead>
              <tr>
                <th></th>
                <th v-for="letter in headers" :key="letter">{{ letter }}</th>
              </tr>
            </thead>

            <tbody>
              <tr v-for="(line, index) in grid" :key="index">
                <th>{{ index + 1 }}</th>

                <td v-for="cell in line" :key="cell">
                  <button
                    class="cell"
                    :class="{ filled: totalIn(cell) > 0, chosen: cell === selected }"
                    type="button"
                    :aria-label="`${cell}: ${totalIn(cell)} dona`"
                    @click="selected = cell"
                  >
                    <span class="cell-name">{{ cell }}</span>
                    <strong v-if="totalIn(cell)" class="cell-count">{{ totalIn(cell) }}</strong>
                  </button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <aside class="table-card card-padded chosen-cell">
        <h3 class="card-title">{{ selected || 'Katakni tanlang' }}</h3>

        <p v-if="!selected" class="field-hint">
          Jadvaldan katakni bosing — ichida nima turgani shu yerda ko‘rinadi.
        </p>

        <p v-else-if="!inSelected.length" class="field-hint">Katak bo‘sh.</p>

        <ul v-else class="cell-items">
          <li v-for="item in inSelected" :key="item.variant">
            <div class="cell-item">
              <strong>{{ item.name }}</strong>
              <small class="cell-sub">{{ item.label || '—' }} · {{ item.quantity }} dona</small>
            </div>

            <select
              v-if="auth.isAdmin"
              :value="selected"
              :disabled="saving === item.variant"
              :aria-label="`${item.name}: joyini o‘zgartirish`"
              @change="place(item, ($event.target as HTMLSelectElement).value)"
            >
              <option v-for="cell in allCells" :key="cell" :value="cell">{{ cell }}</option>
              <option value="">Joyini bo‘shatish</option>
            </select>
          </li>
        </ul>
      </aside>
    </div>

    <!-- Omborda bor, lekin joyi belgilanmagan tovarlar -->
    <div v-if="unplaced.length" class="table-card card-padded loose">
      <h3 class="card-title">Joyi belgilanmagan ({{ unplaced.length }})</h3>

      <p class="field-hint">
        Bu tovarlar omborda turibdi, lekin qaysi katakda ekani yozilmagan.
      </p>

      <ul class="cell-items">
        <li v-for="item in unplaced" :key="item.variant">
          <div class="cell-item">
            <strong>{{ item.name }}</strong>
            <small class="cell-sub">{{ item.label || '—' }} · {{ item.quantity }} dona</small>
          </div>

          <select
            v-if="auth.isAdmin"
            value=""
            :disabled="saving === item.variant"
            :aria-label="`${item.name}: joyini belgilash`"
            @change="place(item, ($event.target as HTMLSelectElement).value)"
          >
            <option value="">Katakni tanlang</option>
            <option v-for="cell in allCells" :key="cell" :value="cell">{{ cell }}</option>
          </select>
        </li>
      </ul>
    </div>

    <!-- Shkaf kichraytirilgan bo'lsa, eski kataklar jadvaldan chiqib
         ketadi. Tovar esa o'sha yerda turibdi — jim qolib bo'lmaydi. -->
    <div v-if="outside.length" class="table-card card-padded warning">
      <h3 class="card-title">Shkafdan tashqarida ({{ outside.length }} katak)</h3>

      <p class="field-hint">
        Shkaf kichraytirilgan va bu kataklar jadvalda yo‘q. Tovarni boshqa katakka
        ko‘chiring yoki Sozlamalarda shkaf o‘lchamini kattalashtiring.
      </p>

      <ul class="cell-items">
        <li v-for="[cell, items] in outside" :key="cell">
          <div class="cell-item">
            <strong>{{ cell }}</strong>
            <small class="cell-sub">{{ items.map((item) => item.name).join(', ') }}</small>
          </div>

          <select
            v-if="auth.isAdmin"
            value=""
            :aria-label="`${cell}: tovarni ko‘chirish`"
            @change="
              items.forEach((item) => place(item, ($event.target as HTMLSelectElement).value))
            "
          >
            <option value="">Qayerga ko‘chirilsin</option>
            <option v-for="target in allCells" :key="target" :value="target">{{ target }}</option>
          </select>
        </li>
      </ul>
    </div>

    <p v-if="loading && !board" class="field-hint">Yuklanmoqda…</p>
  </section>
</template>

<style scoped>
.cabinet {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 300px;
  align-items: start;
  gap: 12px;
}

.card-head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 12px;
}

.grid-scroll {
  overflow-x: auto;
}

.grid {
  width: 100%;
  margin-top: 8px;
  border-collapse: separate;
  border-spacing: 6px;
}

/* Ustun harflari va qator raqamlari — jadvalning o'zi kabi */
.grid th {
  color: var(--text-secondary);
  font-size: 13px;
  font-weight: 600;
}

.grid tbody th {
  width: 24px;
  text-align: right;
}

.cell {
  display: flex;
  flex-direction: column;
  gap: 2px;
  width: 100%;
  min-height: 64px;
  padding: 6px;
  border: 1px solid var(--border);
  border-radius: var(--radius);
  background: var(--surface-soft);
  cursor: pointer;
}

.cell:hover {
  border-color: var(--accent);
}

/* To'lgan katak ko'zga tashlansin: bo'sh shkafda tovarni izlab
   har katakni bosib chiqish kerak bo'lmasin */
.cell.filled {
  border-color: var(--accent);
  background: var(--accent-soft);
}

.cell.chosen {
  outline: 2px solid var(--accent);
  outline-offset: 1px;
}

.cell-name {
  color: var(--text-secondary);
  font-size: 12px;
}

.cell-count {
  font-size: 20px;
  line-height: 1;
}

.cell-items {
  margin: 8px 0 0;
  padding: 0;
  list-style: none;
}

.cell-items li {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 8px 0;
  border-bottom: 1px solid var(--border);
}

.cell-items li:last-child {
  border-bottom: 0;
}

.cell-item {
  min-width: 0;
}

.cell-item strong {
  display: block;
  line-height: 1.25;
}

.cell-sub {
  color: var(--text-secondary);
}

.loose,
.warning {
  margin-top: 12px;
}

.warning {
  border-color: var(--danger, #b3261e);
}

@media (max-width: 1000px) {
  .cabinet {
    grid-template-columns: 1fr;
  }
}
</style>
