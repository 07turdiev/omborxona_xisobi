<script setup lang="ts">
import { onMounted, ref } from 'vue'

import { accountsApi } from '@/api/accounts'
import { errorMessage } from '@/api/client'
import { formatDateTime } from '@/utils/date'
import type { Role, User } from '@/types'

const users = ref<User[]>([])
const loading = ref(false)
const error = ref('')
const notice = ref('')
const saving = ref(false)

const form = ref({
  username: '',
  password: '',
  role: 'cashier' as Role,
  first_name: '',
  last_name: '',
  phone: '',
})

async function load() {
  loading.value = true
  error.value = ''

  try {
    const page = await accountsApi.users()
    users.value = page.results
  } catch (err) {
    error.value = errorMessage(err, 'Xodimlarni yuklab bo‘lmadi.')
  } finally {
    loading.value = false
  }
}

async function onCreate() {
  if (!form.value.username.trim() || !form.value.password.trim() || saving.value) return

  saving.value = true
  error.value = ''
  notice.value = ''

  try {
    await accountsApi.createUser(form.value)

    notice.value = `${form.value.username} qo‘shildi.`
    form.value = { username: '', password: '', role: 'cashier', first_name: '', last_name: '', phone: '' }

    await load()
  } catch (err) {
    error.value = errorMessage(err, 'Xodimni qo‘shib bo‘lmadi.')
  } finally {
    saving.value = false
  }
}

async function onToggle(user: User) {
  try {
    await accountsApi.updateUser(user.id, { is_active: !user.is_active })
    await load()
  } catch (err) {
    error.value = errorMessage(err, 'O‘zgartirib bo‘lmadi.')
  }
}

async function onPassword(user: User) {
  const password = window.prompt(`${user.username} uchun yangi parol:`)

  if (!password) return

  try {
    await accountsApi.setPassword(user.id, password)
    notice.value = `${user.username} paroli yangilandi.`
  } catch (err) {
    error.value = errorMessage(err, 'Parolni yangilab bo‘lmadi.')
  }
}

onMounted(load)
</script>

<template>
  <section class="app-section active">
    <p v-if="error" class="load-error">{{ error }}</p>
    <p v-if="notice" class="notice">{{ notice }}</p>

    <div class="users">
      <div class="table-card">
        <div class="table-scroll">
          <table class="data-table">
            <thead>
              <tr>
                <th>Login</th>
                <th>Ism</th>
                <th>Roli</th>
                <th>Oxirgi kirish</th>
                <th>Holati</th>
                <th></th>
              </tr>
            </thead>

            <tbody>
              <tr v-if="loading">
                <td colspan="6" class="empty-state">Yuklanmoqda…</td>
              </tr>

              <tr v-for="user in users" v-else :key="user.id">
                <td><strong>{{ user.username }}</strong></td>
                <td>{{ user.full_name || '—' }}</td>
                <td>{{ user.role_display }}</td>
                <td>{{ formatDateTime(user.last_login) }}</td>
                <td>
                  <span class="pill" :class="user.is_active ? 'pill-green' : 'pill-red'">
                    {{ user.is_active ? 'Faol' : 'Bloklangan' }}
                  </span>
                </td>
                <td class="num row-actions">
                  <button class="button button-outline" type="button" @click="onPassword(user)">
                    Parol
                  </button>

                  <button class="button button-outline" type="button" @click="onToggle(user)">
                    {{ user.is_active ? 'Bloklash' : 'Ochish' }}
                  </button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <aside class="table-card card-padded">
        <h3>Yangi xodim</h3>

        <div class="field">
          <label>Login</label>
          <input v-model="form.username" type="text" autocomplete="off" />
        </div>

        <div class="field">
          <label>Parol</label>
          <input v-model="form.password" type="text" autocomplete="new-password" />
        </div>

        <div class="field">
          <label>Roli</label>
          <select v-model="form.role">
            <option value="cashier">Kassir</option>
            <option value="admin">Administrator</option>
          </select>
        </div>

        <div class="field">
          <label>Ismi</label>
          <input v-model="form.first_name" type="text" />
        </div>

        <div class="field">
          <label>Familiyasi</label>
          <input v-model="form.last_name" type="text" />
        </div>

        <div class="field">
          <label>Telefon</label>
          <input v-model="form.phone" type="text" placeholder="+998" />
        </div>

        <button class="button button-gradient" type="button" :disabled="saving" @click="onCreate">
          {{ saving ? 'Saqlanmoqda…' : 'Qo‘shish' }}
        </button>
      </aside>
    </div>
  </section>
</template>

<style scoped>
.users {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 300px;
  align-items: start;
  gap: 12px;
}

@media (max-width: 1000px) {
  .users {
    grid-template-columns: 1fr;
  }
}

.row-actions .button {
  margin-left: 6px;
}
</style>
