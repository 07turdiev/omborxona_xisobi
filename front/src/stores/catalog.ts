import { computed, ref } from 'vue'
import { defineStore } from 'pinia'

import { catalogApi, type ProductFilters } from '@/api/catalog'
import type { AttributeDefinition, Category, Product, ProductInput } from '@/types'

export const useCatalogStore = defineStore('catalog', () => {
  const categories = ref<Category[]>([])
  const products = ref<Product[]>([])

  /** Kategoriya bo'yicha atribut ta'riflari keshi. */
  const attributeCache = ref<Record<number, AttributeDefinition[]>>({})

  const loading = ref(false)
  const saving = ref(false)
  const error = ref('')

  const filters = ref<ProductFilters>({ search: '', category: '' })

  const isEmpty = computed(() => !loading.value && products.value.length === 0)

  /** Daraxtni tekis ro'yxat sifatida, nomi oldiga chuqurlik bo'shlig'i bilan. */
  const categoryOptions = computed(() =>
    categories.value.map((category) => ({
      ...category,
      label: `${'— '.repeat(Math.max(0, category.depth - 1))}${category.name}`,
    })),
  )

  async function loadCategories() {
    categories.value = await catalogApi.categories()
  }

  async function loadProducts() {
    loading.value = true
    error.value = ''

    try {
      const data = await catalogApi.products(filters.value)
      products.value = data.results
    } catch {
      error.value = 'Mahsulotlar ro‘yxatini olishda xatolik.'
    } finally {
      loading.value = false
    }
  }

  /** Kategoriya uchun atributlar — meros bilan, keshlangan. */
  async function attributesFor(categoryId: number): Promise<AttributeDefinition[]> {
    if (attributeCache.value[categoryId]) {
      return attributeCache.value[categoryId]
    }

    const definitions = await catalogApi.categoryAttributes(categoryId)
    attributeCache.value[categoryId] = definitions

    return definitions
  }

  /** Atribut ta'rifi o'zgarganda keshni tozalash uchun. */
  function clearAttributeCache() {
    attributeCache.value = {}
  }

  async function saveProduct(payload: ProductInput, id?: number) {
    saving.value = true

    try {
      if (id) {
        await catalogApi.updateProduct(id, payload)
      } else {
        await catalogApi.createProduct(payload)
      }

      await loadProducts()
      return { ok: true as const, errors: {} }
    } catch (err: unknown) {
      const response = (err as { response?: { data?: Record<string, string[]> } }).response
      return { ok: false as const, errors: response?.data ?? {} }
    } finally {
      saving.value = false
    }
  }

  async function saveVariantAttributes(
    variantId: number,
    values: Record<string, unknown>,
  ) {
    saving.value = true

    try {
      await catalogApi.updateVariant(variantId, {
        attributes: values as Record<string, string | boolean | null>,
      })
      await loadProducts()
      return { ok: true as const, errors: {} }
    } catch (err: unknown) {
      const response = (err as { response?: { data?: Record<string, string[]> } }).response
      return { ok: false as const, errors: response?.data ?? {} }
    } finally {
      saving.value = false
    }
  }

  async function removeProduct(id: number) {
    await catalogApi.removeProduct(id)
    await loadProducts()
  }

  return {
    categories, products, loading, saving, error, filters, isEmpty,
    categoryOptions,
    loadCategories, loadProducts, attributesFor, clearAttributeCache,
    saveProduct, saveVariantAttributes, removeProduct,
  }
})
