<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'

import { companiesApi } from '@/api/companies'
import type { Company, CompanyInput, CompanySummary } from '@/types'

const items = ref<Company[]>([])
const summary = ref<CompanySummary | null>(null)
const loading = ref(false)
const error = ref('')

const filters = reactive({ search: '', is_active: '' })

const modalOpen = ref(false)
const editing = ref<Company | null>(null)
const saving = ref(false)
const errors = ref<Record<string, string[]>>({})
const logoFile = ref<File | null>(null)
const logoPreview = ref<string | null>(null)

const LEGAL_FORMS = [
  { value: 'llc', label: 'MChJ' },
  { value: 'ip', label: 'YaTT' },
  { value: 'jsc', label: 'AJ' },
  { value: 'pe', label: 'XK' },
  { value: 'other', label: 'Boshqa' },
]

function emptyForm(): CompanyInput {
  return {
    name: '',
    short_name: '',
    code: '',
    legal_form: 'llc',
    business_type: 'general',
    base_currency: 'UZS',
    is_active: true,
    inn: '',
    registration_number: '',
    vat_code: '',
    director: '',
    phone: '',
    email: '',
    website: '',
    address: '',
    actual_address: '',
    bank_name: '',
    mfo: '',
    bank_account: '',
    notes: '',
    owner_username: '',
    owner_password: '',
    owner_first_name: '',
    owner_last_name: '',
  }
}

const form = reactive<CompanyInput>(emptyForm())

async function load() {
  loading.value = true
  error.value = ''

  try {
    const [list, totals] = await Promise.all([
      companiesApi.list(filters),
      companiesApi.summary(),
    ])

    items.value = list.results
    summary.value = totals
  } catch {
    error.value = 'Kompaniyalarni olishda xatolik.'
  } finally {
    loading.value = false
  }
}

onMounted(load)

let searchTimer: ReturnType<typeof setTimeout> | undefined

function onSearchInput() {
  clearTimeout(searchTimer)
  searchTimer = setTimeout(load, 300)
}

function openCreate() {
  editing.value = null
  errors.value = {}
  logoFile.value = null
  logoPreview.value = null
  Object.assign(form, emptyForm())
  modalOpen.value = true
}

function openEdit(company: Company) {
  editing.value = company
  errors.value = {}
  logoFile.value = null
  logoPreview.value = company.logo
  Object.assign(form, emptyForm(), company)
  modalOpen.value = true
}

function onLogoChange(event: Event) {
  const file = (event.target as HTMLInputElement).files?.[0] ?? null

  logoFile.value = file
  logoPreview.value = file ? URL.createObjectURL(file) : (editing.value?.logo ?? null)
}

async function onSubmit() {
  errors.value = {}
  saving.value = true

  const payload: CompanyInput = { ...form }

  // Egasi faqat yaratishda beriladi; keyin — kompaniyaning xodimlar bo'limidan
  if (editing.value) {
    delete payload.owner_username
    delete payload.owner_password
    delete payload.owner_first_name
    delete payload.owner_last_name
  }

  try {
    await companiesApi.save(payload, editing.value?.id, logoFile.value)
    modalOpen.value = false
    await load()
  } catch (err) {
    const data = (err as { response?: { data?: Record<string, string[]> } }).response?.data
    errors.value = data ?? { detail: ['Saqlab bo‘lmadi.'] }
  } finally {
    saving.value = false
  }
}

async function onToggleActive(company: Company) {
  const message = company.is_active
    ? `"${company.name}" faolsizlantirilsinmi?\n\nXodimlari tizimga kira olmaydi. ` +
      'Ma’lumotlar o‘chirilmaydi — keyin qayta faollashtirish mumkin.'
    : `"${company.name}" qayta faollashtirilsinmi?`

  if (!window.confirm(message)) return

  try {
    await companiesApi.save({ is_active: !company.is_active }, company.id)
    await load()
  } catch {
    error.value = 'Holatni o‘zgartirib bo‘lmadi.'
  }
}

const fieldError = (field: string): string => errors.value[field]?.[0] ?? ''
</script>

