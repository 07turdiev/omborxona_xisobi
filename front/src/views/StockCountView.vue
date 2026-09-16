<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'

import ScanField from '@/components/ScanField.vue'
import { catalogApi } from '@/api/catalog'
import { errorMessage } from '@/api/client'
import { inventoryApi } from '@/api/inventory'
import { formatDate, todayIso } from '@/utils/date'
import { differingLines, findScanned, uncountedLines, type CountLine } from '@/utils/stockCount'
import type { Category, StockCount } from '@/types'

const counts = ref<StockCount[]>([])
const categories = ref<Category[]>([])
const opened = ref<StockCount | null>(null)

const loading = ref(false)
const saving = ref(false)
const error = ref('')
const notice = ref('')

const editorOpen = ref(false)
const scanner = ref<InstanceType<typeof ScanField> | null>(null)
const draft = ref({ date: todayIso(), category: null as number | null, note: '' })
const lines = ref<CountLine[]>([])

const uncounted = computed(() => uncountedLines(lines.value))
const differing = computed(() => differingLines(lines.value))

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
  error.value = ''
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

async function openEditor() {
  editorOpen.value = true
  opened.value = null
  notice.value = ''
  draft.value = { date: todayIso(), category: null, note: '' }

  await fillLines()
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
  }

  scanner.value?.focus()
}

async function onSave(confirmAfter: boolean) {
  if (!lines.value.length || saving.value) return

  // Sanalmagan qatorlar nol bo'lib yoziladi — bu kamomad demakdir.
  // Shuning uchun tasdiqlashdan oldin ogohlantiramiz.
  if (confirmAfter && uncounted.value > 0) {
    const ok = window.confirm(
      `${uncounted.value} ta qator hali sanalmagan (0 turibdi).\n\n` +
        'Tasdiqlansa, ular yo‘q hisoblanadi va qoldiqdan chiqariladi.\n' +
        'Davom etasizmi?',
    )

    if (!ok) return
  }

  saving.value = true
  error.value = ''
  notice.value = ''

  try {
    let count = await inventoryApi.createCount({
      date: draft.value.date,
      category: draft.value.category,
      note: draft.value.note,
      lines: lines.value.map((line) => ({
        variant: line.variant,
        counted_quantity: line.counted_quantity,
      })),
    })

    if (confirmAfter) {
      count = await inventoryApi.confirmCount(count.id)
      notice.value = `${count.number} tasdiqlandi — qoldiq to‘g‘rilandi.`
    } else {
      notice.value = `${count.number} qoralama sifatida saqlandi.`
    }

    editorOpen.value = false
    await load()
  } catch (err) {
    error.value = errorMessage(err, 'Saqlab bo‘lmadi.')
  } finally {
    saving.value = false
  }
}

async function onOpen(count: StockCount) {
  opened.value = await inventoryApi.count(count.id)
  editorOpen.value = false
}

async function onConfirm(count: StockCount) {
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

onMounted(load)
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
      <div class="editor-head">
        <div class="field">
          <label>Sana</label>
          <input v-model="draft.date" type="date" />
        </div>

        <div class="field">
          <label>Kategoriya</label>
          <select v-model="draft.category" @change="fillLines">
            <option :value="null">Hammasi</option>
            <option v-for="item in categories" :key="item.id" :value="item.id">
              {{ item.name }}
            </option>
          </select>
        </div>

        <div class="field">
          <label>Izoh</label>
          <input v-model="draft.note" type="text" />
        </div>
      </div>

      <ScanField
        ref="scanner"
        placeholder="Tovarni skanerlang — har skan +1 dona"
        @scan="onScan"
      />

      <div class="counters">
        <span>Jami qator: <strong>{{ lines.length }}</strong></span>
        <span :class="{ warn: uncounted > 0 }">
          Sanalmagan: <strong>{{ uncounted }}</strong>
        </span>
        <span>Farqli: <strong>{{ differing }}</strong></span>
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
                />
              </td>

              <td class="num">{{ line.counted_quantity - line.expected_quantity }}</td>
            </tr>
          </tbody>
        </table>
      </div>

      <div class="editor-footer">
        <button class="button button-outline" type="button" @click="editorOpen = false">
          Bekor qilish
        </button>

        <button class="button button-outline" type="button" :disabled="saving" @click="onSave(false)">
          Qoralama
        </button>

        <button class="button button-gradient" type="button" :disabled="saving" @click="onSave(true)">
          {{ saving ? 'Saqlanmoqda…' : 'Saqlash va tasdiqlash' }}
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
                <button class="button button-outline" type="button" @click="onOpen(count)">
                  Ko‘rish
                </button>

                <button
                  v-if="count.status === 'draft'"
                  class="button button-gradient"
                  type="button"
                  @click="onConfirm(count)"
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

.editor-head {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 10px;
  margin-bottom: 8px;
}

.counters {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  margin: 10px 0;
  font-size: 13px;
}

.counters .warn strong {
  color: var(--red);
}

.table-scroll.tall {
  max-height: 380px;
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
  justify-content: flex-end;
  gap: 8px;
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid var(--border);
}

.row-actions .button {
  margin-left: 6px;
}
</style>
