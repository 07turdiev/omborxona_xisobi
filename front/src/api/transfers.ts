import api from '@/api/client'
import type { Paginated, Transfer, TransferLineInput } from '@/types'

export interface TransferInput {
  date: string
  from_warehouse: number | null
  to_warehouse: number | null
  transit_warehouse: number | null
  note?: string
  items: TransferLineInput[]
}

function clean(params: object) {
  return Object.fromEntries(
    Object.entries(params).filter(([, value]) => value !== '' && value != null),
  )
}

export const transfersApi = {
  async list(filters: { status?: string; warehouse?: string | number; search?: string } = {}) {
    const { data } = await api.get<Paginated<Transfer>>('/transfers/', {
      params: clean(filters),
    })
    return data
  },

  async create(payload: TransferInput) {
    const { data } = await api.post<Transfer>('/transfers/', payload)
    return data
  },

  async update(id: number, payload: Partial<TransferInput>) {
    const { data } = await api.patch<Transfer>(`/transfers/${id}/`, payload)
    return data
  },

  async remove(id: number) {
    await api.delete(`/transfers/${id}/`)
  },

  async send(id: number) {
    const { data } = await api.post<Transfer>(`/transfers/${id}/send/`)
    return data
  },

  /** `received` — {qator_id: miqdor}. Bo'sh bo'lsa hammasi to'liq qabul qilinadi. */
  async receive(id: number, received: Record<number, string> = {}) {
    const { data } = await api.post<Transfer>(`/transfers/${id}/receive/`, { received })
    return data
  },

  async cancel(id: number) {
    const { data } = await api.post<Transfer>(`/transfers/${id}/cancel/`)
    return data
  },

  async transitWarehouses() {
    const { data } = await api.get<{ id: number; name: string; code: string }[]>(
      '/transfers/transit-warehouses/',
    )
    return data
  },
}
