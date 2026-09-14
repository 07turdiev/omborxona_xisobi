import api, { downloadFile } from '@/api/client'
import type { Debt, DebtSummary, Paginated } from '@/types'

export interface DebtFilters {
  search?: string
  /** `active` | `overdue` | `paid` | `cancelled` */
  status?: string
  customer_type?: string
  warehouse?: string | number
  partner?: string | number
  page?: number
}

export interface PaymentInput {
  amount: string
  method: string
  note?: string
  /** Takroriy yuborishdan himoya: bir oyna — bitta kalit */
  request_key: string
}

function clean(params: object) {
  return Object.fromEntries(
    Object.entries(params).filter(([, value]) => value !== '' && value != null),
  )
}

export const debtsApi = {
  async list(filters: DebtFilters = {}) {
    const { data } = await api.get<Paginated<Debt>>('/debts/', { params: clean(filters) })
    return data
  },

  async summary(filters: DebtFilters = {}) {
    const { status: _status, page: _page, ...rest } = filters
    const { data } = await api.get<DebtSummary>('/debts/summary/', { params: clean(rest) })
    return data
  },

  async pay(id: number, payload: PaymentInput) {
    const { data } = await api.post<Debt>(`/debts/${id}/pay/`, payload)
    return data
  },

  exportExcel(filters: DebtFilters = {}) {
    return downloadFile('/debts/export/', clean(filters), 'qarzdorlar.xlsx')
  },
}
