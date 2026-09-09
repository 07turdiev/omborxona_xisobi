<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'

import api from '@/api/client'
import { tenantsApi } from '@/api/tenants'
import { useAuthStore } from '@/stores/auth'
import { useThemeStore } from '@/stores/theme'
import type { TenantSettings } from '@/types'

const auth = useAuthStore()
const theme = useThemeStore()

const loading = ref(false)
const saving = ref(false)
const saved = ref(false)
const errors = ref<Record<string, string[]>>({})

const form = reactive<Partial<TenantSettings>>({})
const info = ref<TenantSettings | null>(null)

/** Valyutalar va kurslar — sozlamalar sahifasidan boshqariladi. */
interface Currency {
  id: number
  code: string
  name: string
  symbol: string
  is_base: boolean
  is_active: boolean
}

interface Rate {
  id: number
  currency: number
  rate: string
  valid_from: string
  source: string
}

const currencies = ref<Currency[]>([])
const rates = ref<Rate[]>([])
const rateForm = reactive({ currency: null as number | null, rate: '', valid_from: '' })
const rateError = ref('')

const canManage = computed(() => {
  const role = auth.user?.current_tenant?.role
  return role === 'owner' || role === 'manager'
})

async function load() {
  loading.value = true

  try {
    info.value = await tenantsApi.settings()
    Object.assign(form, info.value)

    const [currencyData, rateData] = await Promise.all([
      api.get<{ results: Currency[] }>('/currencies/'),
      api.get<{ results: Rate[] }>('/exchange-rates/'),
    ])

    currencies.value = currencyData.data.results
    rates.value = rateData.data.results
  } catch {
    // Valyuta endpointlari hali ulanmagan bo'lishi mumkin — sozlamalar
    // baribir ko'rsatiladi
  } finally {
    loading.value = false
  }
}

onMounted(load)

async function onSave() {
  errors.value = {}
  saved.value = false
  saving.value = true

  try {
    info.value = await tenantsApi.saveSettings(form)
    Object.assign(form, info.value)
    saved.value = true

    // Sidebar'dagi tashkilot nomi yangilansin
    await auth.fetchMe()

    setTimeout(() => (saved.value = false), 3000)
  } catch (err) {
    const data = (err as { response?: { data?: Record<string, string[]> } }).response?.data
    errors.value = data ?? { detail: ['Saqlab bo‘lmadi.'] }
  } finally {
    saving.value = false
  }
}

async function onAddRate() {
  rateError.value = ''

  if (!rateForm.currency || !rateForm.rate || !rateForm.valid_from) {
    rateError.value = 'Barcha maydonlarni to‘ldiring.'
    return
  }

  try {
    await api.post('/exchange-rates/', { ...rateForm, source: 'Qo‘lda' })
    rates.value = (await api.get<{ results: Rate[] }>('/exchange-rates/')).data.results
    rateForm.rate = ''
  } catch (err) {
    const data = (err as { response?: { data?: Record<string, string[]> } }).response?.data
    rateError.value = Object.values(data ?? {}).flat()[0] ?? 'Kurs qo‘shilmadi.'
  }
}

function currencyCode(id: number): string {
  return currencies.value.find((c) => c.id === id)?.code ?? '—'
}

const fieldError = (field: string): string => errors.value[field]?.[0] ?? ''
</script>

