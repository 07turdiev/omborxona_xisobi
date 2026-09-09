import { computed, ref } from 'vue'
import { defineStore } from 'pinia'

import api, { tenantStorage, tokenStorage } from '@/api/client'
import type { TokenPair, User } from '@/types'

export const useAuthStore = defineStore('auth', () => {
  const user = ref<User | null>(null)
  const loading = ref(false)

  const isAuthenticated = computed(() => Boolean(tokenStorage.access))

  async function login(username: string, password: string) {
    loading.value = true
    try {
      const { data } = await api.post<TokenPair>('/auth/login/', { username, password })
      tokenStorage.set(data.access, data.refresh)
      await fetchMe()
    } finally {
      loading.value = false
    }
  }

  async function fetchMe() {
    const { data } = await api.get<User>('/auth/me/')
    user.value = data
    return data
  }

  function logout() {
    tokenStorage.clear()
    tenantStorage.clear()
    user.value = null
  }

  /**
   * Boshqa tashkilotga o'tadi.
   *
   * Sahifa butunlay qayta yuklanadi. Sabab: o'nlab store da oldingi
   * tashkilot ma'lumoti qolgan bo'ladi va ularni bittalab tozalash
   * xatoga yo'l ochadi — bittasi unutilsa, foydalanuvchi begona
   * ma'lumotni ko'rib qoladi. Server tomondan bunday sizish mumkin
   * emas (RLS), lekin interfeysda chalkashlik bo'lardi.
   */
  function switchTenant(tenantId: string) {
    tenantStorage.set(tenantId)
    window.location.reload()
  }

  return { user, loading, isAuthenticated, login, fetchMe, logout, switchTenant }
})
