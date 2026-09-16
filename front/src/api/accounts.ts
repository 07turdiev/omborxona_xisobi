import api from '@/api/client'
import type { Paginated, Role, ShopSettings, User } from '@/types'

export const accountsApi = {
  async me() {
    const { data } = await api.get<User>('/auth/me/')
    return data
  },

  async users(page = 1) {
    const { data } = await api.get<Paginated<User>>('/users/', { params: { page } })
    return data
  },

  async createUser(payload: {
    username: string
    password: string
    role: Role
    first_name?: string
    last_name?: string
    phone?: string
  }) {
    const { data } = await api.post<User>('/users/', payload)
    return data
  },

  async updateUser(id: number, payload: Partial<User>) {
    const { data } = await api.patch<User>(`/users/${id}/`, payload)
    return data
  },

  async setPassword(id: number, password: string) {
    await api.post(`/users/${id}/set-password/`, { password })
  },
}

export const settingsApi = {
  async get() {
    const { data } = await api.get<ShopSettings>('/settings/')
    return data
  },

  async save(payload: Partial<ShopSettings>) {
    const { data } = await api.patch<ShopSettings>('/settings/', payload)
    return data
  },
}
