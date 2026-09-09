<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'

import { tenantsApi, type MemberInput } from '@/api/tenants'
import { useAuthStore } from '@/stores/auth'
import { useWarehouseStore } from '@/stores/warehouses'
import type { MembershipRow, RoleChoice, WarehouseAccessRow } from '@/types'

const auth = useAuthStore()
const warehouses = useWarehouseStore()

const items = ref<MembershipRow[]>([])
const roles = ref<RoleChoice[]>([])

const loading = ref(false)
const saving = ref(false)
const error = ref('')

const filters = reactive({ search: '', role: '' })

// Xodim qo'shish
const addOpen = ref(false)
const errors = ref<Record<string, string[]>>({})

function emptyForm(): MemberInput {
  return {
    username: '',
    password: '',
    first_name: '',
    last_name: '',
    email: '',
    phone: '',
    role: 'viewer',
  }
}

const form = reactive<MemberInput>(emptyForm())

// Ombor huquqlari
const accessOpen = ref(false)
const accessTarget = ref<MembershipRow | null>(null)
const accessRows = ref<WarehouseAccessRow[]>([])
const newAccess = reactive({ warehouse: null as number | null, level: 'view' })

const accessLevels = [
  { value: 'view', label: 'Ko‘rish' },
  { value: 'operate', label: 'Kirim-chiqim qilish' },
  { value: 'manage', label: 'To‘liq boshqarish' },
]

const canManage = computed(() => {
  const role = auth.user?.current_tenant?.role
  return role === 'owner' || role === 'manager'
})

async function load() {
  loading.value = true
  error.value = ''

  try {
    items.value = (await tenantsApi.members(filters)).results
  } catch {
    error.value = 'Xodimlarni olishda xatolik.'
  } finally {
    loading.value = false
  }
}

onMounted(async () => {
  roles.value = await tenantsApi.roles()
  await Promise.all([load(), warehouses.load()])
})

let searchTimer: ReturnType<typeof setTimeout> | undefined

function onSearchInput() {
  clearTimeout(searchTimer)
  searchTimer = setTimeout(load, 300)
}

function asErrors(err: unknown): Record<string, string[]> {
  const data = (err as { response?: { data?: unknown } }).response?.data

  if (data && typeof data === 'object') return data as Record<string, string[]>

  return { detail: ['Kutilmagan xatolik.'] }
}

// -- xodim qo'shish --------------------------------------------------

function openAdd() {
  errors.value = {}
  Object.assign(form, emptyForm())
  addOpen.value = true
}

async function onAdd() {
  errors.value = {}
  saving.value = true

  try {
    await tenantsApi.addMember(form)
    addOpen.value = false
    await load()
  } catch (err) {
    errors.value = asErrors(err)
  } finally {
    saving.value = false
  }
}

// -- rol va faollik --------------------------------------------------

async function onRoleChange(member: MembershipRow, role: string) {
  try {
    await tenantsApi.updateMember(member.id, { role })
    await load()
  } catch (err) {
    error.value = Object.values(asErrors(err)).flat()[0] ?? 'O‘zgartirib bo‘lmadi.'
  }
}

async function onToggleActive(member: MembershipRow) {
  try {
    await tenantsApi.updateMember(member.id, { is_active: !member.is_active })
    await load()
  } catch (err) {
    error.value = Object.values(asErrors(err)).flat()[0] ?? 'O‘zgartirib bo‘lmadi.'
  }
}

async function onRemove(member: MembershipRow) {
  const ok = window.confirm(
    `${member.full_name} tashkilotdan chiqarilsinmi?\n\n` +
      'Foydalanuvchi hisobi o‘chirilmaydi — u boshqa tashkilotlarda ' +
      'ishlayotgan bo‘lishi mumkin.',
  )

  if (!ok) return

  try {
    await tenantsApi.removeMember(member.id)
    await load()
  } catch (err) {
    error.value = Object.values(asErrors(err)).flat()[0] ?? 'Chiqarib bo‘lmadi.'
  }
}

// -- ombor huquqlari -------------------------------------------------

async function openAccess(member: MembershipRow) {
  accessTarget.value = member
  newAccess.warehouse = null
  newAccess.level = 'view'
  error.value = ''

  accessRows.value = (await tenantsApi.warehouseAccess(member.user)).results
  accessOpen.value = true
}

async function onGrant() {
  if (!accessTarget.value || !newAccess.warehouse) return

  try {
    await tenantsApi.grantAccess({
      warehouse: newAccess.warehouse,
      user: accessTarget.value.user,
      level: newAccess.level,
    })

    accessRows.value = (
      await tenantsApi.warehouseAccess(accessTarget.value.user)
    ).results
    newAccess.warehouse = null
    await load()
  } catch (err) {
    error.value = Object.values(asErrors(err)).flat()[0] ?? 'Huquq berib bo‘lmadi.'
  }
}

