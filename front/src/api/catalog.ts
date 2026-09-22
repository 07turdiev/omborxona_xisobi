import api from '@/api/client'
import type {
  CatalogCard,
  CatalogProduct,
  Category,
  Color,
  Paginated,
  Product,
  ProductImage,
  Size,
  Variant,
} from '@/types'

export interface ProductInput {
  category: number
  name: string
  /** Bo'sh yuborilsa nomdan yasaladi */
  slug?: string
  brand?: string
  description?: string
  material?: string
  care?: string
  sale_price: string
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

/** `-` — teskari tartib: `-stock` — qoldig'i ko'pi birinchi */
export type CatalogOrdering = 'newest' | 'name' | 'stock' | '-stock'

export interface CatalogFilters {
  search?: string
  category?: number | string
  in_stock?: 'true'
  low_stock?: 'true'
  ordering?: CatalogOrdering
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

  async createColor(payload: { name: string; hex_code: string }) {
    const { data } = await api.post<Color>('/colors/', payload)
    return data
  },

  async updateColor(id: number, payload: Partial<Color>) {
    const { data } = await api.patch<Color>(`/colors/${id}/`, payload)
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

  /**
   * Modelga bitta variant qo'shadi — aynan shu o'lcham × rang juftligi.
   * Juftlik bor bo'lsa, borini qaytaradi (server idempotent).
   */
  async addVariant(product: number, payload: { size: number | null; color: number | null }) {
    const { data } = await api.post<Variant>(`/products/${product}/variants/`, payload)
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

  // --- Katalog -----------------------------------------------------------

  async catalog(filters: CatalogFilters = {}) {
    const { data } = await api.get<Paginated<CatalogCard>>('/catalog/', {
      params: clean(filters),
    })
    return data
  },

  async catalogProduct(id: number) {
    const { data } = await api.get<CatalogProduct>(`/catalog/${id}/`)
    return data
  },

  // --- Rasmlar -----------------------------------------------------------

  async productImages(product: number) {
    const { data } = await api.get<ProductImage[]>('/product-images/', { params: { product } })
    return data
  },

  /**
   * Rasmni yuklaydi. `onProgress` 0 dan 1 gacha ulush oladi.
   *
   * `Content-Type` ataylab ko'rsatilgan: umumiy mijoz JSON sarlavhasi
   * bilan yaratilgan va shu holatda axios `FormData` ni JSON ga
   * aylantirib yuboradi — fayl umuman ketmaydi.
   */
  async uploadImage(
    product: number,
    file: File,
    color: number | null,
    onProgress?: (share: number) => void,
  ) {
    const body = new FormData()

    body.append('product', String(product))
    body.append('image', file)

    if (color !== null) body.append('color', String(color))

    const { data } = await api.post<ProductImage>('/product-images/', body, {
      headers: { 'Content-Type': 'multipart/form-data' },
      onUploadProgress: (event) => {
        if (event.total) onProgress?.(event.loaded / event.total)
      },
    })

    return data
  },

  async updateImage(id: number, payload: { color?: number | null; is_primary?: boolean }) {
    const { data } = await api.patch<ProductImage>(`/product-images/${id}/`, payload)
    return data
  },

  async removeImage(id: number) {
    await api.delete(`/product-images/${id}/`)
  },

  async reorderImages(product: number, images: number[]) {
    const { data } = await api.post<ProductImage[]>('/product-images/reorder/', {
      product,
      images,
    })
    return data
  },
}
