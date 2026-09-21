import api from '@/api/client'
import type { Paginated, Purchase, PurchaseLine, Supplier, SupplierPayment } from '@/types'

export interface PurchaseInput {
  date: string
  supplier: number | null
  note?: string
  amount_paid?: string
  lines: Pick<PurchaseLine, 'variant' | 'quantity' | 'unit_cost' | 'new_sale_price'>[]
}

export const purchasesApi = {
  async list(filters: { status?: string; supplier?: number; page?: number } = {}) {
    const { data } = await api.get<Paginated<Purchase>>('/purchases/', { params: filters })
    return data
  },

  async get(id: number) {
    const { data } = await api.get<Purchase>(`/purchases/${id}/`)
    return data
  },

  async create(payload: PurchaseInput) {
    const { data } = await api.post<Purchase>('/purchases/', payload)
    return data
  },

  async update(id: number, payload: PurchaseInput) {
    const { data } = await api.patch<Purchase>(`/purchases/${id}/`, payload)
    return data
  },

  async remove(id: number) {
    await api.delete(`/purchases/${id}/`)
  },

  async confirm(id: number) {
    const { data } = await api.post<Purchase>(`/purchases/${id}/confirm/`)
    return data
  },

  async cancel(id: number) {
    const { data } = await api.post<Purchase>(`/purchases/${id}/cancel/`)
    return data
  },

  async suppliers(page = 1) {
    const { data } = await api.get<Paginated<Supplier>>('/suppliers/', { params: { page } })
    return data
  },

  async createSupplier(payload: { name: string; phone?: string; note?: string }) {
    const { data } = await api.post<Supplier>('/suppliers/', payload)
    return data
  },

  async updateSupplier(id: number, payload: Partial<Supplier>) {
    const { data } = await api.patch<Supplier>(`/suppliers/${id}/`, payload)
    return data
  },

  async payments(supplier?: number) {
    const { data } = await api.get<Paginated<SupplierPayment>>('/supplier-payments/', {
      params: supplier ? { supplier } : {},
    })

    return data
  },

  async createPayment(payload: { supplier: number; date: string; amount: string; note?: string }) {
    const { data } = await api.post<SupplierPayment>('/supplier-payments/', payload)
    return data
  },
}
