<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'

import { tenantsApi, type MemberInput } from '@/api/tenants'
import { useAuthStore } from '@/stores/auth'
import { useWarehouseStore } from '@/stores/warehouses'
import type {
  MembershipRow,
  PermissionCatalog,
  RoleChoice,
  WarehouseAccessRow,
} from '@/types'

const auth = useAuthStore()
const warehouses = useWarehouseStore()

const items = ref<MembershipRow[]>([])
const roles = ref<RoleChoice[]>([])
const catalog = ref<PermissionCatalog | null>(null)

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

// Ruxsatlar
const permOpen = ref(false)
const permTarget = ref<MembershipRow | null>(null)
const permSelected = ref<Set<string>>(new Set())
const permError = ref('')

/** Xodimlarni boshqarish — `users` ruxsati (egasi va menejerda standart). */
const canManage = computed(() => auth.can('users'))

const isOwnerActor = computed(() => auth.user?.current_tenant?.role === 'owner')

/**
 * Qatorni tahrirlash mumkinmi. Server ham xuddi shu qoidalarni tekshiradi —
 * bu yerda faqat bosib bo'lmaydigan tugmani ko'rsatmaslik uchun.
 */
function canEdit(member: MembershipRow): boolean {
  if (!canManage.value) return false

  // O'z huquqini hech kim o'zgartirmaydi
  if (member.user === auth.user?.id) return false

  // Egasini faqat ega o'zgartiradi
  return member.role !== 'owner' || isOwnerActor.value
}

function roleLabel(value: string): string {
  return roles.value.find((role) => role.value === value)?.label ?? value
}

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
  const [roleList, permissionCatalog] = await Promise.all([
    tenantsApi.roles(),
    tenantsApi.permissionCatalog(),
  ])

  roles.value = roleList
  catalog.value = permissionCatalog

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

function firstError(err: unknown, fallback: string): string {
  const value = Object.values(asErrors(err)).flat()[0]
  return typeof value === 'string' ? value : fallback
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
    error.value = firstError(err, 'O‘zgartirib bo‘lmadi.')
    await load()
  }
}

async function onToggleActive(member: MembershipRow) {
  try {
    await tenantsApi.updateMember(member.id, { is_active: !member.is_active })
    await load()
  } catch (err) {
    error.value = firstError(err, 'O‘zgartirib bo‘lmadi.')
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
    error.value = firstError(err, 'Chiqarib bo‘lmadi.')
  }
}

// -- ruxsatlar -------------------------------------------------------

const permGroups = computed(() => {
  if (!catalog.value) return []

  return Object.entries(catalog.value.groups).map(([key, label]) => ({
    key,
    label,
    items: catalog.value!.items.filter((item) => item.group === key),
  }))
})

const targetDefaults = computed(() => {
  const role = roles.value.find((r) => r.value === permTarget.value?.role)
  return new Set(role?.default_permissions ?? [])
})

function openPermissions(member: MembershipRow) {
  permTarget.value = member
  permSelected.value = new Set(member.permissions)
  permError.value = ''
  permOpen.value = true
}

function togglePermission(value: string) {
  const next = new Set(permSelected.value)

  if (next.has(value)) next.delete(value)
  else next.add(value)

  permSelected.value = next
}

/** Egasi bo'lmagan admin o'zida yo'q ruxsatni bera olmaydi (server ham shunday). */
function canGrant(value: string): boolean {
  return isOwnerActor.value || auth.can(value)
}