async function onRevoke(row: WarehouseAccessRow) {
  await tenantsApi.revokeAccess(row.id)

  if (accessTarget.value) {
    accessRows.value = (
      await tenantsApi.warehouseAccess(accessTarget.value.user)
    ).results
  }

  await load()
}

const fieldError = (field: string): string => {
  const value = errors.value[field]
  return Array.isArray(value) ? (value[0] ?? '') : ''
}
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
            placeholder="Login yoki ism..."
            @input="onSearchInput"
          />
        </div>

        <select v-model="filters.role" @change="load()">
          <option value="">Barcha rollar</option>
          <option v-for="role in roles" :key="role.value" :value="role.value">
            {{ role.label }}
          </option>
        </select>
      </div>

      <button v-if="canManage" class="button button-gradient" @click="openAdd">
        <svg><use href="#i-plus" /></svg>
        <span>Xodim qo‘shish</span>
      </button>
    </div>

    <p v-if="error" class="load-error">{{ error }}</p>

    <div v-if="!canManage" class="notice">
      Xodimlarni boshqarish uchun <strong>egasi</strong> yoki
      <strong>menejer</strong> roli kerak. Siz ro‘yxatni ko‘ra olasiz.
    </div>

    <div class="table-card">
      <div class="table-scroll">
        <table class="data-table">
          <thead>
            <tr>
              <th>Xodim</th>
              <th>Login</th>
              <th>Aloqa</th>
              <th>Rol</th>
              <th>Omborlar</th>
              <th>Holat</th>
              <th></th>
            </tr>
          </thead>

          <tbody>
            <tr v-if="loading">
              <td colspan="7" class="empty-state">Yuklanmoqda…</td>
            </tr>

            <tr v-else-if="!items.length">
              <td colspan="7" class="empty-state">Xodim topilmadi.</td>
            </tr>

            <tr v-for="member in items" v-else :key="member.id">
              <td><strong>{{ member.full_name }}</strong></td>
              <td>{{ member.username }}</td>

              <td>
                <span v-if="member.phone || member.email">
                  {{ member.phone || member.email }}
                </span>
                <span v-else class="muted">—</span>
              </td>

              <td>
                <select
                  v-if="canManage"
                  class="role-select"
                  :value="member.role"
                  @change="onRoleChange(member, ($event.target as HTMLSelectElement).value)"
                >
                  <option v-for="role in roles" :key="role.value" :value="role.value">
                    {{ role.label }}
                  </option>
                </select>
                <span v-else>{{ member.role_display }}</span>
              </td>

              <td>
                <button
                  v-if="canManage"
                  class="access-link"
                  type="button"
                  @click="openAccess(member)"
                >
                  <span v-if="member.warehouse_count === 0" class="all-access">
                    hammasi
                  </span>
                  <span v-else class="limited">
                    {{ member.warehouse_count }} ta
                  </span>
                </button>
                <span v-else class="muted">
                  {{ member.warehouse_count === 0 ? 'hammasi' : member.warehouse_count }}
                </span>
              </td>

              <td>
                <span class="pill" :class="member.is_active ? 'pill-green' : 'pill-red'">
                  {{ member.is_active ? 'Faol' : 'Faol emas' }}
                </span>
              </td>

              <td class="row-actions">
                <template v-if="canManage">
                  <button class="button button-soft" type="button" @click="onToggleActive(member)">
                    {{ member.is_active ? 'To‘xtatish' : 'Faollashtirish' }}
                  </button>

                  <button class="button button-danger" type="button" @click="onRemove(member)">
                    <svg><use href="#i-trash" /></svg>
                  </button>
                </template>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Xodim qo'shish -->
    <div class="modal" :class="{ show: addOpen }">
      <div class="modal-backdrop" @click="addOpen = false"></div>

      <div class="modal-dialog modal-large">
        <div class="modal-header">
          <div>
            <span class="modal-eyebrow">XODIM</span>
            <h3>Xodim qo‘shish</h3>
            <p>
              Login mavjud bo‘lsa, o‘sha foydalanuvchiga shu tashkilotda
              a’zolik beriladi — bir odam bir nechta do‘konda ishlashi mumkin.
            </p>
          </div>

          <button class="modal-close" type="button" @click="addOpen = false">
            <svg><use href="#i-close" /></svg>
          </button>
        </div>

        <form @submit.prevent="onAdd">
          <div class="modal-body">
            <div class="form-grid three">
              <div class="field">
                <label>Login</label>
                <input v-model="form.username" required autocomplete="off" />
                <small v-if="fieldError('username')" class="field-error">
                  {{ fieldError('username') }}
                </small>
              </div>

              <div class="field">
                <label>Parol</label>
                <input v-model="form.password" type="password" autocomplete="new-password" />
                <small class="field-hint">Faqat yangi foydalanuvchi uchun</small>
                <small v-if="fieldError('password')" class="field-error">
                  {{ fieldError('password') }}
                </small>
              </div>

              <div class="field">
                <label>Rol</label>
                <select v-model="form.role">
                  <option v-for="role in roles" :key="role.value" :value="role.value">
                    {{ role.label }}
                  </option>
                </select>
              </div>

              <div class="field">
                <label>Ism</label>
                <input v-model="form.first_name" />
              </div>

              <div class="field">
                <label>Familiya</label>
                <input v-model="form.last_name" />
              </div>

              <div class="field">
                <label>Telefon</label>
                <input v-model="form.phone" />
              </div>

              <div class="field span-2">
                <label>Email</label>
                <input v-model="form.email" type="email" />
              </div>
            </div>

            <p v-if="fieldError('detail')" class="form-error">{{ fieldError('detail') }}</p>
          </div>

          <div class="modal-footer">
            <button class="button button-outline" type="button" @click="addOpen = false">
              Bekor qilish
            </button>

            <button class="button button-gradient" type="submit" :disabled="saving">
              {{ saving ? 'Saqlanmoqda…' : 'Qo‘shish' }}
            </button>
          </div>
        </form>
      </div>
    </div>

    <!-- Ombor huquqlari -->
    <div class="modal" :class="{ show: accessOpen }">
      <div class="modal-backdrop" @click="accessOpen = false"></div>

      <div class="modal-dialog">
        <div class="modal-header">
          <div>
            <span class="modal-eyebrow">OMBOR HUQUQLARI</span>
            <h3>{{ accessTarget?.full_name }}</h3>
            <p>
              Cheklov qo‘shilmagan bo‘lsa, xodim <strong>barcha</strong> omborlarni
              va barcha hisobotlarni ko‘radi. Birinchi qator qo‘shilishi bilan
              cheklov kuchga kiradi.
            </p>
          </div>

          <button class="modal-close" type="button" @click="accessOpen = false">
            <svg><use href="#i-close" /></svg>
          </button>
        </div>

        <div class="modal-body">
          <table class="data-table">
            <thead>
              <tr>
                <th>Ombor</th>
                <th>Daraja</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              <tr v-if="!accessRows.length">
                <td colspan="3" class="empty-state">
                  Cheklov yo‘q — barcha omborlar ochiq.
                </td>
              </tr>

              <tr v-for="row in accessRows" :key="row.id">
                <td>{{ row.warehouse_name }}</td>
                <td>{{ row.level_display }}</td>
                <td class="row-actions">
                  <button class="button button-danger" type="button" @click="onRevoke(row)">
                    <svg><use href="#i-trash" /></svg>
                  </button>
                </td>
              </tr>
            </tbody>
          </table>

          <div class="grant-row">
            <select v-model="newAccess.warehouse">
              <option :value="null" disabled>Ombor tanlang…</option>
              <option
                v-for="w in warehouses.items"
                :key="w.id"
                :value="w.id"
                :disabled="accessRows.some((r) => r.warehouse === w.id)"
              >
                {{ w.name }}
              </option>
            </select>

            <select v-model="newAccess.level">
              <option v-for="level in accessLevels" :key="level.value" :value="level.value">
                {{ level.label }}
              </option>
            </select>

            <button
              class="button button-gradient"
              type="button"
              :disabled="!newAccess.warehouse"
              @click="onGrant"
            >
              Qo‘shish
            </button>
          </div>
        </div>

        <div class="modal-footer">
          <button class="button button-outline" type="button" @click="accessOpen = false">
            Yopish
          </button>
        </div>
      </div>
    </div>
  </section>
</template>

<style scoped>
.muted {
  color: var(--text-muted);
}

.role-select {
  min-width: 130px;
}

.access-link {
  border: none;
  background: none;
  cursor: pointer;
  font-size: 13px;
  text-decoration: underline;
}

.all-access {
  color: var(--green);
  font-weight: 700;
}

.limited {
  color: var(--orange);
  font-weight: 700;
}

.pill {
  display: inline-block;
  padding: 4px 9px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 700;
}

.pill-green {
  background: var(--green-soft);
  color: var(--green);
}

.pill-red {
  background: var(--red-soft);
  color: var(--red);
}

.row-actions {
  display: flex;
  gap: 6px;
  justify-content: flex-end;
}

.grant-row {
  display: flex;
  gap: 8px;
  align-items: center;
  margin-top: 14px;
  padding-top: 14px;
  border-top: 1px solid var(--border);
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

.form-error,
.load-error {
  margin: 12px 0;
  padding: 10px 12px;
  border-radius: var(--radius-small);
  background: var(--red-soft);
  color: var(--red);
  font-size: 13px;
}

.load-error {
  margin: 0 0 14px;
}
</style>
