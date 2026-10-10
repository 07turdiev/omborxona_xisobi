<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'

import { errorMessage } from '@/api/client'
import { inventoryApi } from '@/api/inventory'
import { useAuthStore } from '@/stores/auth'
import { useToastStore } from '@/stores/toast'
import type { Cabinet, CabinetItem, ShelfRun } from '@/types'

/**
 * Ombor javonlari: qaysi tovar qayerda turibdi.
 *
 * Ombor tor xona, javonlar devorlar bo'ylab ketadi va har devorda
 * ularning soni har xil. Shuning uchun bu yerda to'g'ri to'rtburchak
 * jadval emas — har qator o'z bo'yi bilan chiziladi.
 *
 * Manzil faqat joyni ko'rsatadi: qoldiq avvalgidek butun ombor
 * bo'yicha yuritiladi. Sahifa bitta savolga javob beradi —
 * «tovarni qayerdan olaman?»
 */

const auth = useAuthStore()
const toast = useToastStore()

const board = ref<Cabinet | null>(null)
const runs = ref<ShelfRun[]>([])
const selected = ref('')
const loading = ref(false)
const error = ref('')
const saving = ref(0)

const setupOpen = ref(false)
const draft = ref<{ id?: number; code: string; name: string; shelves: number }>({
  code: '',
  name: '',
  shelves: 1,
})

const ready = computed(() => (board.value?.runs.length ?? 0) > 0)
const unplaced = computed(() => board.value?.unplaced ?? [])
const outside = computed(() => Object.entries(board.value?.outside ?? {}))

/** Hamma manzil: ro'yxatdan tanlash uchun */
const allCells = computed(() =>
  (board.value?.runs ?? []).flatMap((run) => run.shelves.map((shelf) => shelf.cell)),
)

const chosen = computed(() => {
  for (const run of board.value?.runs ?? []) {
    const shelf = run.shelves.find((item) => item.cell === selected.value)

    if (shelf) return { run, shelf }
  }

  return null
})

function total(items: CabinetItem[]): number {
  return items.reduce((sum, item) => sum + item.quantity, 0)
}

async function load() {
  loading.value = true
  error.value = ''

  try {
    const [map, list] = await Promise.all([inventoryApi.cabinet(), inventoryApi.shelfRuns()])

    board.value = map
    runs.value = list

    if (selected.value && !allCells.value.includes(selected.value)) selected.value = ''
  } catch (err) {
    error.value = errorMessage(err, 'Omborni yuklab bo‘lmadi.')
  } finally {
    loading.value = false
  }
}

/** Tovarni javonga qo'yadi yoki joyini bo'shatadi. */
async function place(item: CabinetItem, cell: string) {
  saving.value = item.variant

  try {
    await inventoryApi.place(item.variant, cell)

    toast.show(cell ? `${item.name} — ${cell} javoniga qo‘yildi` : `${item.name} — joyi bo‘shatildi`)

    await load()

    if (cell) selected.value = cell
  } catch (err) {
    toast.show(errorMessage(err, 'Joyni saqlab bo‘lmadi.'), 'error')
  } finally {
    saving.value = 0
  }
}

// --- Javon qatorlarini sozlash --------------------------------------------

function startRun(run?: ShelfRun) {
  draft.value = run
    ? { id: run.id, code: run.code, name: run.name, shelves: run.shelves }
    : { code: '', name: '', shelves: 1 }

  setupOpen.value = true
}

async function saveRun() {
  if (!draft.value.code.trim() || !draft.value.name.trim()) return

  try {
    await inventoryApi.saveShelfRun({
      ...draft.value,
      code: draft.value.code.trim().toUpperCase(),
      position: draft.value.id ? undefined : runs.value.length,
    })

    await load()

    draft.value = { code: '', name: '', shelves: 1 }
    toast.show('Javon qatori saqlandi')
  } catch (err) {
    toast.show(errorMessage(err, 'Saqlab bo‘lmadi.'), 'error')
  }
}

