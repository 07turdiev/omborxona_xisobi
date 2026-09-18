/** Server javoblarining tiplari. Pul qiymatlari doim satr. */

export interface Paginated<T> {
  count: number
  next: string | null
  previous: string | null
  results: T[]
}

export type Role = 'admin' | 'cashier'

export interface User {
  id: number
  username: string
  first_name: string
  last_name: string
  full_name: string
  phone: string
  role: Role
  role_display: string
  is_active: boolean
  last_login: string | null
}

export interface ShopSettings {
  shop_name: string
  label_width_mm: number
  label_height_mm: number
  /** Chek qog'ozi — printer drayveridagi maxsus qog'oz bilan bir xil bo'lishi kerak */
  receipt_width_mm: number
  receipt_page_height_mm: number
  max_discount_percent: string
}

export interface Category {
  id: number
  name: string
  product_count?: number
  /** Soliq tasnifi kodi — kategoriyadagi mahsulotlar uchun standart */
  mxik_code: string
  package_code: string
}

export interface Size {
  id: number
  name: string
  position: number
}

export interface Color {
  id: number
  name: string
  /** #RRGGBB — katalogdagi rang doirachasi */
  hex_code: string
}

/** O'lcham bo'yicha qoldiq, hamma ranglar yig'indisi */
export interface SizeStock {
  size_id: number
  size_name: string
  position: number
  quantity: number
}

/** Katalogdagi karta — ro'yxat uchun yengil javob */
export interface CatalogCard {
  id: number
  name: string
  slug: string
  category: number
  category_name: string
  brand: string
  sale_price: string
  total_stock: number
  size_stock: SizeStock[]
  primary_image: ProductImage | null
}

export interface ImageGroup {
  /** `null` — umumiy rasmlar (o'lcham jadvali, brend yorlig'i) */
  color: number | null
  color_name: string | null
  hex_code: string | null
  images: ProductImage[]
}

export interface CatalogVariant {
  id: number
  size: number | null
  size_name: string | null
  color: number | null
  color_name: string | null
  barcode: string
  price: string
  /** Faqat administrator javobida */
  average_cost?: string
  stock_quantity: number
  is_active: boolean
}

export interface CatalogProduct extends CatalogCard {
  description: string
  material: string
  care: string
  image_groups: ImageGroup[]
  colors: Color[]
  sizes: Size[]
  variants: CatalogVariant[]
}

export interface Variant {
  id: number
  product: number
  product_name: string
  size: number | null
  size_name: string | null
  color: number | null
  color_name: string | null
  label: string
  sku: string
  barcode: string
  sale_price: string | null
  price: string
  /** Faqat administrator javobida bo'ladi */
  average_cost?: string
  stock_quantity: number
  min_stock: number
  is_active: boolean
}

export interface ProductImage {
  id: number
  /** Bo'sh bo'lsa rasm butun mahsulotga tegishli */
  color: number | null
  thumb: string
  medium: string
  large: string
  is_primary: boolean
  sort_order: number
}

export interface Product {
  id: number
  category: number
  category_name: string
  name: string
  brand: string
  description: string
  material: string
  care: string
  /** Onlayn do'kon manzili uchun. Hozir hech qayerda ko'rsatilmaydi. */
  slug: string
  sale_price: string
  images: ProductImage[]
  /** Bo'sh bo'lsa kategoriyaniki ishlatiladi */
  mxik_code: string
  package_code: string
  /** Amaldagi kod: mahsulotniki yoki kategoriyaniki */
  effective_mxik_code: string
  is_active: boolean
  variants: Variant[]
}

export interface Supplier {
  id: number
  name: string
  phone: string
  note: string
  is_active: boolean
  balance: string
}

export interface SupplierPayment {
  id: number
  supplier: number
  supplier_name: string
  date: string
  amount: string
  note: string
  created_at: string
}

export type PurchaseStatus = 'draft' | 'confirmed' | 'cancelled'

export interface PurchaseLine {
  id?: number
  variant: number
  product_name?: string
  variant_label?: string
  sku?: string
  barcode?: string
  quantity: number
  unit_cost: string
  line_total?: string
}

