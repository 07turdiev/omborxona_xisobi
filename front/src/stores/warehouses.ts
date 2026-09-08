import { computed, ref } from 'vue'
import { defineStore } from 'pinia'

import { warehousesApi, type WarehouseFilters } from '@/api/warehouses'
import type { Warehouse, WarehouseChoices, WarehouseInput, WarehouseSummary } from '@/types'

export const useWarehouseStore = defineStore('warehouses', () => {
  const items = ref<Warehouse[]>([])
  const summary = ref<WarehouseSummary | null>(null)
  const choices = ref<WarehouseChoices | null>(null)

  const loading = ref(false)
  const saving = ref(false)
  const error = ref('')

  const filters = ref<WarehouseFilters>({ search: '', goods_type: '', purpose: '' })

  const isEmpty = computed(() => !loading.value && items.value.length === 0)

  async function load() {
    loading.value = true
    error.value = ''

    try {
      const data = await warehousesApi.list(filters.value)
      items.value = data.results
    } catch {
      error.value = 'Omborlar ro‘yxatini olishda xatolik.'
    } finally {
      loading.value = false
    }
  }

  async function loadSummary() {
    try {
      summary.value = await warehousesApi.summary()
    } catch {
      // Sidebar'dagi hisoblagich — kritik emas, jim o'tamiz
    }
  }

  async function loadChoices() {
    if (choices.value) return
    choices.value = await warehousesApi.choices()
  }

  /** Saqlaydi va serverning maydon bo'yicha xatolarini qaytaradi. */
  async function save(payload: Partial<WarehouseInput>, id?: number) {
    saving.value = true

    try {
      if (id) {
        await warehousesApi.update(id, payload)
      } else {
        await warehousesApi.create(payload)
      }

      await Promise.all([load(), loadSummary()])
      return { ok: true as const, errors: {} }
    } catch (err: unknown) {
      const response = (err as { response?: { data?: Record<string, string[]> } }).response
      return { ok: false as const, errors: response?.data ?? {} }
    } finally {
      saving.value = false
    }
  }

  async function remove(id: number) {
    await warehousesApi.remove(id)
    await Promise.all([load(), loadSummary()])
  }

  return {
    items, summary, choices, loading, saving, error, filters, isEmpty,
    load, loadSummary, loadChoices, save, remove,
  }
})
