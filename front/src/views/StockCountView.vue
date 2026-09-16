<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'

import { catalogApi } from '@/api/catalog'
import { errorMessage } from '@/api/client'
import { inventoryApi } from '@/api/inventory'
import { formatDate, todayIso } from '@/utils/date'
import type { Category, StockCount, StockCountLine } from '@/types'

interface EditorLine extends StockCountLine {
  product_name: string
  variant_label: string
  expected_quantity: number
}

const counts = ref<StockCount[]>([])
const categories = ref<Category[]>([])
const opened = ref<StockCount | null>(null)

const loading = ref(false)
const saving = ref(false)
const error = ref('')
const notice = ref('')

const editorOpen = ref(false)
const draft = ref({ date: todayIso(), category: null as number | null, note: '' })
const lines = ref<EditorLine[]>([])

const differences = computed(() =>
  lines.value.filter((line) => line.counted_quantity !== line.expected_quantity),
)

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

/** Tanlangan kategoriya bo'yicha hamma variantni qatorlarga yig'adi. */
async function fillLines() {
  error.value = ''
  lines.value = []

  let page = 1

  // Katalog sahifalab keladi — hammasi yig'iladi
  for (;;) {
    const result = await catalogApi.variants({
      category: draft.value.category ?? undefined,
      active: 'true',
      page,
    })

    lines.value.push(
      ...result.results.map((variant) => ({
        variant: variant.id,
        product_name: variant.product_name,
        variant_label: variant.label,
        expected_quantity: variant.stock_quantity,
        counted_quantity: variant.stock_quantity,
      })),
    )

    if (!result.next) break

    page += 1
  }
}

async function openEditor() {
  editorOpen.value = true
  opened.value = null
  draft.value = { date: todayIso(), category: null, note: '' }

  await fillLines()
}

async function onSave(confirmAfter: boolean) {
  if (!lines.value.length || saving.value) return

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
  if (!window.confirm(`${count.number} tasdiqlansinmi? Qoldiq hisoblangan songa tenglashtiriladi.`)) {
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
            <option v-for="item in categories" :key="item.id" :value="item.id">{{ item.name }}</option>
          </select>
        </div>

        <div class="field">
          <label>Izoh</label>
          <input v-model="draft.note" type="text" />
        </div>
      </div>

      <p class="field-hint">
        Sanab chiqilgan sonni kiriting. Farqi bo‘lganlar ajratib ko‘rsatiladi
        ({{ differences.length }} ta).
      </p>

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
                <input v-model.number="line.counted_quantity" class="cart-number" type="number" min="0" />
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

.table-scroll.tall {
  max-height: 420px;
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
