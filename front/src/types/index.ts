export interface MembershipBrief {
  tenant_id: string
  tenant_name: string
  tenant_slug: string
  role: string
  role_display: string
}

export interface User {
  id: number
  username: string
  email: string
  first_name: string
  last_name: string
  full_name: string
  phone: string
  is_superuser: boolean
  memberships: MembershipBrief[]
  current_tenant: MembershipBrief | null
}

export interface TokenPair {
  access: string
  refresh: string
}

/** DRF PageNumberPagination javobi */
export interface Paginated<T> {
  count: number
  next: string | null
  previous: string | null
  results: T[]
}

export type GoodsType =
  | 'universal'
  | 'electronics'
  | 'clothing'
  | 'food'
  | 'household'
  | 'construction'

export type WarehousePurpose = 'main' | 'retail' | 'transit'

export interface Warehouse {
  id: number
  code: string
  name: string
  goods_type: GoodsType
  goods_type_display: string
  purpose: WarehousePurpose
  purpose_display: string
  is_sellable: boolean
  manager: string
  phone: string
  address: string
  /** Decimal — backend satr sifatida qaytaradi, aniqlik yo'qolmasin */
  area: string | null
  capacity: string | null
  temperature: string
  notes: string
  is_active: boolean
  created_at: string
}

/** Yangi ombor yaratish / tahrirlash uchun forma qiymatlari */
export type WarehouseInput = Omit<
  Warehouse,
  'id' | 'created_at' | 'goods_type_display' | 'purpose_display' | 'is_sellable'
>

export interface WarehouseSummary {
  total: number
  active: number
  sellable: number
  by_goods_type: { goods_type: GoodsType; count: number }[]
}

export interface Choice {
  value: string
  label: string
}

export interface WarehouseChoices {
  goods_types: Choice[]
  purposes: Choice[]
}
