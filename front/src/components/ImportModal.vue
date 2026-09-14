<script setup lang="ts">
import { computed, ref, watch } from 'vue'

import {
  importsApi,
  type ImportPreview,
  type ImportResult,
  type ImportRow,
  type ImportType,
} from '@/api/imports'

const props = defineProps<{ show: boolean; type: ImportType; title: string }>()
const emit = defineEmits<{ close: []; done: [result: ImportResult] }>()

/** Jadvalda ko'rsatiladigan qatorlar chegarasi — 5000 qatorli DOM sekinlashadi */
const ROW_LIMIT = 300

const file = ref<File | null>(null)
const preview = ref<ImportPreview | null>(null)
const result = ref<ImportResult | null>(null)

const checking = ref(false)
const committing = ref(false)
const downloading = ref(false)
const error = ref('')

const confirmDocuments = ref(true)
const allowDuplicate = ref(false)
const filter = ref<'all' | 'errors' | 'warnings'>('all')

const isDocument = computed(() => props.type === 'purchases' || props.type === 'sales')

watch(
  () => props.show,
  (open) => {
    if (!open) return

    file.value = null
    preview.value = null
    result.value = null
    error.value = ''
    confirmDocuments.value = true
    allowDuplicate.value = false
    filter.value = 'all'
  },
)

function messageOf(err: unknown, fallback: string): string {
  const detail = (err as { response?: { data?: { detail?: string | string[] } } }).response?.data
    ?.detail

  if (Array.isArray(detail)) return detail.join(' ')

  return detail || fallback
}

async function onTemplate() {
  downloading.value = true
  error.value = ''

  try {
    await importsApi.template(props.type)
  } catch {
    error.value = 'Shablonni yuklab bo‘lmadi.'
  } finally {
    downloading.value = false
  }
}

async function runPreview() {
  if (!file.value) return

  checking.value = true
  error.value = ''
  result.value = null

  try {
    preview.value = await importsApi.preview(props.type, file.value, confirmDocuments.value)
    allowDuplicate.value = false
  } catch (err) {
    preview.value = null
    error.value = messageOf(err, 'Faylni tekshirib bo‘lmadi.')
  } finally {
    checking.value = false
  }
}

function onFileChange(event: Event) {
  const input = event.target as HTMLInputElement

  file.value = input.files?.[0] ?? null
  input.value = ''

  runPreview()
}

// Qoralama rejimida qoldiq yetishmasligi xato emas, ogohlantirish —
// shuning uchun tekshiruv qayta o'tkaziladi
watch(confirmDocuments, () => {
  if (file.value) runPreview()
})

const canCommit = computed(
  () =>
    Boolean(preview.value?.can_commit) &&
    (!preview.value?.duplicate || allowDuplicate.value) &&
    !committing.value &&
    !checking.value,
)

async function onCommit() {
  if (!file.value || !canCommit.value) return

  committing.value = true
  error.value = ''

  try {
    result.value = await importsApi.commit(props.type, file.value, {
      confirm: confirmDocuments.value,
      allowDuplicate: allowDuplicate.value,
    })
    emit('done', result.value)
  } catch (err) {
    const response = (err as { response?: { status?: number; data?: Record<string, unknown> } })
      .response

    if (response?.data?.preview) {
      preview.value = response.data.preview as ImportPreview
    }

    if (response?.status === 409 && preview.value) {
      preview.value = {
        ...preview.value,
        duplicate: response.data?.duplicate as ImportPreview['duplicate'],
      }
    }

    error.value = messageOf(err, 'Import qilib bo‘lmadi.')
  } finally {
    committing.value = false
  }
}

const shownColumns = computed(() => preview.value?.columns.slice(0, 5) ?? [])

const filteredRows = computed<ImportRow[]>(() => {
  const rows = preview.value?.rows ?? []

  if (filter.value === 'errors') return rows.filter((row) => row.errors.length)
  if (filter.value === 'warnings') return rows.filter((row) => row.warnings.length)

  return rows
})

const ACTIONS: Record<ImportRow['action'], { label: string; pill: string }> = {
  create: { label: 'Yangi', pill: 'pill-green' },
  update: { label: 'Yangilanadi', pill: 'pill-blue' },
  skip: { label: 'O‘zgarishsiz', pill: 'pill-grey' },
  error: { label: 'Xato', pill: 'pill-red' },
}

const formatDate = (value: string) => new Date(value).toLocaleString('ru-RU')
</script>

