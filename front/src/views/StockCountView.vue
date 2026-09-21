<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'

import ScanField from '@/components/ScanField.vue'
import { catalogApi } from '@/api/catalog'
import { errorMessage } from '@/api/client'
import { inventoryApi } from '@/api/inventory'
import { formatDate, todayIso } from '@/utils/date'
import { differingLines, findScanned, uncountedLines, type CountLine } from '@/utils/stockCount'
import type { Category, StockCount } from '@/types'

/** Oxirgi o'zgarishdan keyin shuncha kutib saqlanadi */
const AUTOSAVE_DELAY = 3000

const counts = ref<StockCount[]>([])
const categories = ref<Category[]>([])
const route = useRoute()
const opened = ref<StockCount | null>(null)

const loading = ref(false)
const confirming = ref(false)
const error = ref('')
const notice = ref('')

const editorOpen = ref(false)
const scanner = ref<InstanceType<typeof ScanField> | null>(null)
const draft = ref({ date: todayIso(), category: null as number | null, note: '' })
const lines = ref<CountLine[]>([])

/** Serverdagi qoralama. Birinchi o'zgarishda yaratiladi. */
const draftId = ref<number | null>(null)
const draftNumber = ref('')
const savedAt = ref<Date | null>(null)
const saving = ref(false)

let timer: ReturnType<typeof setTimeout> | null = null

const uncounted = computed(() => uncountedLines(lines.value))
const differing = computed(() => differingLines(lines.value))

const savedLabel = computed(() => {
  if (saving.value) return 'Saqlanmoqda…'
  if (!savedAt.value) return ''

  const time = savedAt.value.toLocaleTimeString('uz-UZ', {
    hour: '2-digit',
    minute: '2-digit',
  })

  return `Saqlandi ${time}`
})

async function load() {
  loading.value = true
  error.value = ''

  try {
    const [page, categoryList] = await Promise.all([
      inventoryApi.counts(),
      catalogApi.categories(),
    ])

    counts.value = page.results
    categories.value = categoryList
  } catch (err) {
    error.value = errorMessage(err, 'Inventarizatsiyalarni yuklab bo‘lmadi.')
  } finally {
    loading.value = false
  }
}

/**
 * Tanlangan kategoriya bo'yicha qatorlarni yig'adi.
 *
 * Sanalgan soni **noldan** boshlanadi: tizimdagi qoldiq bilan
 * to'ldirilsa, sanalmagan tovar «bor» bo'lib qolar va kamomad umuman
 * ko'rinmasdi.
 */
async function fillLines() {
  lines.value = []

  let page = 1

  for (;;) {
    const result = await catalogApi.variants({
      category: draft.value.category ?? undefined,
      active: 'true',
      page,
    })

    lines.value.push(
      ...result.results.map((variant) => ({
        variant: variant.id,
        barcode: variant.barcode,
        product_name: variant.product_name,
        variant_label: variant.label,
        expected_quantity: variant.stock_quantity,
        counted_quantity: 0,
      })),
    )

    if (!result.next) break

    page += 1
  }
}

function resetEditor() {
  if (timer) {
    clearTimeout(timer)
    timer = null
  }

  draftId.value = null
  draftNumber.value = ''
  savedAt.value = null
  lines.value = []
}

async function openEditor() {
  resetEditor()

  editorOpen.value = true
  opened.value = null
  notice.value = ''
  error.value = ''
  draft.value = { date: todayIso(), category: null, note: '' }

  try {
    await fillLines()
  } catch (err) {
    error.value = errorMessage(err, 'Tovarlar ro‘yxatini yuklab bo‘lmadi.')
  }

  scanner.value?.focus()
}

