import api from '@/api/client'
import type { Category, Color, Paginated, Product, Size, Variant } from '@/types'

export interface ProductInput {
  category: number
  name: string
  brand?: string
  description?: string
  sale_price: string
  /** Bo'sh qoldirilsa kategoriyaning MXIK kodi ishlatiladi */
  mxik_code?: string
  package_code?: string
  is_active?: boolean
  size_ids?: number[]
  color_ids?: number[]
}

export interface VariantFilters {
  search?: string
  category?: number | string
  low_stock?: 'true'
  active?: 'true'
  page?: number
}

function clean(params: object) {
  return Object.fromEntries(
    Object.entries(params).filter(([, value]) => value !== '' && value != null),
  )
}

export const catalogApi = {
  async categories() {
    const { data } = await api.get<Category[]>('/categories/')
    return data
  },

  async createCategory(name: string) {
    const { data } = await api.post<Category>('/categories/', { name })
    return data
  },

  async updateCategory(id: number, payload: Partial<Category>) {
    const { data } = await api.patch<Category>(`/categories/${id}/`, payload)
    return data
  },

  async removeCategory(id: number) {
    await api.delete(`/categories/${id}/`)
  },

  async sizes() {
    const { data } = await api.get<Size[]>('/sizes/')
    return data
  },

  async createSize(payload: { name: string; position: number }) {
    const { data } = await api.post<Size>('/sizes/', payload)
    return data
  },

  async removeSize(id: number) {
    await api.delete(`/sizes/${id}/`)
  },

  async colors() {
    const { data } = await api.get<Color[]>('/colors/')
    return data
  },

  async createColor(name: string) {
    const { data } = await api.post<Color>('/colors/', { name })
    return data
  },

  async removeColor(id: number) {
    await api.delete(`/colors/${id}/`)
  },

  async products(filters: { search?: string; category?: number | string; page?: number } = {}) {
    const { data } = await api.get<Paginated<Product>>('/products/', { params: clean(filters) })
    return data
  },

  async product(id: number) {
    const { data } = await api.get<Product>(`/products/${id}/`)
    return data
  },

  async createProduct(payload: ProductInput) {
    const { data } = await api.post<Product>('/products/', payload)
    return data
  },

  async updateProduct(id: number, payload: Partial<ProductInput>) {
    const { data } = await api.patch<Product>(`/products/${id}/`, payload)
    return data
  },

  async variants(filters: VariantFilters = {}) {
    const { data } = await api.get<Paginated<Variant>>('/variants/', { params: clean(filters) })
    return data
  },

  async updateVariant(id: number, payload: Partial<Variant>) {
    const { data } = await api.patch<Variant>(`/variants/${id}/`, payload)
    return data
  },

  /** Skaner uchun: kod bo'yicha variant. Topilmasa 404 qaytadi. */
  async byBarcode(code: string) {
    const { data } = await api.get<Variant>('/variants/by-barcode/', { params: { code } })
    return data
  },
}
