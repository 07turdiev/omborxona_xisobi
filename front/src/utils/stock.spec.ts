import { describe, expect, it } from 'vitest'

import { shopStock, stockLine, stockOfKind, warehouseStock } from './stock'
import type { StockAtLocation } from '@/types'

function at(kind: 'shop' | 'warehouse', quantity: number): StockAtLocation {
  return {
    location: kind === 'shop' ? 2 : 1,
    location_name: kind === 'shop' ? 'Do‘kon' : 'Ombor',
    kind,
    quantity,
  }
}

const dress = { stocks: [at('warehouse', 12), at('shop', 3)], stock_quantity: 15 }

describe('stockOfKind', () => {
  it('turdagi joylarning qoldig‘ini qo‘shadi', () => {
    expect(stockOfKind(dress, 'shop')).toBe(3)
    expect(stockOfKind(dress, 'warehouse')).toBe(12)
  })

  it('joy yo‘q bo‘lsa nol beradi', () => {
    expect(stockOfKind({ stocks: [at('warehouse', 4)] }, 'shop')).toBe(0)
  })

  it('eski javobda qoldiq umuman bo‘lmasligi mumkin', () => {
    expect(stockOfKind({ stock_quantity: 9 }, 'shop')).toBe(0)
  })
})

describe('shopStock va warehouseStock', () => {
  it('sotiladigani zaldagi qoldiq', () => {
    expect(shopStock(dress)).toBe(3)
    expect(warehouseStock(dress)).toBe(12)
  })
})

describe('stockLine', () => {
  it('ikkala joyni bitta qatorda ko‘rsatadi', () => {
    expect(stockLine(dress)).toBe('Zalda 3 · omborda 12')
  })

  it('bo‘sh qoldiq ham yoziladi — «yo‘q» ekani ko‘rinib tursin', () => {
    expect(stockLine({ stocks: [] })).toBe('Zalda 0 · omborda 0')
  })
})