/** Boshlangan qoralamani davom ettiradi: sanalgan sonlar tiklanadi. */
async function continueDraft(count: StockCount) {
  resetEditor()

  editorOpen.value = true
  opened.value = null
  notice.value = ''
  error.value = ''

  draft.value = {
    date: count.date,
    category: count.category,
    note: count.note,
  }

  try {
    const full = await inventoryApi.count(count.id)

    // Joriy qoldiq va shtrix-kodlar katalogdan olinadi (qoralamada ular yo'q)
    await fillLines()

    const counted = new Map(full.lines.map((line) => [line.variant, line.counted_quantity]))

    for (const line of lines.value) {
      line.counted_quantity = counted.get(line.variant) ?? 0
    }

    draftId.value = full.id
    draftNumber.value = full.number
    savedAt.value = new Date()
  } catch (err) {
    error.value = errorMessage(err, 'Qoralamani ochib bo‘lmadi.')
  }

  scanner.value?.focus()
}

/** Har skan — mos qatorga +1. */
function onScan(code: string) {
  error.value = ''

  const result = findScanned(lines.value, code)
  const line = result.ok ? lines.value[result.index] : undefined

  if (!result.ok) {
    error.value = result.message
  } else if (line) {
    line.counted_quantity += 1
    notice.value = `${line.product_name} ${line.variant_label} — ${line.counted_quantity} dona`
    scheduleSave()
  }

  scanner.value?.focus()
}

function scheduleSave() {
  if (timer) clearTimeout(timer)

  timer = setTimeout(flushSave, AUTOSAVE_DELAY)
}

/** Qoralamani serverga yozadi. Birinchi chaqiruvda hujjat yaratiladi. */
async function flushSave() {
  if (timer) {
    clearTimeout(timer)
    timer = null
  }

  if (!lines.value.length) return

  // Avvalgi saqlash tugamagan bo'lsa, biroz kutib qayta urinamiz
  if (saving.value) {
    timer = setTimeout(flushSave, 1000)
    return
  }

  saving.value = true

  const payload = lines.value.map((line) => ({
    variant: line.variant,
    counted_quantity: line.counted_quantity,
  }))

  try {
    if (draftId.value === null) {
      const created = await inventoryApi.createCount({
        date: draft.value.date,
        category: draft.value.category,
        note: draft.value.note,
        lines: payload,
      })

      draftId.value = created.id
      draftNumber.value = created.number
      await load()
    } else {
      await inventoryApi.updateCount(draftId.value, {
        note: draft.value.note,
        lines: payload,
      })
    }

    savedAt.value = new Date()
  } catch (err) {
    error.value = errorMessage(err, 'Avtomatik saqlanmadi. Internetni tekshiring.')
  } finally {
    saving.value = false
  }
}

async function closeEditor() {
  await flushSave()

  editorOpen.value = false
  resetEditor()
  await load()
}

async function onConfirm() {
  if (!lines.value.length || confirming.value) return

  // Sanalmagan qatorlar nol bo'lib yoziladi — bu kamomad demakdir
  if (uncounted.value > 0) {
    const ok = window.confirm(
      `${uncounted.value} ta qator hali sanalmagan (0 turibdi).\n\n` +
        'Tasdiqlansa, ular yo‘q hisoblanadi va qoldiqdan chiqariladi.\n' +
        'Davom etasizmi?',
    )

    if (!ok) return
  }

  confirming.value = true
  error.value = ''

  try {
    await flushSave()

    if (draftId.value === null) {
      error.value = 'Avval hech bo‘lmasa bitta tovarni sanang.'
      return
    }

    const confirmed = await inventoryApi.confirmCount(draftId.value)

    notice.value = `${confirmed.number} tasdiqlandi — qoldiq to‘g‘rilandi.`
    editorOpen.value = false
    resetEditor()
    await load()
  } catch (err) {
    error.value = errorMessage(err, 'Tasdiqlab bo‘lmadi.')
  } finally {
    confirming.value = false
  }
}

async function onOpen(count: StockCount) {
  opened.value = await inventoryApi.count(count.id)
  editorOpen.value = false
}

