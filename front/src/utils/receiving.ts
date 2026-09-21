/**
 * Kirim ekranining holati: model bo'yicha o'lcham × rang katakchasi.
 *
 * Do'konga tovar shtrix-kodsiz keladi va bitta model 10-20 variant bo'ladi.
 * Shuning uchun kirim qatorlari bittalab emas, model bo'yicha kiritiladi:
 * katakchaga dona yoziladi, tannarx esa modelga bitta. Serverga esa
 * baribir oddiy qatorlar ketadi — hujjat tuzilishi o'zgarmagan.
 */

import { addMoney, multiplyMoney, normalizeMoneyInput } from '@/utils/money'
import type { Product, PurchaseLine, Variant } from '@/types'

export interface DraftModel {
  product: number
  name: string
  brand: string
  /** Do'kondagi hozirgi sotuv narxi */
  currentPrice: string
  /** Model uchun bitta tannarx */
  cost: string
  /** Ustama foizi — sotuv narxini taklif qilish uchun */
  markup: string
  /** Yangi sotuv narxi: tasdiqlanganda mahsulotga yoziladi */
  newPrice: string
  variants: Variant[]
  /** variant → nechta dona keldi */
  quantities: Record<number, number>
  /** variant → shu qatorning alohida tannarxi (bo'sh bo'lsa modelniki) */
  overrides: Record<number, string>
}

export interface GridAxis {
  id: number | null
  name: string
}

/**
 * Holatning nusxasi.
 *
 * Katakcha ota komponentning obyektini bevosita o'zgartirmaydi: "Bekor
 * qilish" bosilganda ro'yxatdagi model o'zgarmagan bo'lib qolishi kerak.
 * Vue obyektlari proksi bo'lgani uchun JSON orqali ko'chiriladi —
 * ma'lumot faqat son va satrdan iborat.
 */
export function cloneModel(model: DraftModel): DraftModel {
  return JSON.parse(JSON.stringify(model)) as DraftModel
}

export function emptyModel(product: Product): DraftModel {
  return {
    product: product.id,
    name: product.name,
    brand: product.brand,
    currentPrice: product.sale_price,
    cost: '',
    markup: '',
    newPrice: '',
    variants: product.variants.filter((variant) => variant.is_active),
    quantities: {},
    overrides: {},
  }
}

/**
 * Qoralamani qayta ochish: saqlangan qatorlardan modelni tiklaydi.
 *
 * Tannarx hamma qatorda bir xil bo'lsa — u modelniki, aks holda har
 * qator o'zining alohida qiymatini oladi (eng ko'p uchraydigani model
 * tannarxi bo'lib qoladi).
 */
export function modelFromLines(product: Product, lines: PurchaseLine[]): DraftModel {
  const model = emptyModel(product)

  if (!lines.length) return model

  const counts = new Map<string, number>()

  for (const line of lines) {
    model.quantities[line.variant] = line.quantity
    counts.set(line.unit_cost, (counts.get(line.unit_cost) ?? 0) + 1)
  }

  const [common] = [...counts].sort((a, b) => b[1] - a[1])

  model.cost = common?.[0] ?? ''

  for (const line of lines) {
    if (line.unit_cost !== model.cost) model.overrides[line.variant] = line.unit_cost
  }

  // Narx modelga tegishli — qatorlarda bir xil yozilgan bo'ladi
  model.newPrice = lines.find((line) => line.new_sale_price)?.new_sale_price ?? ''

  return model
}

/** Shu qator uchun amaldagi tannarx: alohidasi bo'lmasa — modelniki. */
export function lineCost(model: DraftModel, variant: number): string {
  const override = (model.overrides[variant] ?? '').trim()

  return normalizeMoneyInput(override || model.cost || '0')
}

export function modelUnits(model: DraftModel): number {
  return Object.values(model.quantities).reduce((sum, quantity) => sum + (quantity || 0), 0)
}

export function modelTotal(model: DraftModel): string {
  let total = '0'

  for (const [variant, quantity] of Object.entries(model.quantities)) {
    if (!quantity) continue

    total = addMoney(total, multiplyMoney(lineCost(model, Number(variant)), quantity))
  }

  return total
}

/** Serverga ketadigan qator */
export interface DraftLine {
  variant: number
  quantity: number
  unit_cost: string
  new_sale_price: string | null
}

/** Modellardan hujjat qatorlari: bo'sh katakchalar tushib qoladi. */
export function draftLines(models: DraftModel[]): DraftLine[] {
  const lines: DraftLine[] = []

  for (const model of models) {
    const newPrice = model.newPrice.trim() ? normalizeMoneyInput(model.newPrice) : null

    for (const variant of model.variants) {
      const quantity = model.quantities[variant.id] ?? 0

      if (quantity <= 0) continue

      lines.push({
        variant: variant.id,
        quantity,
        unit_cost: lineCost(model, variant.id),
        new_sale_price: newPrice,
      })
    }
  }

  return lines
}

export function draftUnits(models: DraftModel[]): number {
  return models.reduce((sum, model) => sum + modelUnits(model), 0)
}

export function draftTotal(models: DraftModel[]): string {
  return models.reduce((sum, model) => addMoney(sum, modelTotal(model)), '0')
}

// --- Katakcha o'qlari -------------------------------------------------------

function axis(variants: Variant[], key: 'size' | 'color'): GridAxis[] {
  const seen = new Map<number | null, string>()

  for (const variant of variants) {
    const id = variant[key]

    if (!seen.has(id)) seen.set(id, (key === 'size' ? variant.size_name : variant.color_name) ?? '—')
  }

  return [...seen].map(([id, name]) => ({ id, name }))
}

export function gridSizes(variants: Variant[]): GridAxis[] {
  return axis(variants, 'size')
}

export function gridColors(variants: Variant[]): GridAxis[] {
  return axis(variants, 'color')
}

export function gridCell(
  variants: Variant[],
  size: number | null,
  color: number | null,
): Variant | undefined {
  return variants.find((variant) => variant.size === size && variant.color === color)
}
