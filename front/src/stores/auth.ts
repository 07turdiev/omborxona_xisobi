import { computed, ref } from 'vue'
import { defineStore } from 'pinia'

import api, { tokenStorage } from '@/api/client'
import { accountsApi } from '@/api/accounts'
import type { ShopSettings, User } from '@/types'
import { settingsApi } from '@/api/accounts'

export const useAuthStore = defineStore('auth', () => {
  const user = ref<User | null>(null)
  const shop = ref<ShopSettings | null>(null)
  const loading = ref(false)

  const isAuthenticated = computed(() => Boolean(tokenStorage.access))
  const isAdmin = computed(() => user.value?.role === 'admin')

  async function login(username: string, password: string) {
    loading.value = true

    try {
      const { data } = await api.post<{ access: string; refresh: string }>('/auth/login/', {
        username,
        password,
      })

      tokenStorage.set(data.access, data.refresh)
      await loadProfile()
    } finally {
      loading.value = false
    }
  }

  /** Xodim va do'kon sozlamalari — kassa ekrani ikkalasiga tayanadi. */
  async function loadProfile() {
    user.value = await accountsApi.me()
    shop.value = await settingsApi.get()
  }

  function logout() {
    tokenStorage.clear()
    user.value = null
    shop.value = null
  }

  return { user, shop, loading, isAuthenticated, isAdmin, login, loadProfile, logout }
})
