import api from '@/api/client'
import type {
  MovementReasonChoice,
  Paginated,
  StockBalance,
  StockMovement,
  StockSummary,
} from '@/types'

export interface StockFilters {
  search?: string
  warehouse?: string | number
  category?: string | number
  status?: string
}

export interface AdjustPayload {
  variant: number
  warehouse: number
  batch?: number | null
  quantity: string
  reason: string
  note?: string
}

function clean(filters: object) {
  return Object.fromEntries(
    Object.entries(filters).filter(([, value]) => value !== '' && value != null),
  )
}

export const stockApi = {
  async list(filters: StockFilters = {}) {
    const { data } = await api.get<Paginated<StockBalance>>('/stock/', {
      params: clean(filters),
    })
    return data
  },

  async summary(filters: StockFilters = {}) {
    const { data } = await api.get<StockSummary>('/stock/summary/', {
      params: clean(filters),
    })
    return data
  },

  async movements(filters: Record<string, unknown> = {}) {
    const { data } = await api.get<Paginated<StockMovement>>('/stock-movements/', {
      params: clean(filters),
    })
    return data
  },

  async reasons() {
    const { data } = await api.get<MovementReasonChoice[]>('/stock/reasons/')
    return data
  },

  async adjust(payload: AdjustPayload) {
    const { data } = await api.post<StockMovement>('/stock/adjust/', payload)
    return data
  },

  async stocktake(payload: {
    variant: number
    warehouse: number
    batch?: number | null
    counted_quantity: string
    note?: string
  }) {
    const { data } = await api.post<StockMovement>('/stock/stocktake/', payload)
    return data
  },
}
