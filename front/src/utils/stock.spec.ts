import { describe, expect, it } from 'vitest'

import { shopStock, stockLine, stockOfKind, warehouseCell, warehouseStock } from './stock'
import type { StockAtLocation } from '@/types'

function at(kind: 'shop' | 'warehouse', quantity: number, cell = ''): StockAtLocation {
  return {
    location: kind === 'shop' ? 2 : 1,
    location_name: kind === 'shop' ? 'Do‘kon' : 'Ombor',
    kind,
    quantity,
    cell,
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

describe('warehouseCell', () => {
  it('ombordagi katakni beradi', () => {
    expect(warehouseCell({ stocks: [at('warehouse', 4, 'B2'), at('shop', 1)] })).toBe('B2')
  })

  it('joy belgilanmagan bo‘lsa bo‘sh', () => {
    expect(warehouseCell({ stocks: [at('warehouse', 4)] })).toBe('')
  })
})

describe('stockLine katak bilan', () => {
  it('omborda tovar bo‘lsa katak ham ko‘rinadi', () => {
    expect(stockLine({ stocks: [at('warehouse', 12, 'B2'), at('shop', 3)] })).toBe(
      'Zalda 3 · omborda 12 · B2',
    )
  })

  it('omborda tovar qolmagan bo‘lsa katak aytilmaydi', () => {
    // Joy eslab qolinadi, lekin bo‘sh katakni ko‘rsatish chalg‘itadi
    expect(stockLine({ stocks: [at('warehouse', 0, 'B2'), at('shop', 3)] })).toBe(
      'Zalda 3 · omborda 0',
    )
  })
})