async function removeRun(run: ShelfRun) {
  if (!window.confirm(`«${run.code} — ${run.name}» o‘chirilsinmi?`)) return

  try {
    await inventoryApi.removeShelfRun(run.id)
    await load()
    toast.show('Javon qatori o‘chirildi')
  } catch (err) {
    toast.show(errorMessage(err, 'O‘chirib bo‘lmadi.'), 'error')
  }
}

onMounted(load)
</script>

<template>
  <section class="app-section active">
    <p v-if="error" class="load-error">{{ error }}</p>

    <!-- Javonlar kiritilmagan: bo'sh ro'yxat chizishdan ko'ra ochiq aytgan ma'qul -->
    <div v-if="board && !ready && !setupOpen" class="table-card card-padded">
      <h3 class="card-title">Ombor javonlari kiritilmagan</h3>

      <p class="field-hint">
        Omborda javonlar devorlar bo‘ylab ketadi. Har devorni alohida qator qilib
        kiriting: harfi, qayerdaligi va nechta javon borligi. Shundan keyin qabulda
        tovarning joyi so‘raladi va bu yerda xarita chiziladi.
      </p>

      <button v-if="auth.isAdmin" class="button button-gradient" type="button" @click="startRun()">
        Javon qatorlarini kiritish
      </button>
    </div>

    <!-- Sozlash: qatorlar ro'yxati va qo'shish shakli -->
    <div v-if="setupOpen" class="table-card card-padded setup">
      <div class="card-head">
        <h3 class="card-title">Javon qatorlari</h3>

        <button class="button button-outline" type="button" @click="setupOpen = false">
          Yopish
        </button>
      </div>

      <table v-if="runs.length" class="data-table">
        <thead>
          <tr>
            <th>Harf</th>
            <th>Qayerda</th>
            <th class="num">Javonlar</th>
            <th></th>
          </tr>
        </thead>

        <tbody>
          <tr v-for="run in runs" :key="run.id">
            <td><strong>{{ run.code }}</strong></td>
            <td>{{ run.name }}</td>
            <td class="num">{{ run.shelves }}</td>
            <td class="num row-actions">
              <button class="button button-outline" type="button" @click="startRun(run)">
                Tahrirlash
              </button>
              <button class="button button-outline" type="button" @click="removeRun(run)">
                O‘chirish
              </button>
            </td>
          </tr>
        </tbody>
      </table>

      <div class="run-form">
        <div class="field narrow">
          <label>Harfi</label>
          <input v-model="draft.code" type="text" maxlength="1" aria-label="Qator harfi" />
        </div>

        <div class="field">
          <label>Qayerda</label>
          <input
            v-model="draft.name"
            type="text"
            placeholder="O‘ng devor"
            aria-label="Javon qatori qayerda"
          />
        </div>

        <div class="field narrow">
          <label>Javonlar</label>
          <input
            v-model.number="draft.shelves"
            type="number"
            min="1"
            max="30"
            aria-label="Javonlar soni"
          />
        </div>

        <button class="button button-gradient" type="button" @click="saveRun">
          {{ draft.id ? 'Saqlash' : 'Qo‘shish' }}
        </button>
      </div>

      <p class="field-hint">
        Raqam tepadan boshlanadi: <strong>D1</strong> — o‘ng devorning eng tepadagi javoni.
      </p>
    </div>

    <div v-if="board && ready" class="cabinet">
      <div class="table-card card-padded board">
        <div class="card-head">
          <h3 class="card-title">Ombor javonlari</h3>

          <button
            v-if="auth.isAdmin"
            class="button button-outline"
            type="button"
            @click="setupOpen = !setupOpen"
          >
            Qatorlarni sozlash
          </button>
        </div>

        <div class="runs">
          <div v-for="run in board.runs" :key="run.code" class="run">
            <div class="run-head">
              <span class="run-letter">{{ run.code }}</span>
              <span class="run-where">{{ run.name }}</span>
            </div>

            <div class="shelves">
              <button
                v-for="shelf in run.shelves"
                :key="shelf.cell"
                class="shelf"
                :class="{ filled: shelf.items.length > 0, chosen: shelf.cell === selected }"
                type="button"
                :aria-label="`${shelf.cell}: ${total(shelf.items)} dona`"
                @click="selected = shelf.cell"
              >
                <span class="shelf-cell">{{ shelf.cell }}</span>
                <strong v-if="shelf.items.length" class="shelf-count">
                  {{ total(shelf.items) }}
                </strong>
              </button>
            </div>
          </div>
        </div>
      </div>

      <aside class="table-card card-padded chosen-cell">
        <h3 class="card-title">{{ selected || 'Javonni tanlang' }}</h3>

        <p v-if="chosen" class="field-hint">{{ chosen.run.name }}</p>

        <p v-if="!selected" class="field-hint">
          Ro‘yxatdan javonni bosing — ichida nima turgani shu yerda ko‘rinadi.
        </p>

        <p v-else-if="!chosen?.shelf.items.length" class="field-hint">Javon bo‘sh.</p>

        <ul v-else class="cell-items">
          <li v-for="item in chosen.shelf.items" :key="item.variant">
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
        Bu tovarlar omborda turibdi, lekin qaysi javonda ekani yozilmagan.
      </p>

      <ul class="cell-items">
        <li v-for="item in unplaced" :key="item.variant">
          <div class="cell-item">
            <strong>{{ item.name }}</strong>
            <small class="cell-sub">{{ item.label || '—' }} · {{ item.quantity }} dona</small>
          </div>

          <select
            v-if="auth.isAdmin && ready"
            value=""
            :disabled="saving === item.variant"
            :aria-label="`${item.name}: joyini belgilash`"
            @change="place(item, ($event.target as HTMLSelectElement).value)"
          >
            <option value="">Javonni tanlang</option>
            <option v-for="cell in allCells" :key="cell" :value="cell">{{ cell }}</option>
          </select>
        </li>
      </ul>
    </div>

    <!-- Javon qatori o'chirilgan bo'lsa, tovar o'sha yerda turganini
         jimgina yo'qotib bo'lmaydi -->
    <div v-if="outside.length" class="table-card card-padded warning">
      <h3 class="card-title">Ro‘yxatdan tashqarida ({{ outside.length }} manzil)</h3>

      <p class="field-hint">
        Bu manzillar endi mavjud emas — javon qatori o‘chirilgan yoki qisqartirilgan.
        Tovarni boshqa javonga ko‘chiring.
      </p>

      <ul class="cell-items">
        <li v-for="[cell, items] in outside" :key="cell">
          <div class="cell-item">
            <strong>{{ cell }}</strong>
            <small class="cell-sub">{{ items.map((item) => item.name).join(', ') }}</small>
          </div>

          <select
            v-if="auth.isAdmin && ready"
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
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