async function onConfirmFromList(count: StockCount) {
  if (!window.confirm(`${count.number} tasdiqlansinmi? Qoldiq sanalgan songa tenglashtiriladi.`)) {
    return
  }

  try {
    await inventoryApi.confirmCount(count.id)
    notice.value = `${count.number} tasdiqlandi.`
    opened.value = null
    await load()
  } catch (err) {
    error.value = errorMessage(err, 'Tasdiqlab bo‘lmadi.')
  }
}

/** Mahsulotning qoldiq tarixidan kelingan bo'lsa (`?open=<id>`) — o'sha sanoq ochiladi */
onMounted(async () => {
  await load()

  const id = Number(route.query.open)

  if (id) await onOpen({ id } as StockCount)
})

// Sahifadan chiqishda saqlanmagan o'zgarish qolmasin
onBeforeUnmount(() => {
  if (timer) clearTimeout(timer)
})
</script>

<template>
  <section class="app-section active">
    <div class="section-toolbar">
      <div class="filters"></div>

      <button class="button button-gradient" type="button" @click="openEditor">
        <svg><use href="#i-plus" /></svg>
        <span>Yangi inventarizatsiya</span>
      </button>
    </div>

    <p v-if="error" class="load-error">{{ error }}</p>
    <p v-if="notice" class="notice">{{ notice }}</p>

    <div v-if="editorOpen" class="table-card card-padded editor">
      <p class="closed-shop">
        <strong>Do‘kon yopiq bo‘lganda sanang.</strong>
        Sanoq davomida sotuv bo‘lsa, qoldiq o‘zgaradi va soxta farqlar chiqadi:
        sanab bo‘lingan tovar sotilsa, tizimda kamomad bo‘lib ko‘rinadi.
      </p>

      <div class="editor-head">
        <div class="field">
          <label>Sana</label>
          <input v-model="draft.date" type="date" :disabled="draftId !== null" />
        </div>

        <div class="field">
          <label>Kategoriya</label>
          <select v-model="draft.category" :disabled="draftId !== null" @change="fillLines">
            <option :value="null">Hammasi</option>
            <option v-for="item in categories" :key="item.id" :value="item.id">
              {{ item.name }}
            </option>
          </select>
          <small v-if="draftId !== null" class="field-hint">
            Sanoq boshlangach kategoriyani o‘zgartirib bo‘lmaydi.
          </small>
        </div>

        <div class="field">
          <label>Izoh</label>
          <input v-model="draft.note" type="text" @change="scheduleSave" />
        </div>
      </div>

      <ScanField
        ref="scanner"
        placeholder="Tovarni skanerlang — har skan +1 dona"
        @scan="onScan"
      />

      <div class="counters">
        <span v-if="draftNumber" class="doc-number">{{ draftNumber }}</span>
        <span>Jami qator: <strong>{{ lines.length }}</strong></span>
        <span :class="{ warn: uncounted > 0 }">
          Sanalmagan: <strong>{{ uncounted }}</strong>
        </span>
        <span>Farqli: <strong>{{ differing }}</strong></span>
        <span class="saved">{{ savedLabel }}</span>
      </div>

      <div class="table-scroll tall">
        <table class="data-table">
          <thead>
            <tr>
              <th>Mahsulot</th>
              <th class="num">Tizimda</th>
              <th class="num">Sanaldi</th>
              <th class="num">Farq</th>
            </tr>
          </thead>

          <tbody>
            <tr v-if="!lines.length">
              <td colspan="4" class="empty-state">Bu kategoriyada tovar yo‘q.</td>
            </tr>

            <tr
              v-for="line in lines"
              v-else
              :key="line.variant"
              :class="{ changed: line.counted_quantity !== line.expected_quantity }"
            >
              <td>
                <strong>{{ line.product_name }}</strong>
                <small class="cell-sub">{{ line.variant_label }}</small>
              </td>

              <td class="num">{{ line.expected_quantity }}</td>

              <td class="num">
                <input
                  v-model.number="line.counted_quantity"
                  class="cart-number"
                  type="number"
                  min="0"
                  @change="scheduleSave"
                />
              </td>

              <td class="num">{{ line.counted_quantity - line.expected_quantity }}</td>
            </tr>
          </tbody>
        </table>
      </div>

      <div class="editor-footer">
        <span class="footer-hint">O‘zgarishlar o‘zi saqlanadi — keyin davom ettirsa bo‘ladi.</span>

        <button class="button button-outline" type="button" @click="closeEditor">Yopish</button>

        <button
          class="button button-gradient"
          type="button"
          :disabled="confirming"
          @click="onConfirm"
        >
          {{ confirming ? 'Tasdiqlanmoqda…' : 'Tasdiqlash' }}
        </button>
      </div>
    </div>

    <div class="table-card">
      <div class="table-scroll">
        <table class="data-table">
          <thead>
            <tr>
              <th>Hujjat</th>
              <th>Sana</th>
              <th>Kategoriya</th>
              <th>Holati</th>
              <th></th>
            </tr>
          </thead>

          <tbody>
            <tr v-if="loading">
              <td colspan="5" class="empty-state">Yuklanmoqda…</td>
            </tr>

            <tr v-else-if="!counts.length">
              <td colspan="5" class="empty-state">Inventarizatsiya o‘tkazilmagan.</td>
            </tr>

            <tr v-for="count in counts" v-else :key="count.id">
              <td><strong>{{ count.number }}</strong></td>
              <td>{{ formatDate(count.date) }}</td>
              <td>{{ count.category_name ?? 'Hammasi' }}</td>
              <td>
                <span class="pill" :class="count.status === 'confirmed' ? 'pill-green' : 'pill-grey'">
                  {{ count.status_display }}
                </span>
              </td>

              <td class="num row-actions">
                <button
                  v-if="count.status === 'draft'"
                  class="button button-outline"
                  type="button"
                  @click="continueDraft(count)"
                >
                  Davom ettirish
                </button>

                <button class="button button-outline" type="button" @click="onOpen(count)">
                  Ko‘rish
                </button>

                <button
                  v-if="count.status === 'draft'"
                  class="button button-gradient"
                  type="button"
                  @click="onConfirmFromList(count)"
                >
                  Tasdiqlash
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <div v-if="opened" class="table-card card-padded">
      <h3>{{ opened.number }}</h3>

      <table class="data-table">
        <thead>
          <tr>
            <th>Mahsulot</th>
            <th class="num">Tizimda</th>
            <th class="num">Sanaldi</th>
            <th class="num">Farq</th>
          </tr>
        </thead>

        <tbody>
          <tr v-for="line in opened.lines" :key="line.variant">
            <td>
              <strong>{{ line.product_name }}</strong>
              <small class="cell-sub">{{ line.variant_label }}</small>
            </td>
            <td class="num">{{ line.expected_quantity }}</td>
            <td class="num">{{ line.counted_quantity }}</td>
            <td class="num">{{ line.difference }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </section>
</template>

<style scoped>
.editor {
  margin-bottom: 12px;
}

.closed-shop {
  margin: 0 0 12px;
  padding: 10px 12px;
  border: 1px solid var(--orange);
  border-radius: var(--radius);
  background: var(--orange-soft);
  font-size: 14px;
}

.editor-head {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 10px;
  margin-bottom: 8px;
}

.counters {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 16px;
  margin: 10px 0;
  font-size: 14px;
}

.counters .warn strong {
  color: var(--red);
}

.doc-number {
  font-weight: 700;
}

.saved {
  margin-left: auto;
  color: var(--green);
  font-weight: 600;
}

.table-scroll.tall {
  max-height: 360px;
  overflow-y: auto;
}

.cart-number {
  width: 90px;
  text-align: right;
}

.changed td {
  background: var(--accent-soft);
}

.editor-footer {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid var(--border);
}

.footer-hint {
  margin-right: auto;
  color: var(--text-muted);
  font-size: 13px;
}

.row-actions .button {
  margin-left: 6px;
}
</style>