export interface Purchase {
  id: number
  number: string
  date: string
  supplier: number | null
  supplier_name: string | null
  status: PurchaseStatus
  status_display: string
  note: string
  total: string
  amount_paid: string
  debt: string
  is_editable: boolean
  confirmed_at: string | null
  cancelled_at: string | null
  lines: PurchaseLine[]
  created_at: string
}

export interface SaleLine {
  id: number
  variant: number
  product_name: string
  variant_label: string
  sku: string
  barcode: string
  quantity: number
  unit_price: string
  discount_amount: string
  line_total: string
  /** Faqat administrator javobida */
  unit_cost?: string
  line_cost?: string
  profit?: string
  returned_quantity: number
}

export interface Sale {
  id: number
  number: string
  created_at: string
  cashier: number | null
  cashier_name: string | null
  subtotal: string
  discount_total: string
  total: string
  cash_amount: string
  card_amount: string
  status: 'completed' | 'voided'
  status_display: string
  voided_at: string | null
  fiscal_receipt_id: string
  fiscal_qr_url: string
  lines: SaleLine[]
  /** Faqat administrator javobida */
  profit?: string
}

export type RefundMethod = 'cash' | 'card'

export interface SaleReturnLine {
  id: number
  sale_line: number
  product_name: string
  variant_label: string
  sku: string
  quantity: number
  unit_cost?: string
  refund_amount: string
}

export interface SaleReturn {
  id: number
  number: string
  created_at: string
  sale: number
  sale_number: string
  total: string
  refund_method: RefundMethod
  refund_method_display: string
  fiscal_receipt_id: string
  fiscal_qr_url: string
  lines: SaleReturnLine[]
}

export interface ExchangeResult {
  sale_return: SaleReturn
  sale: Sale
  difference: string
}

export interface StockMovement {
  id: number
  variant: number
  product_name: string
  variant_label: string
  sku: string
  quantity: number
  reason: string
  reason_display: string
  document_type: string
  document_id: number | null
  unit_cost: string
  user: number | null
  user_name: string | null
  created_at: string
}

export interface StockCountLine {
  id?: number
  variant: number
  product_name?: string
  variant_label?: string
  sku?: string
  expected_quantity?: number
  counted_quantity: number
  difference?: number
  average_cost?: string
}

export interface StockCount {
  id: number
  number: string
  date: string
  status: 'draft' | 'confirmed'
  status_display: string
  category: number | null
  category_name: string | null
  note: string
  confirmed_at: string | null
  lines: StockCountLine[]
  created_at: string
}

export interface WriteOff {
  id: number
  variant: number
  product_name: string
  variant_label: string
  sku: string
  quantity: number
  reason: string
  unit_cost: string
  created_at: string
}

export type ExpenseCategory = 'rent' | 'salary' | 'utilities' | 'other'

export interface Expense {
  id: number
  date: string
  category: ExpenseCategory
  category_display: string
  amount: string
  note: string
  created_at: string
}

export interface DashboardPeriod {
  revenue: string
  receipts: number
  average_receipt: string
  gross_profit: string
}

export interface Dashboard {
  today: DashboardPeriod
  month: DashboardPeriod
  low_stock_count: number
}

export interface SalesReport {
  date_from: string
  date_to: string
  revenue: string
  receipts: number
  discounts: string
  returns: string
  net_revenue: string
  cost: string
  gross_profit: string
  losses: string
  expenses: string
  net_profit: string
  payments: { cash: string; card: string }
  by_category: { name: string; quantity: number; revenue: string; cost: string; profit: string }[]
  by_cashier: { name: string | null; receipts: number; revenue: string }[]
  loss_rows: { reason: string; quantity: number; amount: string }[]
  expense_rows: { category: string; amount: string }[]
}

export interface TopProduct {
  product_id: number
  name: string
  quantity: number
  revenue: string
  cost: string
  profit: string
  variants: { sku: string; size: string | null; color: string | null; quantity: number; revenue: string }[]
}

export interface StockReportRow {
  variant_id: number
  sku: string
  barcode: string
  product: string
  category: string
  label: string
  quantity: number
  min_stock: number
  average_cost: string
  price: string
  cost_value: string
  retail_value: string
}

export interface StockReport {
  rows: StockReportRow[]
  positions: number
  units: number
  cost_value: string
  retail_value: string
  potential_profit: string
}

export interface SupplierBalance {
  supplier_id: number
  name: string
  phone: string
  purchases: string
  paid: string
  balance: string
}
