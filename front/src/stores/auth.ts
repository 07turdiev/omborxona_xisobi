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

  // Router qo'riqchisi va App.vue birinchi yuklanishda `/me` ni bir vaqtda
  // so'rashi mumkin — bitta so'rov ikkalasiga yetadi
  let pendingMe: Promise<User> | null = null

  async function fetchMe() {
    pendingMe ??= api
      .get<User>('/auth/me/')
      .then(({ data }) => {
        user.value = data
        return data
      })
      .finally(() => {
        pendingMe = null
      })

    return pendingMe
  }

  /**
   * Joriy tashkilotdagi ruxsat.
   *
   * Faqat interfeys uchun: menyu va ustunlarni yashiradi. Haqiqiy himoya
   * serverda — ruxsatsiz so'rov 403 oladi, moliyaviy maydonlar esa
   * javobning o'zida tozalanadi.
   */
  function can(permission: string): boolean {
    return user.value?.current_tenant?.permissions?.includes(permission) ?? false
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

  return { user, loading, isAuthenticated, can, login, fetchMe, logout, switchTenant }
})
