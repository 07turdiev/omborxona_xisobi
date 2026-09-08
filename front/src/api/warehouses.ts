import api from '@/api/client'
import type {
  Paginated,
  Warehouse,
  WarehouseChoices,
  WarehouseInput,
  WarehouseSummary,
} from '@/types'

export interface WarehouseFilters {
  search?: string
  goods_type?: string
  purpose?: string
  is_active?: string
}

export const warehousesApi = {
  async list(filters: WarehouseFilters = {}) {
    const params = Object.fromEntries(
      Object.entries(filters).filter(([, value]) => value),
    )
    const { data } = await api.get<Paginated<Warehouse>>('/warehouses/', { params })
    return data
  },

  async create(payload: Partial<WarehouseInput>) {
    const { data } = await api.post<Warehouse>('/warehouses/', payload)
    return data
  },

  async update(id: number, payload: Partial<WarehouseInput>) {
    const { data } = await api.patch<Warehouse>(`/warehouses/${id}/`, payload)
    return data
  },

  async remove(id: number) {
    await api.delete(`/warehouses/${id}/`)
  },

  async summary() {
    const { data } = await api.get<WarehouseSummary>('/warehouses/summary/')
    return data
  },

  async choices() {
    const { data } = await api.get<WarehouseChoices>('/warehouses/choices/')
    return data
  },
}
