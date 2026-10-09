/**
 * Joy bo'yicha qoldiq.
 *
 * Do'konda tovar ikki joyda turadi: omborda va savdo zalida. Sotuv
 * faqat zaldagi qoldiqdan bo'ladi; zalda tugagan tovar ombordan olib
 * chiqiladi. Shu sababli ekranlar «umumiy qoldiq» emas, aynan qaysi
 * joyda nechta borligini ko'rsatadi.
 */

import type { LocationKind, StockAtLocation } from '@/types'

interface HasStocks {
  stocks?: StockAtLocation[]
  stock_quantity?: number
}

/** Shu turdagi joylardagi qoldiq yig'indisi. */
export function stockOfKind(item: HasStocks, kind: LocationKind): number {
  return (item.stocks ?? [])
    .filter((stock) => stock.kind === kind)
    .reduce((sum, stock) => sum + stock.quantity, 0)
}

/** Savdo zalidagi qoldiq — kassada sotiladigani shu. */
export function shopStock(item: HasStocks): number {
  return stockOfKind(item, 'shop')
}

/** Ombordagi qoldiq — zalga chiqarish uchun zaxira. */
export function warehouseStock(item: HasStocks): number {
  return stockOfKind(item, 'warehouse')
}

/**
 * Ombordagi shkafning katagi: `B2`. Belgilanmagan bo'lsa bo'sh satr.
 *
 * Zalda katak bo'lmaydi — u yerda tovar javonda turadi.
 */
export function warehouseCell(item: HasStocks): string {
  return (item.stocks ?? []).find((stock) => stock.kind === 'warehouse')?.cell ?? ''
}

/**
 * «Zalda 3 · omborda 12 · B2» ko'rinishidagi qator.
 *
 * Katak faqat omborda tovar turganda qo'shiladi: qoldig'i yo'q
 * tovarning joyini aytish chalg'itadi.
 */
export function stockLine(item: HasStocks): string {
  const parts = [`Zalda ${shopStock(item)}`, `omborda ${warehouseStock(item)}`]
  const cell = warehouseCell(item)

  if (cell && warehouseStock(item) > 0) parts.push(cell)

  return parts.join(' · ')
}
