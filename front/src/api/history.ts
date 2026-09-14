import api from '@/api/client'
import type { AuditEventRow, HistoryMeta, Paginated } from '@/types'

export interface HistoryFilters {
  search?: string
  object_type?: string
  action?: string
  warehouse?: string | number
  user?: string | number
  date_from?: string
  date_to?: string
  page?: number
}

function clean(params: object) {
  return Object.fromEntries(
    Object.entries(params).filter(([, value]) => value !== '' && value != null),
  )
}

export const historyApi = {
  async list(filters: HistoryFilters = {}) {
    const { data } = await api.get<Paginated<AuditEventRow>>('/history/', {
      params: clean(filters),
    })
    return data
  },

  async meta() {
    const { data } = await api.get<HistoryMeta>('/history/meta/')
    return data
  },
}