<template>
  <section class="app-section active">
    <p v-if="loading" class="empty-state">Yuklanmoqda…</p>

    <template v-else>
      <div v-if="!canManage" class="notice">
        Sozlamalarni o‘zgartirish uchun <strong>egasi</strong> yoki
        <strong>menejer</strong> roli kerak.
      </div>

      <!-- Tashkilot -->
      <div class="table-card">
        <h3>Tashkilot</h3>

        <div class="form-grid three">
          <div class="field span-2">
            <label>Nomi</label>
            <input v-model="form.name" :disabled="!canManage" />
            <small v-if="fieldError('name')" class="field-error">
              {{ fieldError('name') }}
            </small>
          </div>

          <div class="field">
            <label>Qisqa nomi</label>
            <input :value="form.slug" disabled />
            <small class="field-hint">O‘zgartirilmaydi — havolalarda ishlatiladi</small>
          </div>

          <div class="field">
            <label>Faoliyat turi</label>
            <select v-model="form.business_type" :disabled="!canManage">
              <option value="construction">Qurilish mollari</option>
              <option value="clothing">Kiyim-kechak</option>
              <option value="grocery">Oziq-ovqat</option>
              <option value="general">Aralash / boshqa</option>
            </select>
          </div>

          <div class="field">
            <label>INN</label>
            <input v-model="form.inn" :disabled="!canManage" />
          </div>

          <div class="field">
            <label>Telefon</label>
            <input v-model="form.phone" :disabled="!canManage" />
          </div>

          <div class="field full">
            <label>Manzil</label>
            <input v-model="form.address" :disabled="!canManage" />
          </div>
        </div>
      </div>

      <!-- Hujjat raqamlari -->
      <div class="table-card">
        <h3>Hujjat raqamlari</h3>

        <p class="hint">
          Prefiks o‘zgarsa <strong>eski hujjatlar o‘z raqamini saqlaydi</strong> —
          raqam yaratilishda bir marta yoziladi. Namuna:
          <code>{{ form.purchase_prefix }}-2026-000001</code>
        </p>

        <div class="form-grid three">
          <div class="field">
            <label>Kirim</label>
            <input v-model="form.purchase_prefix" :disabled="!canManage" />
            <small v-if="fieldError('purchase_prefix')" class="field-error">
              {{ fieldError('purchase_prefix') }}
            </small>
          </div>

          <div class="field">
            <label>Sotuv</label>
            <input v-model="form.sale_prefix" :disabled="!canManage" />
            <small v-if="fieldError('sale_prefix')" class="field-error">
              {{ fieldError('sale_prefix') }}
            </small>
          </div>

          <div class="field">
            <label>Ko‘chirish</label>
            <input v-model="form.transfer_prefix" :disabled="!canManage" />
            <small v-if="fieldError('transfer_prefix')" class="field-error">
              {{ fieldError('transfer_prefix') }}
            </small>
          </div>
        </div>
      </div>

      <!-- Hisob-kitob -->
      <div class="table-card">
        <h3>Hisob-kitob</h3>

        <div class="form-grid three">
          <div class="field">
            <label>Asosiy valyuta</label>
            <input v-model="form.base_currency" maxlength="3" :disabled="!canManage" />
            <small class="field-hint">Hisobotlar shu valyutada jamlanadi</small>
            <small v-if="fieldError('base_currency')" class="field-error">
              {{ fieldError('base_currency') }}
            </small>
          </div>

          <div class="field">
            <label>Yaroqlilik ogohlantirishi</label>
            <input
              v-model.number="form.expiry_warning_days"
              type="number"
              min="1"
              max="365"
              :disabled="!canManage"
            />
            <small class="field-hint">
              Muddat tugashiga shuncha kun qolganda ogohlantiriladi
            </small>
          </div>

          <div class="field">
            <label>Xodimlar soni</label>
            <input :value="info?.member_count" disabled />
          </div>
        </div>
      </div>

      <div v-if="canManage" class="save-row">
        <span v-if="saved" class="saved-note">Saqlandi</span>
        <span v-if="fieldError('detail')" class="form-error">{{ fieldError('detail') }}</span>

        <button class="button button-gradient" type="button" :disabled="saving" @click="onSave">
          {{ saving ? 'Saqlanmoqda…' : 'Saqlash' }}
        </button>
      </div>

      <!-- Valyuta kurslari -->
      <div v-if="currencies.length" class="table-card">
        <h3>Valyuta kurslari</h3>

        <p class="hint">
          Kurs <strong>sanadan boshlab</strong> amal qiladi va keyingisi
          qo‘shilgunicha kuchda qoladi. Eski hujjatlar o‘sha kungi kurs bilan
          hisoblanadi — shuning uchun kurs o‘zgarganda eski foyda o‘zgarmaydi.
        </p>

        <table class="data-table">
          <thead>
            <tr>
              <th>Valyuta</th>
              <th class="num">Kurs</th>
              <th>Amal qila boshlaydi</th>
              <th>Manba</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="!rates.length">
              <td colspan="4" class="empty-state">Kurs qo‘shilmagan.</td>
            </tr>
            <tr v-for="rate in rates" :key="rate.id">
              <td>{{ currencyCode(rate.currency) }}</td>
              <td class="num">{{ Number(rate.rate).toLocaleString('uz-UZ') }}</td>
              <td>{{ rate.valid_from }}</td>
              <td>{{ rate.source || '—' }}</td>
            </tr>
          </tbody>
        </table>

        <div v-if="canManage" class="grant-row">
          <select v-model="rateForm.currency">
            <option :value="null" disabled>Valyuta…</option>
            <option
              v-for="c in currencies.filter((x) => !x.is_base)"
              :key="c.id"
              :value="c.id"
            >
              {{ c.code }} — {{ c.name }}
            </option>
          </select>

          <input v-model="rateForm.rate" type="number" step="0.000001" placeholder="12650" />
          <input v-model="rateForm.valid_from" type="date" />

          <button class="button button-gradient" type="button" @click="onAddRate">
            Kurs qo‘shish
          </button>
        </div>

        <p v-if="rateError" class="form-error">{{ rateError }}</p>
      </div>

      <!-- Interfeys -->
      <div class="table-card">
        <h3>Interfeys</h3>

        <div class="theme-row">
          <div>
            <strong>Tungi rejim</strong>
            <small>Ko‘z uchun qulayroq, kechqurun ishlash uchun</small>
          </div>

          <button class="button button-outline" type="button" @click="theme.toggle()">
            {{ theme.isDark ? 'Kunduzgi rejimga o‘tish' : 'Tungi rejimga o‘tish' }}
          </button>
        </div>
      </div>
    </template>
  </section>
