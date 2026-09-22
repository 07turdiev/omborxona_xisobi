import { computed, ref, watch } from 'vue'
import { defineStore } from 'pinia'

import { addMoney, compareMoney, multiplyMoney, percentOf, subtractMoney, toCents } from '@/utils/money'
import { shopStock } from '@/utils/stock'
import { uuid } from '@/utils/uuid'
import type { Variant } from '@/types'

export interface CartLine {
  variantId: number
  sku: string
  barcode: string
  name: string
  label: string
  price: string
  quantity: number
  stock: number
  discountPercent: string
}

export type DiscountMode = 'percent' | 'amount'

const STORAGE_KEY = 'pos-cart'

interface StoredCart {
  lines: CartLine[]
  requestKey: string
  discountMode: DiscountMode
  discountValue: string
}

function readStored(): StoredCart | null {
  try {
    const raw = sessionStorage.getItem(STORAGE_KEY)
    return raw ? (JSON.parse(raw) as StoredCart) : null
  } catch {
    return null
  }
}

/**
 * Kassa savati.
 *
 * Savat `sessionStorage` da saqlanadi: sahifa tasodifan yangilansa
 * skanerlangan tovarlar yo'qolmaydi. Sotuv yakunlangach tozalanadi.
 *
 * `requestKey` — bitta savat uchun bitta kalit. «Yakunlash» ikki marta
 * bosilsa, server o'sha kalitni ko'rib ikkinchi chek yaratmaydi.
 */
export const usePosStore = defineStore('pos', () => {
  const stored = readStored()

  const lines = ref<CartLine[]>(stored?.lines ?? [])
  const requestKey = ref<string>(stored?.requestKey ?? uuid())
  const discountMode = ref<DiscountMode>(stored?.discountMode ?? 'percent')
  const discountValue = ref<string>(stored?.discountValue ?? '0')

  watch(
    [lines, requestKey, discountMode, discountValue],
    () => {
      try {
        sessionStorage.setItem(
          STORAGE_KEY,
          JSON.stringify({
            lines: lines.value,
            requestKey: requestKey.value,
            discountMode: discountMode.value,
            discountValue: discountValue.value,
          }),
        )
      } catch {
        // Saqlash yopiq bo'lsa ham kassa ishlayveradi
      }
    },
    { deep: true },
  )

  const isEmpty = computed(() => lines.value.length === 0)

  const lineTotals = computed(() =>
    lines.value.map((line) => {
      const base = multiplyMoney(line.price, line.quantity)
      const discount = percentOf(base, line.discountPercent || '0')

      return { base, discount, total: subtractMoney(base, discount) }
    }),
  )

  const subtotal = computed(() =>
    lineTotals.value.reduce((sum, item) => addMoney(sum, item.base), '0'),
  )

  const lineDiscounts = computed(() =>
    lineTotals.value.reduce((sum, item) => addMoney(sum, item.discount), '0'),
  )

  const afterLineDiscounts = computed(() => subtractMoney(subtotal.value, lineDiscounts.value))

  /** Chek chegirmasi: foiz yoki to'g'ridan-to'g'ri summa. */
  const receiptDiscount = computed(() => {
    const value = discountValue.value || '0'

    if (discountMode.value === 'percent') {
      return percentOf(afterLineDiscounts.value, value)
    }

    // Summa chek summasidan oshmaydi
    return compareMoney(value, afterLineDiscounts.value) > 0 ? afterLineDiscounts.value : value
  })

  const discountTotal = computed(() => addMoney(lineDiscounts.value, receiptDiscount.value))

  const total = computed(() => subtractMoney(subtotal.value, discountTotal.value))

  const itemCount = computed(() => lines.value.reduce((sum, line) => sum + line.quantity, 0))

  /**
   * Skanerlangan variantni qo'shadi yoki miqdorini oshiradi.
   *
   * Qoldiq **savdo zali** bo'yicha tekshiriladi: omborda turgan tovar
   * avval zalga chiqariladi (kassadagi «Ombordan olib chiqish»).
   */
  function add(variant: Variant, quantity = 1): { ok: boolean; message?: string } {
    const existing = lines.value.find((line) => line.variantId === variant.id)
    const wanted = (existing?.quantity ?? 0) + quantity
    const available = shopStock(variant)

    if (wanted > available) {
      return {
        ok: false,
        message: `${variant.product_name} — zalda ${available} dona qolgan`,
      }
    }

    if (existing) {
      existing.quantity = wanted
      existing.stock = available
    } else {
      lines.value.push({
        variantId: variant.id,
        sku: variant.sku,
        barcode: variant.barcode,
        name: variant.product_name,
        label: variant.label,
        price: variant.price,
        quantity,
        stock: available,
        discountPercent: '0',
      })
    }

    return { ok: true }
  }

  function setQuantity(variantId: number, quantity: number): { ok: boolean; message?: string } {
    const line = lines.value.find((item) => item.variantId === variantId)

    if (!line) return { ok: true }

    if (quantity <= 0) {
      remove(variantId)
      return { ok: true }
    }

    if (quantity > line.stock) {
      return { ok: false, message: `Zalda ${line.stock} dona qolgan` }
    }

    line.quantity = quantity

    return { ok: true }
  }

  function setLineDiscount(variantId: number, percent: string) {
    const line = lines.value.find((item) => item.variantId === variantId)

    if (line) line.discountPercent = percent || '0'
  }

  function remove(variantId: number) {
    lines.value = lines.value.filter((line) => line.variantId !== variantId)
  }

  /** Sotuv yakunlangach yoki bekor qilinganda. */
  function clear() {
    lines.value = []
    discountValue.value = '0'
    discountMode.value = 'percent'
    requestKey.value = uuid()

    try {
      sessionStorage.removeItem(STORAGE_KEY)
    } catch {
      // e'tiborsiz
    }
  }

  /** Chegirma kassirga ruxsat etilganidan oshmasinmi. */
  function discountExceeds(limitPercent: string): boolean {
    if (toCents(subtotal.value) === 0n) return false

    return compareMoney(discountTotal.value, percentOf(subtotal.value, limitPercent)) > 0
  }

  return {
    lines,
    requestKey,
    discountMode,
    discountValue,
    isEmpty,
    itemCount,
    lineTotals,
    subtotal,
    discountTotal,
    total,
    add,
    setQuantity,
    setLineDiscount,
    remove,
    clear,
    discountExceeds,
  }
})