<template>
  <section class="app-section active">
    <div class="section-toolbar">
      <div class="filters">
        <div class="search-field">
          <svg><use href="#i-search" /></svg>
          <input
            v-model="filters.search"
            type="search"
            placeholder="Nomi, INN yoki kod..."
            @input="onSearchInput"
          />
        </div>

        <select v-model="filters.is_active" @change="load()">
          <option value="">Barcha holatlar</option>
          <option value="true">Faol</option>
          <option value="false">Faol emas</option>
        </select>
      </div>

      <button class="button button-gradient" type="button" @click="openCreate">
        <svg><use href="#i-plus" /></svg>
        <span>Kompaniya qo‘shish</span>
      </button>
    </div>

    <p v-if="error" class="load-error">{{ error }}</p>

    <div class="kpi-grid">
      <article class="kpi-card">
        <div class="kpi-icon"><svg><use href="#i-company" /></svg></div>
        <p>Kompaniyalar</p>
        <strong>{{ summary?.total ?? 0 }}</strong>
      </article>

      <article class="kpi-card">
        <div class="kpi-icon"><svg><use href="#i-report" /></svg></div>
        <p>Faol</p>
        <strong>{{ summary?.active ?? 0 }}</strong>
      </article>

      <article class="kpi-card">
        <div class="kpi-icon"><svg><use href="#i-warehouse" /></svg></div>
        <p>Omborlar</p>
        <strong>{{ summary?.warehouses ?? 0 }}</strong>
      </article>

      <article class="kpi-card">
        <div class="kpi-icon"><svg><use href="#i-users" /></svg></div>
        <p>Foydalanuvchilar</p>
        <strong>{{ summary?.users ?? 0 }}</strong>
      </article>
    </div>

    <div class="table-card">
      <div class="table-scroll">
        <table class="data-table">
          <thead>
            <tr>
              <th>Kompaniya</th>
              <th>Kod</th>
              <th>Shakl</th>
              <th>INN</th>
              <th>Rahbar</th>
              <th>Egasi</th>
              <th class="num">Omborlar</th>
              <th class="num">Xodimlar</th>
              <th>Holat</th>
              <th></th>
            </tr>
          </thead>

          <tbody>
            <tr v-if="loading">
              <td colspan="10" class="empty-state">Yuklanmoqda…</td>
            </tr>

            <tr v-else-if="!items.length">
              <td colspan="10" class="empty-state">Kompaniya topilmadi.</td>
            </tr>

            <tr v-for="company in items" v-else :key="company.id">
              <td>
                <div class="company-cell">
                  <img v-if="company.logo" :src="company.logo" alt="" class="company-logo" />
                  <div>
                    <strong>{{ company.name }}</strong>
                    <small class="cell-sub">{{ company.phone || company.slug }}</small>
                  </div>
                </div>
              </td>
              <td>{{ company.code || '—' }}</td>
              <td>{{ company.legal_form_display }}</td>
              <td>{{ company.inn || '—' }}</td>
              <td>{{ company.director || '—' }}</td>
              <td>{{ company.owner?.full_name ?? '—' }}</td>
              <td class="num">{{ company.warehouse_count }}</td>
              <td class="num">{{ company.member_count }}</td>

              <td>
                <span class="pill" :class="company.is_active ? 'pill-green' : 'pill-red'">
                  {{ company.is_active ? 'Faol' : 'Faol emas' }}
                </span>
              </td>

              <td class="row-actions">
                <button class="button button-soft" type="button" @click="openEdit(company)">
                  Tahrirlash
                </button>
                <button class="button button-outline" type="button" @click="onToggleActive(company)">
                  {{ company.is_active ? 'To‘xtatish' : 'Faollashtirish' }}
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Kompaniya formasi -->
    <div class="modal" :class="{ show: modalOpen }">
      <div class="modal-backdrop" @click="modalOpen = false"></div>

      <div class="modal-dialog modal-large">
        <div class="modal-header">
          <div>
            <span class="modal-eyebrow">KOMPANIYA</span>
            <h3>{{ editing ? editing.name : 'Yangi kompaniya' }}</h3>
            <p>
              Har bir kompaniyaning ma’lumotlari boshqalaridan to‘liq ajratilgan.
              Rekvizitlar hujjat va chek sarlavhasida chiqadi.
            </p>
          </div>

          <button class="modal-close" type="button" @click="modalOpen = false">
            <svg><use href="#i-close" /></svg>
          </button>
        </div>

        <form @submit.prevent="onSubmit">
          <div class="modal-body">
            <h4 class="form-section">Asosiy ma’lumot</h4>

            <div class="form-grid three">
              <div class="field span-2">
                <label>To‘liq nomi</label>
                <input v-model="form.name" required />
                <small v-if="fieldError('name')" class="field-error">{{ fieldError('name') }}</small>
              </div>

              <div class="field">
                <label>Qisqa nom</label>
                <input v-model="form.short_name" />
              </div>

              <div class="field">
                <label>Ichki kod</label>
                <input v-model="form.code" maxlength="8" placeholder="QS" />
                <small v-if="fieldError('code')" class="field-error">{{ fieldError('code') }}</small>
              </div>

              <div class="field">
                <label>Huquqiy shakli</label>
                <select v-model="form.legal_form">
                  <option v-for="item in LEGAL_FORMS" :key="item.value" :value="item.value">
                    {{ item.label }}
                  </option>
                </select>
              </div>

              <div class="field">
                <label>Faoliyat turi</label>
                <select v-model="form.business_type">
                  <option value="construction">Qurilish mollari</option>
                  <option value="clothing">Kiyim-kechak</option>
                  <option value="grocery">Oziq-ovqat</option>
                  <option value="general">Aralash / boshqa</option>
                </select>
              </div>
            </div>

            <h4 class="form-section">Ro‘yxatdan o‘tish ma’lumotlari</h4>

            <div class="form-grid three">
              <div class="field">
                <label>INN (STIR)</label>
                <input v-model="form.inn" inputmode="numeric" />
                <small v-if="fieldError('inn')" class="field-error">{{ fieldError('inn') }}</small>
              </div>

              <div class="field">
                <label>Ro‘yxatdan o‘tish raqami</label>
                <input v-model="form.registration_number" />
              </div>

              <div class="field">
                <label>QQS to‘lovchi kodi</label>
                <input v-model="form.vat_code" />
              </div>

              <div class="field">
                <label>Rahbar</label>
                <input v-model="form.director" />
              </div>

              <div class="field">
                <label>Asosiy valyuta</label>
                <input v-model="form.base_currency" maxlength="3" />
                <small v-if="fieldError('base_currency')" class="field-error">
                  {{ fieldError('base_currency') }}
                </small>
              </div>
            </div>

            <h4 class="form-section">Aloqa va manzil</h4>

            <div class="form-grid three">
              <div class="field">
                <label>Telefon</label>
                <input v-model="form.phone" />
              </div>

              <div class="field">
                <label>Email</label>
                <input v-model="form.email" type="email" />
                <small v-if="fieldError('email')" class="field-error">{{ fieldError('email') }}</small>
              </div>

              <div class="field">
                <label>Veb-sayt</label>
                <input v-model="form.website" placeholder="https://" />
                <small v-if="fieldError('website')" class="field-error">{{ fieldError('website') }}</small>
              </div>

              <div class="field full">
                <label>Yuridik manzil</label>
                <input v-model="form.address" />
              </div>

              <div class="field full">
                <label>Haqiqiy manzil</label>
                <input v-model="form.actual_address" />
              </div>
            </div>

            <h4 class="form-section">Bank rekvizitlari</h4>

            <div class="form-grid three">
              <div class="field">
                <label>Bank</label>
                <input v-model="form.bank_name" />
              </div>

              <div class="field">
                <label>MFO</label>
                <input v-model="form.mfo" maxlength="5" inputmode="numeric" />
                <small v-if="fieldError('mfo')" class="field-error">{{ fieldError('mfo') }}</small>
              </div>

              <div class="field">
                <label>Hisob raqami</label>
                <input v-model="form.bank_account" maxlength="20" inputmode="numeric" />
                <small v-if="fieldError('bank_account')" class="field-error">
                  {{ fieldError('bank_account') }}
                </small>
              </div>
            </div>

            <h4 class="form-section">Logotip va izoh</h4>

            <div class="logo-row">
              <img v-if="logoPreview" :src="logoPreview" alt="Logotip" class="logo-preview" />
              <span v-else class="muted">Logotip yo‘q</span>

              <label class="button button-outline">
                <input type="file" accept="image/png,image/jpeg,image/webp" hidden @change="onLogoChange" />
                Logotip tanlash
              </label>

              <small class="field-hint">PNG, JPEG yoki WEBP, 2 MB gacha</small>
            </div>
            <small v-if="fieldError('logo')" class="field-error">{{ fieldError('logo') }}</small>

            <div class="field full">
              <label>Izoh</label>
              <textarea v-model="form.notes" rows="2"></textarea>
            </div>

            <template v-if="!editing">
              <h4 class="form-section">Kompaniya egasi</h4>

              <p class="hint">
                Login mavjud bo‘lsa, o‘sha foydalanuvchi ega bo‘ladi — parol kerak emas.
                Aks holda yangi foydalanuvchi yaratiladi.
              </p>

              <div class="form-grid">
                <div class="field">
                  <label>Login</label>
                  <input v-model="form.owner_username" required autocomplete="off" />
                  <small v-if="fieldError('owner_username')" class="field-error">
                    {{ fieldError('owner_username') }}
                  </small>
                </div>

                <div class="field">
                  <label>Parol</label>
                  <input v-model="form.owner_password" type="password" autocomplete="new-password" />
                  <small v-if="fieldError('owner_password')" class="field-error">
                    {{ fieldError('owner_password') }}
                  </small>
                </div>

                <div class="field">
                  <label>Ism</label>
                  <input v-model="form.owner_first_name" />
                </div>

                <div class="field">
                  <label>Familiya</label>
                  <input v-model="form.owner_last_name" />
                </div>
              </div>
            </template>

            <p v-if="fieldError('detail')" class="form-error">{{ fieldError('detail') }}</p>
          </div>

          <div class="modal-footer">
            <button class="button button-outline" type="button" @click="modalOpen = false">
              Bekor qilish
            </button>

            <button class="button button-gradient" type="submit" :disabled="saving">
              {{ saving ? 'Saqlanmoqda…' : 'Saqlash' }}
            </button>
          </div>
        </form>
      </div>
    </div>
  </section>
</template>

<style scoped>

.form-section {
  margin: 16px 0 8px;
  color: var(--text-secondary);
  font-size: 13px;
  font-weight: 600;
}

.form-section:first-child {
  margin-top: 0;
}

.company-cell {
  display: flex;
  align-items: center;
  gap: 8px;
}

.company-logo {
  width: 28px;
  height: 28px;
  object-fit: contain;
  border-radius: var(--radius-small);
}

.logo-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
}

.logo-preview {
  max-width: 160px;
  max-height: 56px;
  object-fit: contain;
}

</style>
