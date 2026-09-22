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

/** «Zalda 3 · omborda 12» ko'rinishidagi qator. */
export function stockLine(item: HasStocks): string {
  return `Zalda ${shopStock(item)} · omborda ${warehouseStock(item)}`
}
