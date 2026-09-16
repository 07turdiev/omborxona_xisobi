import api from '@/api/client'
import type { ExchangeResult, Paginated, RefundMethod, Sale, SaleReturn } from '@/types'

export interface SaleLineInput {
  variant: number
  quantity: number
  unit_price: string
  discount_percent?: string
  discount_amount?: string
}

export interface SaleInput {
  lines: SaleLineInput[]
  discount_amount?: string
  discount_percent?: string
  cash_amount: string
  card_amount: string
  /** Takroriy yuborishdan himoya */
  request_key: string
}

export interface ReturnInput {
  sale: number
  items: { sale_line: number; quantity: number }[]
  refund_method: RefundMethod
  request_key: string
}

export interface ExchangeInput extends ReturnInput {
  lines: SaleLineInput[]
  cash_amount: string
  card_amount: string
}

export const salesApi = {
  async list(filters: { status?: string; date_from?: string; date_to?: string; page?: number } = {}) {
    const { data } = await api.get<Paginated<Sale>>('/sales/', { params: filters })
    return data
  },

  /** Chek raqami bo'yicha (qaytarish uchun skaner qilinadi). */
  async byNumber(number: string) {
    const { data } = await api.get<Paginated<Sale>>('/sales/', {
      params: { number: number.trim() },
    })

    return data.results[0] ?? null
  },

  async get(id: number) {
    const { data } = await api.get<Sale>(`/sales/${id}/`)
    return data
  },

  async create(payload: SaleInput) {
    const { data } = await api.post<Sale>('/sales/', payload)
    return data
  },

  async void(id: number) {
    const { data } = await api.post<Sale>(`/sales/${id}/void/`)
    return data
  },

  async returns(filters: { sale?: number; page?: number } = {}) {
    const { data } = await api.get<Paginated<SaleReturn>>('/returns/', { params: filters })
    return data
  },

  async createReturn(payload: ReturnInput) {
    const { data } = await api.post<SaleReturn>('/returns/', payload)
    return data
  },

  async exchange(payload: ExchangeInput) {
    const { data } = await api.post<ExchangeResult>('/exchanges/', payload)
    return data
  },
}
