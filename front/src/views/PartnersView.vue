<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'

import { partnersApi } from '@/api/documents'
import type { Partner } from '@/types'

const items = ref<Partner[]>([])
const loading = ref(false)
const saving = ref(false)
const error = ref('')

const filters = reactive({ search: '', role: '' })

const modalOpen = ref(false)
const editing = ref<Partner | null>(null)
const errors = ref<Record<string, string[]>>({})

function emptyForm(): Partial<Partner> {
  return {
    name: '',
    is_supplier: true,
    is_customer: false,
    inn: '',
    phone: '',
    email: '',
    contact: '',
    address: '',
    bank: '',
    note: '',
    is_active: true,
  }
}

const form = reactive<Partial<Partner>>(emptyForm())

async function load() {
  loading.value = true
  error.value = ''

  try {
    items.value = (await partnersApi.list(filters)).results
  } catch {
    error.value = 'Kontragentlarni olishda xatolik.'
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
  Object.assign(form, emptyForm())
  modalOpen.value = true
}

function openEdit(partner: Partner) {
  editing.value = partner
  errors.value = {}
  Object.assign(form, { ...partner })
  modalOpen.value = true
}

async function onSubmit() {
  errors.value = {}
  saving.value = true

  try {
    if (editing.value) {
      await partnersApi.update(editing.value.id, form)
    } else {
      await partnersApi.create(form)
    }

    modalOpen.value = false
    await load()
  } catch (err) {
    const data = (err as { response?: { data?: Record<string, string[]> } }).response?.data
    errors.value = data ?? { detail: ['Saqlab bo‘lmadi.'] }
  } finally {
    saving.value = false
  }
}

async function onDelete(partner: Partner) {
  if (!window.confirm(`"${partner.name}" o‘chirilsinmi?`)) return

  try {
    await partnersApi.remove(partner.id)
    await load()
  } catch {
    error.value =
      'O‘chirib bo‘lmadi — bu kontragentga bog‘langan hujjatlar bor. ' +
      'Uni «Faol emas» qilib qo‘ying.'
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
            placeholder="Nomi, INN yoki telefon..."
            @input="onSearchInput"
          />
        </div>

        <select v-model="filters.role" @change="load()">
          <option value="">Hammasi</option>
          <option value="supplier">Yetkazib beruvchilar</option>
          <option value="customer">Mijozlar</option>
        </select>
      </div>

      <button class="button button-gradient" @click="openCreate">
        <svg><use href="#i-plus" /></svg>
        <span>Kontragent qo‘shish</span>
      </button>
    </div>

    <p v-if="error" class="load-error">{{ error }}</p>

    <div class="table-card">
      <div class="table-scroll">
        <table class="data-table">
          <thead>
            <tr>
              <th>Nomi</th>
              <th>Roli</th>
              <th>INN</th>
              <th>Telefon</th>
              <th>Aloqa shaxsi</th>
              <th>Manzil</th>
              <th>Holat</th>
              <th></th>
            </tr>
          </thead>

          <tbody>
            <tr v-if="loading">
              <td colspan="8" class="empty-state">Yuklanmoqda…</td>
            </tr>

            <tr v-else-if="!items.length">
              <td colspan="8" class="empty-state">
                Kontragent topilmadi. «Kontragent qo‘shish» bilan birinchisini yarating.
              </td>
            </tr>

            <tr v-for="partner in items" v-else :key="partner.id">
              <td><strong>{{ partner.name }}</strong></td>

              <td>
                <span v-if="partner.is_supplier" class="pill pill-blue">Yetkazuvchi</span>
                <span v-if="partner.is_customer" class="pill pill-teal">Mijoz</span>
              </td>

              <td>{{ partner.inn || '—' }}</td>
              <td>{{ partner.phone || '—' }}</td>
              <td>{{ partner.contact || '—' }}</td>
              <td class="address">{{ partner.address || '—' }}</td>

              <td>
                <span class="pill" :class="partner.is_active ? 'pill-green' : 'pill-red'">
                  {{ partner.is_active ? 'Faol' : 'Faol emas' }}
                </span>
              </td>

              <td class="row-actions">
                <button class="button button-soft" type="button" @click="openEdit(partner)">
                  Tahrirlash
                </button>

                <button class="button button-danger" type="button" @click="onDelete(partner)">
                  <svg><use href="#i-trash" /></svg>
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <div class="modal" :class="{ show: modalOpen }">
      <div class="modal-backdrop" @click="modalOpen = false"></div>

      <div class="modal-dialog modal-large">
        <div class="modal-header">
          <div>
            <span class="modal-eyebrow">KONTRAGENT</span>
            <h3>{{ editing ? 'Tahrirlash' : 'Kontragent qo‘shish' }}</h3>
            <p>Bir tashkilot bir vaqtda yetkazib beruvchi ham, mijoz ham bo‘lishi mumkin.</p>
          </div>

          <button class="modal-close" type="button" @click="modalOpen = false">
            <svg><use href="#i-close" /></svg>
          </button>
        </div>

        <form @submit.prevent="onSubmit">
          <div class="modal-body">
            <div class="form-grid three">
              <div class="field span-2">
                <label>Nomi</label>
                <input v-model="form.name" required />
                <small v-if="fieldError('name')" class="field-error">
                  {{ fieldError('name') }}
                </small>
              </div>

              <div class="field">
                <label>INN</label>
                <input v-model="form.inn" />
              </div>

              <div class="field">
                <label>Roli</label>

                <div class="role-checks">
                  <label class="check">
                    <input v-model="form.is_supplier" type="checkbox" />
                    <span>Yetkazib beruvchi</span>
                  </label>

                  <label class="check">
                    <input v-model="form.is_customer" type="checkbox" />
                    <span>Mijoz</span>
                  </label>
                </div>

                <small v-if="fieldError('is_supplier')" class="field-error">
                  {{ fieldError('is_supplier') }}
                </small>
              </div>

              <div class="field">
                <label>Telefon</label>
                <input v-model="form.phone" placeholder="+998 90 123 45 67" />
              </div>

              <div class="field">
                <label>Email</label>
                <input v-model="form.email" type="email" />
              </div>

              <div class="field">
                <label>Aloqa shaxsi</label>
                <input v-model="form.contact" />
              </div>

              <div class="field span-2">
                <label>Manzil</label>
                <input v-model="form.address" />
              </div>

              <div class="field full">
                <label>Bank rekvizitlari</label>
                <input v-model="form.bank" />
              </div>

              <div class="field full">
                <label>Izoh</label>
                <textarea v-model="form.note" rows="2"></textarea>
              </div>

              <div class="field">
                <label>Holati</label>
                <select v-model="form.is_active">
                  <option :value="true">Faol</option>
                  <option :value="false">Faol emas</option>
                </select>
              </div>
            </div>

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
.address {
  max-width: 220px;
  color: var(--text-secondary);
  font-size: 7px;
}

.pill {
  display: inline-block;
  margin-right: 4px;
  padding: 4px 9px;
  border-radius: 999px;
  font-size: 7px;
  font-weight: 700;
  white-space: nowrap;
}

.pill-blue {
  background: var(--blue-soft);
  color: var(--blue);
}

.pill-teal {
  background: var(--teal-soft);
  color: var(--teal);
}

.pill-green {
  background: var(--green-soft);
  color: var(--green);
}

.pill-red {
  background: var(--red-soft);
  color: var(--red);
}

.role-checks {
  display: flex;
  gap: 14px;
  padding-top: 6px;
}

.check {
  display: flex;
  align-items: center;
  gap: 5px;
  font-size: 8px;
  cursor: pointer;
}

.check input {
  width: auto;
  margin: 0;
}

.row-actions {
  display: flex;
  gap: 6px;
  justify-content: flex-end;
}

.field-error {
  margin-top: 4px;
  color: var(--red);
  font-size: 7px;
}

.form-error,
.load-error {
  margin: 12px 0;
  padding: 10px 12px;
  border-radius: var(--radius-small);
  background: var(--red-soft);
  color: var(--red);
  font-size: 8px;
}

.load-error {
  margin: 0 0 14px;
}
</style>
