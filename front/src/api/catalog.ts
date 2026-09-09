import api from '@/api/client'
import type {
  AttributeDefinition,
  Barcode,
  Category,
  Paginated,
  Product,
  ProductInput,
  ProductUnit,
  Variant,
} from '@/types'

export interface ProductFilters {
  search?: string
  category?: string | number
  is_active?: string
}

export const catalogApi = {
  async categories() {
    // Kategoriya ro'yxati sahifalanmaydi — daraxt to'liq kerak
    const { data } = await api.get<Category[]>('/categories/')
    return data
  },

  async createCategory(payload: Partial<Category>) {
    const { data } = await api.post<Category>('/categories/', payload)
    return data
  },

  async updateCategory(id: number, payload: Partial<Category>) {
    const { data } = await api.patch<Category>(`/categories/${id}/`, payload)
    return data
  },

  async removeCategory(id: number) {
    await api.delete(`/categories/${id}/`)
  },

  /** Kategoriyada amal qiladigan atributlar — **meros bilan**. */
  async categoryAttributes(id: number) {
    const { data } = await api.get<AttributeDefinition[]>(`/categories/${id}/attributes/`)
    return data
  },

  /** Faqat shu kategoriyaning **o'z** atributlari — meros olganlarisiz. */
  async attributeDefinitions(category: number) {
    const { data } = await api.get<Paginated<AttributeDefinition>>(
      '/attribute-definitions/',
      { params: { category } },
    )
    return data.results
  },

  async createAttributeDefinition(payload: Partial<AttributeDefinition>) {
    const { data } = await api.post<AttributeDefinition>('/attribute-definitions/', payload)
    return data
  },

  async updateAttributeDefinition(id: number, payload: Partial<AttributeDefinition>) {
    const { data } = await api.patch<AttributeDefinition>(
      `/attribute-definitions/${id}/`,
      payload,
    )
    return data
  },

  async removeAttributeDefinition(id: number) {
    await api.delete(`/attribute-definitions/${id}/`)
  },

  async products(filters: ProductFilters = {}) {
    const params = Object.fromEntries(
      Object.entries(filters).filter(([, value]) => value !== '' && value != null),
    )
    const { data } = await api.get<Paginated<Product>>('/products/', { params })
    return data
  },

  async createProduct(payload: ProductInput) {
    const { data } = await api.post<Product>('/products/', payload)
    return data
  },

  async updateProduct(id: number, payload: ProductInput) {
    const { data } = await api.patch<Product>(`/products/${id}/`, payload)
    return data
  },

  async removeProduct(id: number) {
    await api.delete(`/products/${id}/`)
  },

  async variant(id: number) {
    const { data } = await api.get<Variant>(`/variants/${id}/`)
    return data
  },

  async updateVariant(id: number, payload: Partial<Variant>) {
    const { data } = await api.patch<Variant>(`/variants/${id}/`, payload)
    return data
  },

  async createVariant(payload: Partial<Variant>) {
    const { data } = await api.post<Variant>('/variants/', payload)
    return data
  },

  async byBarcode(code: string) {
    const { data } = await api.get<Variant>('/variants/by-barcode/', { params: { code } })
    return data
  },

  async createProductUnit(payload: Partial<ProductUnit>) {
    const { data } = await api.post<ProductUnit>('/product-units/', payload)
    return data
  },

  async removeProductUnit(id: number) {
    await api.delete(`/product-units/${id}/`)
  },

  async createBarcode(payload: Partial<Barcode>) {
    const { data } = await api.post<Barcode>('/barcodes/', payload)
    return data
  },

  async removeBarcode(id: number) {
    await api.delete(`/barcodes/${id}/`)
  },
}