async function savePermissions(permissions: string[] | null) {
  if (!permTarget.value) return

  permError.value = ''
  saving.value = true

  try {
    await tenantsApi.updateMember(permTarget.value.id, { permissions })
    permOpen.value = false
    await load()
  } catch (err) {
    permError.value = firstError(err, 'Ruxsatlarni saqlab bo‘lmadi.')
  } finally {
    saving.value = false
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
    error.value = firstError(err, 'Huquq berib bo‘lmadi.')
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
      Xodimlarni boshqarish uchun <strong>«Xodimlar»</strong> ruxsati kerak.
      Siz ro‘yxatni ko‘ra olasiz.
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
              <th>Ruxsatlar</th>
              <th>Omborlar</th>
              <th>Holat</th>
              <th></th>
            </tr>
          </thead>

          <tbody>
            <tr v-if="loading">
              <td colspan="8" class="empty-state">Yuklanmoqda…</td>
            </tr>

            <tr v-else-if="!items.length">
              <td colspan="8" class="empty-state">Xodim topilmadi.</td>
            </tr>

            <tr v-for="member in items" v-else :key="member.id">
              <td>
                <strong>{{ member.full_name }}</strong>
                <small v-if="member.user === auth.user?.id" class="cell-sub">siz</small>
              </td>
              <td>{{ member.username }}</td>

              <td>
                <span v-if="member.phone || member.email">
                  {{ member.phone || member.email }}
                </span>
                <span v-else class="muted">—</span>
              </td>

              <td>
                <select
                  v-if="canEdit(member)"
                  class="role-select"
                  :value="member.role"
                  @change="onRoleChange(member, ($event.target as HTMLSelectElement).value)"
                >
                  <option
                    v-for="role in roles"
                    :key="role.value"
                    :value="role.value"
                    :disabled="role.value === 'owner' && !isOwnerActor"
                  >
                    {{ role.label }}
                  </option>
                </select>
                <span v-else>{{ member.role_display }}</span>
              </td>

              <td>
                <button
                  v-if="canEdit(member) && member.role !== 'owner'"
                  class="access-link"
                  type="button"
                  @click="openPermissions(member)"
                >
                  <span v-if="member.uses_role_defaults" class="all-access">rol bo‘yicha</span>
                  <span v-else class="limited">alohida · {{ member.permissions.length }}</span>
                </button>
                <span v-else-if="member.role === 'owner'" class="muted">hammasi</span>
                <span v-else class="muted">
                  {{ member.uses_role_defaults ? 'rol bo‘yicha' : `alohida · ${member.permissions.length}` }}
                </span>
              </td>

              <td>
                <button
                  v-if="canEdit(member)"
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
                <template v-if="canEdit(member)">
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
              Ruxsatlar roldan olinadi; keyin ularni alohida sozlash mumkin.
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
                  <option
                    v-for="role in roles"
                    :key="role.value"
                    :value="role.value"
                    :disabled="role.value === 'owner' && !isOwnerActor"
                  >
                    {{ role.label }}
                  </option>
                </select>
                <small v-if="fieldError('role')" class="field-error">
                  {{ fieldError('role') }}
                </small>
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

            <p v-if="fieldError('detail') || fieldError('permissions')" class="form-error">
              {{ fieldError('detail') || fieldError('permissions') }}
            </p>
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

    <!-- Ruxsatlar -->
    <div class="modal" :class="{ show: permOpen }">
      <div class="modal-backdrop" @click="permOpen = false"></div>

      <div class="modal-dialog modal-large">
        <div class="modal-header">
          <div>
            <span class="modal-eyebrow">RUXSATLAR</span>
            <h3>{{ permTarget?.full_name }}</h3>
            <p>
              Rol: <strong>{{ roleLabel(permTarget?.role ?? '') }}</strong>.
              <span class="default-mark">•</span> belgisi — shu rolning standart ruxsati.
              Kirim narxi va foyda alohida ruxsat: ularsiz xodim sotuv qila oladi,
              lekin tovar qanchaga olinganini ko‘rmaydi.
            </p>
          </div>

          <button class="modal-close" type="button" @click="permOpen = false">
            <svg><use href="#i-close" /></svg>
          </button>
        </div>

        <div class="modal-body">
          <div class="perm-groups">
            <fieldset v-for="group in permGroups" :key="group.key" class="perm-group">
              <legend>{{ group.label }}</legend>

              <label
                v-for="item in group.items"
                :key="item.value"
                class="perm-item"
                :class="{ locked: !canGrant(item.value) }"
                :title="canGrant(item.value) ? '' : 'Sizda bu ruxsat yo‘q — uni bera olmaysiz'"
              >
                <input
                  type="checkbox"
                  :checked="permSelected.has(item.value)"
                  :disabled="!canGrant(item.value) && !permSelected.has(item.value)"
                  @change="togglePermission(item.value)"
                />
                <span>{{ item.label }}</span>
                <span v-if="targetDefaults.has(item.value)" class="default-mark">•</span>
              </label>
            </fieldset>
          </div>

          <p v-if="permError" class="form-error">{{ permError }}</p>
        </div>

        <div class="modal-footer">
          <button
            class="button button-outline"
            type="button"
            :disabled="saving || permTarget?.uses_role_defaults"
            @click="savePermissions(null)"
          >
            Rol standartiga qaytarish
          </button>

          <button
            class="button button-gradient"
            type="button"
            :disabled="saving"
            @click="savePermissions([...permSelected])"
          >
            {{ saving ? 'Saqlanmoqda…' : 'Saqlash' }}
          </button>
        </div>
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

.grant-row {
  display: flex;
  gap: 8px;
  align-items: center;
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid var(--border);
}

.perm-groups {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 12px;
}

.perm-group {
  margin: 0;
  padding: 12px;

  border: 1px solid var(--border);
  border-radius: var(--radius);
}

.perm-group legend {
  padding: 0 4px;

  color: var(--text-muted);
  font-size: 12px;
  font-weight: 600;
}

.perm-item {
  padding: 4px 0;

  display: flex;
  align-items: center;
  gap: 8px;

  font-size: 13px;
  cursor: pointer;
}

.perm-item.locked {
  color: var(--text-muted);
  cursor: not-allowed;
}

.default-mark {
  color: var(--green);
  font-weight: 700;
}

</style>
