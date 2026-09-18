/**
 * Ombor jurnalidagi yozuvdan uni yaratgan hujjatga havola.
 *
 * Jurnal hujjatni turi (`purchase`, `sale`, …) va id si bilan saqlaydi;
 * raqamini server qo'shib beradi. Har tur o'z sahifasida ochiladi.
 */

import type { StockMovement } from '@/types'

type Movement = Pick<
  StockMovement,
  'document_type' | 'document_id' | 'document_number' | 'document_sale_number'
>

/** Hujjat sahifasi. Ochib bo'lmaydigan yozuvda `null`. */
export function documentLink(movement: Movement): string | null {
  const { document_type: type, document_id: id } = movement

  switch (type) {
    case 'sale':
      return movement.document_number
        ? `/receipts?number=${encodeURIComponent(movement.document_number)}`
        : null

    // Qaytarish o'z chekida ko'rinadi: qaysi chekdan qaytgani
    case 'salereturn':
      return movement.document_sale_number
        ? `/receipts?number=${encodeURIComponent(movement.document_sale_number)}`
        : null

    case 'purchase':
      return id ? `/purchases?open=${id}` : null

    case 'stockcount':
      return id ? `/stock-counts?open=${id}` : null

    // Hisobdan chiqarishning raqami yo'q — ro'yxatga olib boradi
    case 'writeoff':
      return '/write-offs'

    default:
      return null
  }
}

/** Havola matni: hujjat raqami, raqami yo'q bo'lsa — turi. */
export function documentLabel(movement: Movement): string {
  if (movement.document_number) return movement.document_number

  return movement.document_type === 'writeoff' ? 'Hisobdan chiqarish' : '—'
}
