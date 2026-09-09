import api from '@/api/client'
import type {
  MembershipRow,
  Paginated,
  RoleChoice,
  TenantSettings,
  WarehouseAccessRow,
} from '@/types'

export interface MemberInput {
  username: string
  password?: string
  first_name?: string
  last_name?: string
  email?: string
  phone?: string
  role: string
}

function clean(params: object) {
  return Object.fromEntries(
    Object.entries(params).filter(([, value]) => value !== '' && value != null),
  )
}

export const tenantsApi = {
  async settings() {
    const { data } = await api.get<TenantSettings>('/tenant/current/')
    return data
  },

  async saveSettings(payload: Partial<TenantSettings>) {
    const { data } = await api.patch<TenantSettings>('/tenant/current/', payload)
    return data
  },

  async members(filters: { search?: string; role?: string } = {}) {
    const { data } = await api.get<Paginated<MembershipRow>>('/members/', {
      params: clean(filters),
    })
    return data
  },

  async roles() {
    const { data } = await api.get<RoleChoice[]>('/members/roles/')
    return data
  },

  async addMember(payload: MemberInput) {
    const { data } = await api.post<MembershipRow>('/members/', payload)
    return data
  },

  async updateMember(id: number, payload: { role?: string; is_active?: boolean }) {
    const { data } = await api.patch<MembershipRow>(`/members/${id}/`, payload)
    return data
  },

  async removeMember(id: number) {
    await api.delete(`/members/${id}/`)
  },

  async warehouseAccess(user?: number) {
    const { data } = await api.get<Paginated<WarehouseAccessRow>>('/warehouse-access/', {
      params: clean({ user }),
    })
    return data
  },

  async grantAccess(payload: { warehouse: number; user: number; level: string }) {
    const { data } = await api.post<WarehouseAccessRow>('/warehouse-access/', payload)
    return data
  },

  async revokeAccess(id: number) {
    await api.delete(`/warehouse-access/${id}/`)
  },
}