</template>

<style scoped>
.table-card {
  margin-bottom: 14px;
  padding: 18px 20px;
}

.table-card h3 {
  margin-bottom: 14px;
  font-size: 15px;
}

.hint {
  margin-bottom: 14px;
  color: var(--text-secondary);
  font-size: 13px;
  line-height: 1.6;
}

.hint code {
  padding: 1px 5px;
  border-radius: var(--radius);
  background: var(--surface-hover);
  font-size: 12px;
}

.save-row {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 12px;
  margin-bottom: 14px;
}

.saved-note {
  color: var(--green);
  font-size: 13px;
  font-weight: 700;
}

.grant-row {
  display: flex;
  gap: 8px;
  align-items: center;
  margin-top: 14px;
  padding-top: 14px;
  border-top: 1px solid var(--border);
}

.theme-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.theme-row strong {
  display: block;
  font-size: 14px;
}

.theme-row small {
  display: block;
  margin-top: 2px;
  color: var(--text-muted);
  font-size: 12px;
}

.num {
  text-align: right;
}

.notice {
  margin-bottom: 14px;
  padding: 12px 14px;
  border: 1px solid var(--border);
  border-radius: var(--radius-small);
  background: var(--surface-soft);
  color: var(--text-secondary);
  font-size: 13px;
  line-height: 1.6;
}

.field-error {
  margin-top: 4px;
  color: var(--red);
  font-size: 12px;
}

.field-hint {
  margin-top: 4px;
  color: var(--text-muted);
  font-size: 12px;
}

.form-error {
  padding: 8px 12px;
  border-radius: var(--radius-small);
  background: var(--red-soft);
  color: var(--red);
  font-size: 13px;
}
</style>
