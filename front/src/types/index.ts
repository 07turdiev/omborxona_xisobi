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

// -- Katalog ---------------------------------------------------------

export interface Category {
  id: number
  name: string
  parent: number | null
  path: string
  depth: number
  default_unit: string
  code_prefix: string
  is_active: boolean
  product_count: number
}

export type AttributeValueType = 'text' | 'number' | 'choice' | 'boolean'

export interface AttributeDefinition {
  id: number
  category: number
  category_name: string
  key: string
  name: string
  value_type: AttributeValueType
  value_type_display: string
  unit: string
  choices: string[]
  default_value: string
  is_required: boolean
  is_variant_axis: boolean
  uniqueness: number
  position: number
}

export interface ProductUnit {
  id: number
  variant: number
  unit: string
  /** Decimal — satr sifatida keladi */
  factor_to_base: string
  is_default_purchase: boolean
  is_default_sale: boolean
}

export interface Barcode {
  id: number
  variant: number
  code: string
  code_normalized: string
  code_type: string
}

export interface Variant {
  id: number
  product: number
  product_name: string
  category: number
  sku: string
  name: string
  display_name: string
  /** Xom qiymatlar: {"qalinlik": "12 mm"} */
  attributes: Record<string, string | boolean | null>
  /** To'liq juftliklar: {"qalinlik": {"raw": "12 mm", "num": "0.012"}} */
  attributes_full: Record<string, { raw: unknown; num: string | null }>
  purchase_price: string | null
  sale_price: string | null
  currency: string
  min_stock: string | null
  is_active: boolean
  units: ProductUnit[]
  barcodes: Barcode[]
}

export interface Product {
  id: number
  category: number
  category_name: string
  name: string
  brand: string
  model: string
  description: string
  base_unit: string
  effective_unit: string
  is_active: boolean
  variants: Variant[]
}

export type ProductInput = Partial<
  Omit<Product, 'id' | 'category_name' | 'effective_unit' | 'variants'>
> & { sku?: string }

// -- Qoldiqlar -------------------------------------------------------

export interface StockBalance {
  id: number
  variant: number
  product_name: string
  variant_name: string
  sku: string
  unit: string
  category_name: string
  warehouse: number
  warehouse_name: string
  warehouse_purpose: WarehousePurpose
  batch: number | null
  batch_code: string | null
  expiry_date: string | null
  is_expired: boolean
  /** Decimal — satr sifatida keladi, aniqlik yo'qolmasin */
  quantity: string
  reserved_quantity: string
  available_quantity: string
  is_sellable: boolean
  is_overallocated: boolean
  is_low: boolean
  purchase_price: string | null
  sale_price: string | null
  /** FIFO qatlamlaridan hisoblangan haqiqiy qiymat */
  cost_value: string
  /** Qatlamlar bo'yicha vaznlangan o'rtacha birlik tannarxi */
  avg_unit_cost: string | null
}

export interface StockSummary {
  positions: number
  units: string
  reserved: string
  /** FIFO bo'yicha haqiqiy tannarx */
  cost_value: string
  purchase_value: string
  retail_value: string
  low_count: number
  expired_count: number
}

export interface StockMovement {
  id: number
  variant: number
  product_name: string
  sku: string
  warehouse: number
  warehouse_name: string
  batch: number | null
  batch_code: string | null
  quantity: string
  reason: string
  reason_display: string
  unit_cost: string | null
  currency: string
  document_type: string
  document_id: number | null
  note: string
  meta: Record<string, unknown>
  occurred_at: string
  user_name: string
}

export interface MovementReasonChoice {
  value: string
  label: string
  direction: 'in' | 'out' | 'both'
  is_loss: boolean
}

// -- Kontragentlar ---------------------------------------------------

export interface Partner {
  id: number
  name: string
  is_supplier: boolean
  is_customer: boolean
  role_display: string
  inn: string
  phone: string
  email: string
  contact: string
  address: string
  bank: string
  note: string
  is_active: boolean
  created_at: string
}

// -- Hujjatlar -------------------------------------------------------

export type DocumentKind = 'purchase' | 'sale' | 'return_in' | 'return_out'
export type DocumentStatus = 'draft' | 'confirmed' | 'cancelled'

export interface DocumentLine {
  id: number
  variant: number
  product_name: string
  variant_name: string
  sku: string
  batch: number | null
  batch_code: string | null
  unit: string
  base_unit: string
  /** Decimal — satr sifatida */
  factor: string
  quantity: string
  quantity_base: string
  unit_price: string
  unit_price_base: string
  discount_percent: string
  line_total: string
  line_cost: string
  note: string
  position: number
}

/** Hujjat yaratishda yuboriladigan qator */
export interface DocumentLineInput {
  variant: number | null
  batch?: number | null
  unit?: string
  quantity: string
  unit_price: string
  discount_percent?: string
  note?: string
}

export interface Document {
  id: number
  kind: DocumentKind
  kind_display: string
  number: string
  date: string
  status: DocumentStatus
  status_display: string
  is_editable: boolean
  warehouse: number
  warehouse_name: string
  partner: number | null
  partner_name: string | null
  currency: string
  external_number: string
  note: string
  total_amount: string
  total_cost: string
  profit: string
  confirmed_at: string | null
  cancelled_at: string | null
  lines: DocumentLine[]
  line_count: number
}

export interface DocumentTotals {
  count: number
  amount: string
  cost: string
  profit: string
}

export interface DocumentSummary {
  purchases: DocumentTotals
  sales: DocumentTotals
  profit: string
  margin_percent: number
}