/* Qatorlar yonma-yon: har biri o'z bo'yi bilan, chunki devorlarda
   javonlar soni teng emas */
.runs {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  margin-top: 12px;
}

.run {
  display: flex;
  flex-direction: column;
  gap: 8px;
  min-width: 132px;
}

.run-head {
  display: flex;
  align-items: center;
  gap: 8px;
}

.run-letter {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 26px;
  height: 26px;
  flex: none;
  border-radius: var(--radius);
  background: var(--accent);
  color: var(--accent-text);
  font-weight: 700;
}

.run-where {
  color: var(--text-secondary);
  font-size: 13px;
}

.shelves {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.shelf {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 7px 10px;
  border: 1px solid var(--border);
  border-radius: var(--radius);
  background: var(--surface-soft);
  cursor: pointer;
}

.shelf:hover {
  border-color: var(--accent);
}

/* To'lgan javon ko'zga tashlansin: bo'sh omborda tovarni izlab
   har javonni bosib chiqish kerak bo'lmasin */
.shelf.filled {
  border-color: var(--accent);
  background: var(--accent-soft);
}

.shelf.chosen {
  outline: 2px solid var(--accent);
  outline-offset: 1px;
}

.shelf-cell {
  color: var(--text-secondary);
  font-size: 13px;
}

.shelf-count {
  font-size: 15px;
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

.setup {
  margin-bottom: 12px;
}

.run-form {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-end;
  gap: 10px;
  margin-top: 12px;
}

.run-form .field {
  flex: 1 1 180px;
  min-width: 0;
}

.run-form .field.narrow {
  flex: 0 0 96px;
}

.row-actions .button {
  margin-left: 6px;
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
