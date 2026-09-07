import { computed, ref } from 'vue'
import { defineStore } from 'pinia'

import api, { tokenStorage } from '@/api/client'
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
    user.value = null
  }

  return { user, loading, isAuthenticated, login, fetchMe, logout }
})
