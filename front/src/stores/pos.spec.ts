import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it } from 'vitest'

import { usePosStore } from './pos'
import type { Variant } from '@/types'

/** Zalda 10 dona turgan 100 000 so'mlik tovar */
function variant(promotion: Variant['promotion'] = null): Variant {
  return {
    id: 1,
    product: 1,
    product_name: 'Kurtka',
    size: null,
    size_name: null,
    color: null,
    color_name: null,
    label: '',
    sku: 'K-1',
    barcode: '2000000000015',
    sale_price: null,
    price: '100000.00',
    promotion,
    stock_quantity: 10,
    stocks: [{ location: 1, location_name: 'Zal', kind: 'shop', quantity: 10, cell: '' }],
    min_stock: 0,
    is_active: true,
  }
}

const PROMO = {
  id: 7,
  name: 'Kuzgi aksiya',
  percent: '30.00',
  ends_on: '2026-10-20',
  price: '70000.00',
}

describe('kassa savati — aksiya', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('aksiya narxi o‘zi qo‘llanadi', () => {
    const pos = usePosStore()

    pos.add(variant(PROMO), 2)

    expect(pos.subtotal).toBe('200000.00')
    expect(pos.promoTotal).toBe('60000.00')
    expect(pos.total).toBe('140000.00')
  })

  it('kassir chegirmasi aksiyaga qo‘shiladi — ikkalasi ham qator summasidan', () => {
    const pos = usePosStore()

    pos.add(variant(PROMO), 2)
    pos.setLineDiscount(1, '5')

    // 30 % + 5 % = 70 000 — server ham shunday hisoblaydi
    expect(pos.discountTotal).toBe('70000.00')
    expect(pos.total).toBe('130000.00')
  })

  it('kassir chegarasiga aksiya kirmaydi', () => {
    const pos = usePosStore()

    pos.add(variant(PROMO), 2)

    // Aksiya 30 %, chegara 10 % — kassir hali hech narsa bermagan
    expect(pos.discountExceeds('10')).toBe(false)

    pos.setLineDiscount(1, '15')

    expect(pos.discountExceeds('10')).toBe(true)
  })

  it('aksiyasiz tovar avvalgidek', () => {
    const pos = usePosStore()

    pos.add(variant(), 1)

    expect(pos.promoTotal).toBe('0.00')
    expect(pos.total).toBe('100000.00')
  })
})