<template>
  <div class="modal" :class="{ show }">
    <div class="modal-backdrop" @click="emit('close')"></div>

    <div class="modal-dialog import-dialog">
      <div class="modal-header">
        <div>
          <span class="modal-eyebrow">EXCEL IMPORT</span>
          <h3>{{ title }}</h3>
          <p>
            Avval fayl tekshiriladi va natija ko‘rsatiladi. Bitta xatoli qator bo‘lsa ham
            fayl saqlanmaydi.
          </p>
        </div>

        <button class="modal-close" type="button" @click="emit('close')">
          <svg><use href="#i-close" /></svg>
        </button>
      </div>

      <div class="modal-body">
        <!-- Natija -->
        <div v-if="result" class="notice import-done">
          <strong>Import yakunlandi.</strong>
          <template v-if="result.documents">
            {{ result.created }} ta hujjat
            {{ result.confirmed ? 'tasdiqlandi va qoldiqqa yozildi' : 'qoralama sifatida saqlandi' }}:
            {{ result.documents.map((doc) => doc.number).join(', ') }}
          </template>
          <template v-else>
            Yangi: {{ result.created }}, yangilandi: {{ result.updated }}.
          </template>
        </div>

        <template v-else>
          <div class="import-actions">
            <button
              class="button button-outline"
              type="button"
              :disabled="downloading"
              @click="onTemplate"
            >
              <svg><use href="#i-download" /></svg>
              <span>{{ downloading ? 'Tayyorlanmoqda…' : 'Shablon' }}</span>
            </button>

            <label class="button button-soft">
              <input
                type="file"
                accept=".xlsx,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                hidden
                @change="onFileChange"
              />
              <svg><use href="#i-import" /></svg>
              <span>{{ file ? 'Boshqa fayl' : 'Fayl tanlash' }}</span>
            </label>

            <span v-if="file" class="muted">{{ file.name }}</span>

            <label v-if="isDocument" class="import-check">
              <input v-model="confirmDocuments" type="checkbox" />
              Hujjatlarni darhol tasdiqlash (qoldiqqa yoziladi)
            </label>
          </div>

          <p v-if="checking" class="empty-state">Fayl tekshirilmoqda…</p>

          <template v-if="preview && !checking">
            <div class="import-stats">
              <div><span>Qatorlar</span><strong>{{ preview.total }}</strong></div>
              <div><span>To‘g‘ri</span><strong class="ok">{{ preview.valid }}</strong></div>
              <div><span>Xatoli</span><strong class="bad">{{ preview.invalid }}</strong></div>
              <div v-if="isDocument">
                <span>Hujjatlar</span><strong>{{ preview.summary.documents }}</strong>
              </div>
              <template v-else>
                <div><span>Yangi</span><strong>{{ preview.summary.create }}</strong></div>
                <div><span>Yangilanadi</span><strong>{{ preview.summary.update }}</strong></div>
              </template>
            </div>

            <div v-if="preview.missing_columns.length" class="notice notice-warning">
              Majburiy ustunlar topilmadi: <strong>{{ preview.missing_columns.join(', ') }}</strong>.
              Shablonni yuklab oling.
            </div>

            <div v-if="preview.unknown_columns.length" class="notice">
              Tanilmagan ustunlar hisobga olinmaydi: {{ preview.unknown_columns.join(', ') }}
            </div>

            <div v-if="preview.hidden_columns.length" class="notice">
              Ruxsatingiz yo‘qligi sababli hisobga olinmaydi:
              {{ preview.hidden_columns.join(', ') }}
            </div>

            <div v-if="preview.duplicate" class="notice notice-warning">
              Bu fayl avval import qilingan:
              {{ formatDate(preview.duplicate.imported_at) }},
              {{ preview.duplicate.user_name || '—' }}.
              <label class="import-check">
                <input v-model="allowDuplicate" type="checkbox" />
                Baribir qayta import qilish
              </label>
            </div>

            <div v-if="preview.rows.length" class="import-filter">
              <select v-model="filter">
                <option value="all">Barcha qatorlar</option>
                <option value="errors">Faqat xatolar ({{ preview.invalid }})</option>
                <option value="warnings">Ogohlantirishlar ({{ preview.with_warnings }})</option>
              </select>
            </div>

            <div v-if="preview.rows.length" class="table-scroll import-table">
              <table class="data-table">
                <thead>
                  <tr>
                    <th>Qator</th>
                    <th>Holat</th>
                    <th v-for="column in shownColumns" :key="column.key">{{ column.label }}</th>
                    <th>Izoh</th>
                  </tr>
                </thead>

                <tbody>
                  <tr v-for="row in filteredRows.slice(0, ROW_LIMIT)" :key="row.row">
                    <td>{{ row.row }}</td>
                    <td>
                      <span class="pill" :class="ACTIONS[row.action].pill">
                        {{ ACTIONS[row.action].label }}
                      </span>
                    </td>
                    <td v-for="column in shownColumns" :key="column.key">
                      {{ row.values[column.key] || '—' }}
                    </td>
                    <td class="import-messages">
                      <div v-for="message in row.errors" :key="message" class="bad">
                        {{ message }}
                      </div>
                      <div v-for="message in row.warnings" :key="message" class="warn">
                        {{ message }}
                      </div>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>

            <p v-if="filteredRows.length > ROW_LIMIT" class="field-hint">
              Birinchi {{ ROW_LIMIT }} ta qator ko‘rsatildi ({{ filteredRows.length }} dan).
            </p>
          </template>
        </template>

        <p v-if="error" class="form-error">{{ error }}</p>
      </div>

      <div class="modal-footer">
        <button class="button button-outline" type="button" @click="emit('close')">
          {{ result ? 'Yopish' : 'Bekor qilish' }}
        </button>

        <button
          v-if="!result"
          class="button button-gradient"
          type="button"
          :disabled="!canCommit"
          @click="onCommit"
        >
          {{ committing ? 'Saqlanmoqda…' : 'Import qilish' }}
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.import-dialog {
  width: min(1040px, calc(100vw - 32px));
  max-width: none;
}

.import-actions {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 10px;
  margin-bottom: 14px;
}

.import-check {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
}

.import-stats {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(110px, 1fr));
  gap: 8px;
  margin-bottom: 12px;
}

.import-stats > div {
  padding: 8px 12px;
  border: 1px solid var(--border, #e5e7eb);
  border-radius: 8px;
}

.import-stats span {
  display: block;
  font-size: 12px;
  color: var(--muted, #6b7280);
}

.import-stats strong {
  font-size: 18px;
}

.notice {
  margin-bottom: 10px;
}

.import-filter {
  margin: 6px 0 8px;
}

.import-table {
  max-height: 420px;
  overflow: auto;
}

.import-messages {
  min-width: 240px;
  font-size: 12px;
}

.ok {
  color: var(--green, #16a34a);
}

.bad {
  color: var(--red, #dc2626);
}

.warn {
  color: var(--orange, #d97706);
}

.import-done {
  line-height: 1.6;
}
</style>
