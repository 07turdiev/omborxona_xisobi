import { computed, ref } from 'vue'
import { defineStore } from 'pinia'

import { stockApi, type AdjustPayload, type StockFilters } from '@/api/stock'
import type { MovementReasonChoice, StockBalance, StockMovement, StockSummary } from '@/types'

export const useStockStore = defineStore('stock', () => {
  const items = ref<StockBalance[]>([])
  const movements = ref<StockMovement[]>([])
  const summary = ref<StockSummary | null>(null)
  const reasons = ref<MovementReasonChoice[]>([])

  const loading = ref(false)
  const saving = ref(false)
  const error = ref('')

  const filters = ref<StockFilters>({
    search: '',
    warehouse: '',
    category: '',
    status: '',
  })

  const isEmpty = computed(() => !loading.value && items.value.length === 0)

  async function load() {
    loading.value = true
    error.value = ''

    try {
      const [rows, totals] = await Promise.all([
        stockApi.list(filters.value),
        stockApi.summary(filters.value),
      ])

      items.value = rows.results
      summary.value = totals
    } catch {
      error.value = 'Qoldiqlarni olishda xatolik.'
    } finally {
      loading.value = false
    }
  }

  async function loadReasons() {
    if (reasons.value.length) return
    reasons.value = await stockApi.reasons()
  }

  async function loadMovements(params: Record<string, unknown> = {}) {
    const data = await stockApi.movements(params)
    movements.value = data.results
  }

  async function adjust(payload: AdjustPayload) {
    saving.value = true

    try {
      await stockApi.adjust(payload)
      await load()
      return { ok: true as const, errors: {} }
    } catch (err: unknown) {
      const response = (err as { response?: { data?: Record<string, string[]> } }).response
      return { ok: false as const, errors: response?.data ?? {} }
    } finally {
      saving.value = false
    }
  }

  async function stocktake(payload: {
    variant: number
    warehouse: number
    batch?: number | null
    counted_quantity: string
    note?: string
  }) {
    saving.value = true

    try {
      await stockApi.stocktake(payload)
      await load()
      return { ok: true as const, errors: {} }
    } catch (err: unknown) {
      const response = (err as { response?: { data?: Record<string, string[]> } }).response
      return { ok: false as const, errors: response?.data ?? {} }
    } finally {
      saving.value = false
    }
  }

  return {
    items, movements, summary, reasons, loading, saving, error, filters, isEmpty,
    load, loadReasons, loadMovements, adjust, stocktake,
  }
})
