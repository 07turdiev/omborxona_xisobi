/**
 * Lokal chop etish agenti bilan aloqa (`agent/` papkasi).
 *
 * Agent ishlab tursa, chek va yorliq to'g'ridan-to'g'ri printerga ketadi:
 * brauzer oynasi ochilmaydi, qog'oz bo'sh ketmaydi va shtrix-kodni
 * printerning o'zi chizadi. Agent bo'lmasa — ilova jimgina brauzer
 * orqali chop etishga qaytadi, ya'ni agent majburiy emas.
 */

import { formatSum, isZero } from '@/utils/money'
import type { Sale, ShopSettings } from '@/types'

/** Agent faqat shu kompyuterda tinglaydi */
const BASE = 'http://127.0.0.1:7777'

/** Agent o'chirilgan bo'lsa kassa kutib qolmasligi kerak */
const PROBE_TIMEOUT = 300
const PRINT_TIMEOUT = 5000

/**
 * Bitta kompyuterli o'rnatmada token kerak emas: agent allaqachon faqat
 * ilovaning manzilidan kelgan so'rovni qabul qiladi. Kerak bo'lsa
 * `front/.env.local` ga `VITE_AGENT_TOKEN=...` yoziladi.
 */
const TOKEN = import.meta.env.VITE_AGENT_TOKEN ?? ''

export interface AgentError {
  at: string
  message: string
}

export interface AgentPrinter {
  name: string
  transport: string
  target: string | null
  responds: boolean
  lastError: AgentError | null
}

export interface AgentHealth {
  version: string
  codePage: string
  printers: AgentPrinter[]
}

export interface ReceiptLinePayload {
  name: string
  variant: string
  quantity: number
  unitPrice: string
  lineTotal: string
}

export interface ReceiptPayload {
  shopName: string
  number: string
  dateTime: string
  cashier: string
  lines: ReceiptLinePayload[]
  discount: string
  total: string
  payments: { cash: string; card: string }
  barcode: string
  footer: string
  openDrawer?: boolean
}

/** Yorliqqa chiqadigan tovar — ro'yxatlar shu shaklda beradi */
export interface LabelItem {
  barcode: string
  name: string
  label: string
  price: string
  quantity: number
}

export interface LabelPayload {
  shopName: string
  name: string
  variant: string
  price: string
  barcode: string
  quantity: number
}

export interface LabelJob {
  widthMm: number
  heightMm: number
  labels: LabelPayload[]
}

async function request<T>(path: string, init: RequestInit, timeout: number): Promise<T> {
  const headers: Record<string, string> = {}

  // `Content-Type` faqat ma'lumot yuborilganda qo'yiladi: uni GET ga ham
  // qo'shsak, brauzer har safar oldindan OPTIONS so'rovini yuboradi va
  // 300 ms lik tekshiruv shunga ketib qolishi mumkin.
  if (init.body) headers['Content-Type'] = 'application/json'

  if (TOKEN) headers['X-Agent-Token'] = TOKEN

  const response = await fetch(`${BASE}${path}`, {
    ...init,
    headers,
    signal: AbortSignal.timeout(timeout),
  })

  if (!response.ok) {
    const body = (await response.json().catch(() => ({}))) as { error?: string }

    throw new Error(body.error ?? `agent javobi: ${response.status}`)
  }

  return (await response.json()) as T
}

/** Agent ishlayaptimi. Ishlamasa `null` — bu oddiy holat, xato emas. */
export async function health(): Promise<AgentHealth | null> {
  try {
    return await request<AgentHealth>('/health', { method: 'GET' }, PROBE_TIMEOUT)
  } catch {
    return null
  }
}

export async function sendReceipt(receipt: ReceiptPayload): Promise<void> {
  await request('/receipt', { method: 'POST', body: JSON.stringify(receipt) }, PRINT_TIMEOUT)
}

export async function sendLabels(job: LabelJob): Promise<void> {
  await request('/labels', { method: 'POST', body: JSON.stringify(job) }, PRINT_TIMEOUT)
}

/**
 * Sana: `18.09.2026 14:35`.
 *
 * `toLocaleString` ishlatilmaydi — natija brauzer tiliga qarab
 * o'zgaradi, chekda esa format doim bir xil bo'lishi kerak.
 */
function formatDateTime(iso: string): string {
  const date = new Date(iso)
  const pad = (value: number) => String(value).padStart(2, '0')

  return (
    `${pad(date.getDate())}.${pad(date.getMonth() + 1)}.${date.getFullYear()} ` +
    `${pad(date.getHours())}:${pad(date.getMinutes())}`
  )
}

/** Sotuvdan agent tushunadigan chek yasaydi. */
export function receiptPayload(sale: Sale, shopName: string): ReceiptPayload {
  const payload: ReceiptPayload = {
    shopName,
    number: sale.number,
    dateTime: formatDateTime(sale.created_at),
    cashier: sale.cashier_name ?? '',
    lines: sale.lines.map((line) => ({
      name: line.product_name,
      variant: line.variant_label,
      quantity: line.quantity,
      unitPrice: line.unit_price,
      lineTotal: line.line_total,
    })),
    discount: sale.discount_total,
    total: sale.total,
    payments: { cash: sale.cash_amount, card: sale.card_amount },
    // Faqat raqam: skaner klaviatura tiliga qarab harflarni boshqacha
    // yozib yuboradi (izoh: ReceiptPrint.vue)
    barcode: sale.number.replace(/\D/g, ''),
    footer: 'Qaytarish uchun shu chekni saqlang',
  }

  // Pul qutisi naqd to'lovda ochiladi. Boshqa holatda kalit umuman
  // yuborilmaydi — qutini ochish-ochmaslikni agent sozlamasi hal qiladi.
  if (!isZero(sale.cash_amount)) payload.openDrawer = true

  return payload
}

/** Ro'yxatdagi tovarlardan agent tushunadigan yorliq ishini yasaydi. */
export function labelJob(items: LabelItem[], shop: ShopSettings | null): LabelJob {
  return {
    widthMm: shop?.label_width_mm ?? 40,
    heightMm: shop?.label_height_mm ?? 30,
    labels: items
      .filter((item) => item.barcode)
      .map((item) => ({
        shopName: shop?.shop_name ?? '',
        name: item.name,
        variant: item.label,
        price: formatSum(item.price),
        barcode: item.barcode,
        quantity: Math.max(1, Math.trunc(item.quantity) || 1),
      })),
  }
}
