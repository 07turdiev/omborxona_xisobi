import api, { downloadFile } from '@/api/client'
import type { Dashboard, Expense, Paginated, SalesReport, StockReport, SupplierBalance, TopProduct } from '@/types'

/** `type` — `interface` uchun indeks imzosi bo'lmaydi, so'rov parametrlariga o'tmaydi. */
export type Period = {
  date_from: string
  date_to: string
}

export const reportsApi = {
  async dashboard() {
    const { data } = await api.get<Dashboard>('/reports/dashboard/')
    return data
  },

  async sales(period: Period) {
    const { data } = await api.get<SalesReport>('/reports/sales/', { params: period })
    return data
  },

  async topProducts(period: Period, limit = 10) {
    const { data } = await api.get<TopProduct[]>('/reports/top-products/', {
      params: { ...period, limit },
    })

    return data
  },

  async stock(filters: { category?: number | string; low_stock?: 'true' } = {}) {
    const { data } = await api.get<StockReport>('/reports/stock/', { params: filters })
    return data
  },

  async suppliers() {
    const { data } = await api.get<SupplierBalance[]>('/reports/suppliers/')
    return data
  },

  exportSales(period: Period) {
    return downloadFile('/reports/sales/export/', period)
  },

  exportStock(filters: { category?: number | string; low_stock?: 'true' } = {}) {
    return downloadFile('/reports/stock/export/', filters)
  },

  exportMovements(period: Period) {
    return downloadFile('/reports/movements/export/', period)
  },
}

export const expensesApi = {
  async list(filters: { date_from?: string; date_to?: string; category?: string; page?: number } = {}) {
    const { data } = await api.get<Paginated<Expense>>('/expenses/', { params: filters })
    return data
  },

  async create(payload: { date: string; category: string; amount: string; note?: string }) {
    const { data } = await api.post<Expense>('/expenses/', payload)
    return data
  },

  async remove(id: number) {
    await api.delete(`/expenses/${id}/`)
  },
}
