import api from '@/api/client'
import type {
  Location,
  Paginated,
  StockCount,
  StockCountLine,
  StockMovement,
  WriteOff,
} from '@/types'

export interface TransferInput {
  source: number
  target: number
  note?: string
  lines: { variant: number; quantity: number }[]
}

export interface Transfer {
  id: number
  number: string
  date: string
  source_name: string
  target_name: string
  note: string
  created_by_name: string
  created_at: string
  lines: {
    id: number
    variant: number
    product_name: string
    variant_label: string
    sku: string
    quantity: number
  }[]
}

export const inventoryApi = {
  /** Joylar: ombor va savdo zali */
  async locations() {
    const { data } = await api.get<Location[]>('/locations/')
    return data
  },

  async transfers(page = 1) {
    const { data } = await api.get<Paginated<Transfer>>('/transfers/', { params: { page } })
    return data
  },

  /** Ombordan zalga (yoki teskari) ko'chiradi. */
  async transfer(payload: TransferInput) {
    const { data } = await api.post<Transfer>('/transfers/', payload)
    return data
  },

  async movements(filters: { variant?: number; reason?: string; page?: number } = {}) {
    const { data } = await api.get<Paginated<StockMovement>>('/movements/', { params: filters })
    return data
  },

  async counts(page = 1) {
    const { data } = await api.get<Paginated<StockCount>>('/stock-counts/', { params: { page } })
    return data
  },

  async count(id: number) {
    const { data } = await api.get<StockCount>(`/stock-counts/${id}/`)
    return data
  },

  async createCount(payload: {
    date: string
    category?: number | null
    location?: number | null
    note?: string
    lines: StockCountLine[]
  }) {
    const { data } = await api.post<StockCount>('/stock-counts/', payload)
    return data
  },

  async updateCount(id: number, payload: { note?: string; lines: StockCountLine[] }) {
    const { data } = await api.patch<StockCount>(`/stock-counts/${id}/`, payload)
    return data
  },

  async confirmCount(id: number) {
    const { data } = await api.post<StockCount>(`/stock-counts/${id}/confirm/`)
    return data
  },

  async removeCount(id: number) {
    await api.delete(`/stock-counts/${id}/`)
  },

  async writeOffs(page = 1) {
    const { data } = await api.get<Paginated<WriteOff>>('/write-offs/', { params: { page } })
    return data
  },

  async createWriteOff(payload: { variant: number; quantity: number; reason: string }) {
    const { data } = await api.post<WriteOff>('/write-offs/', payload)
    return data
  },
}
