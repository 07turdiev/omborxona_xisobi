import { describe, expect, it } from 'vitest'

import {
  draftLines,
  groupCell,
  groupLines,
  draftTotal,
  draftUnits,
  emptyModel,
  gridCell,
  gridColors,
  gridSizes,
  modelFromLines,
  modelTotal,
  modelUnits,
  orderAxis,
} from './receiving'
import type { Product, PurchaseLine, Variant } from '@/types'

/** O'lcham × rang: S/M × Oq/Qora — jami to'rt variant */
function variant(id: number, size: number, sizeName: string, color: number, colorName: string): Variant {
  return {
    id,
    product: 1,
    product_name: 'Bahorgi kurtka',
    size,
    size_name: sizeName,
    color,
    color_name: colorName,
    label: `${sizeName} / ${colorName}`,
    sku: `P0001-0${id}`,
    barcode: `200000000000${id}`,
    sale_price: null,
    price: '400000.00',
    stock_quantity: 0,
    min_stock: 0,
    is_active: true,
  }
}

const OQ_S = variant(1, 10, 'S', 20, 'Oq')
const OQ_M = variant(2, 11, 'M', 20, 'Oq')
const QORA_S = variant(3, 10, 'S', 21, 'Qora')
const QORA_M = variant(4, 11, 'M', 21, 'Qora')

function product(): Product {
  return {
    id: 1,
    category: 1,
    category_name: 'Kurtkalar',
    name: 'Bahorgi kurtka',
    slug: 'bahorgi-kurtka',
    brand: 'Madlen',
    description: '',
    material: '',
    care: '',
    sale_price: '400000.00',
    mxik_code: '',
    package_code: '',
    effective_mxik_code: '',
    is_active: true,
    images: [],
    variants: [OQ_S, OQ_M, QORA_S, QORA_M],
  }
}

function line(variantId: number, quantity: number, cost: string, price?: string): PurchaseLine {
  return {
    id: variantId,
    variant: variantId,
    product: 1,
    quantity,
    unit_cost: cost,
    new_sale_price: price ?? null,
  }
}

describe('katakcha o‘qlari', () => {
  it('ustun — o‘lcham, qator — rang', () => {
    const variants = product().variants

    expect(gridSizes(variants).map((size) => size.name)).toEqual(['S', 'M'])
    expect(gridColors(variants).map((color) => color.name)).toEqual(['Oq', 'Qora'])
    expect(gridCell(variants, 11, 21)?.id).toBe(QORA_M.id)
    expect(gridCell(variants, 99, 21)).toBeUndefined()
  })
})

describe('o‘qlarni tartiblash', () => {
  const shopSizes = [{ id: 10 }, { id: 11 }, { id: 12 }]

  it('do‘kondagi tartibda turadi', () => {
    const axis = [
      { id: 12, name: 'L' },
      { id: 10, name: 'S' },
      { id: 11, name: 'M' },
    ]

    expect(orderAxis(axis, shopSizes).map((item) => item.name)).toEqual(['S', 'M', 'L'])
  })

  it('ro‘yxatda yo‘q o‘q oxirida qoladi', () => {
    const axis = [
      { id: 99, name: 'Maxsus' },
      { id: 10, name: 'S' },
    ]

    expect(orderAxis(axis, shopSizes).map((item) => item.name)).toEqual(['S', 'Maxsus'])
  })

  it('o‘lchamsiz (bo‘sh) ustun birinchi', () => {
    const axis = [
      { id: 10, name: 'S' },
      { id: null, name: '—' },
    ]

    expect(orderAxis(axis, shopSizes).map((item) => item.name)).toEqual(['—', 'S'])
  })
})

describe('kirim qatorlari', () => {
  it('bitta tannarx hamma qatorga tushadi', () => {
    const model = emptyModel(product())

    model.cost = '200000'
    model.quantities = { [OQ_S.id]: 3, [QORA_M.id]: 2 }

    expect(draftLines([model])).toEqual([
      { variant: OQ_S.id, quantity: 3, unit_cost: '200000.00', new_sale_price: null },
      { variant: QORA_M.id, quantity: 2, unit_cost: '200000.00', new_sale_price: null },
    ])

    expect(modelUnits(model)).toBe(5)
    expect(modelTotal(model)).toBe('1000000.00')
  })

  it('qatorning alohida tannarxi modelnikidan ustun', () => {
    const model = emptyModel(product())

    model.cost = '200000'
    model.quantities = { [OQ_S.id]: 1, [QORA_M.id]: 1 }
    model.overrides = { [QORA_M.id]: '250000' }

    const costs = draftLines([model]).map((item) => item.unit_cost)

    expect(costs).toEqual(['200000.00', '250000.00'])
    expect(modelTotal(model)).toBe('450000.00')
  })

  it('bo‘sh katakcha qator bo‘lmaydi', () => {
    const model = emptyModel(product())

    model.cost = '100000'
    model.quantities = { [OQ_S.id]: 2, [OQ_M.id]: 0 }

    expect(draftLines([model])).toHaveLength(1)
  })

  it('yangi sotuv narxi modelning hamma qatoriga yoziladi', () => {
    const model = emptyModel(product())

    model.cost = '200000'
    model.newPrice = '320000'
    model.quantities = { [OQ_S.id]: 1, [OQ_M.id]: 1 }

    expect(draftLines([model]).map((item) => item.new_sale_price)).toEqual([
      '320000.00',
      '320000.00',
    ])
  })

  it('bir necha modelning jami', () => {
    const first = emptyModel(product())
    const second = emptyModel({ ...product(), id: 2 })

    first.cost = '100000'
    first.quantities = { [OQ_S.id]: 2 }

    second.cost = '50000'
    second.quantities = { [QORA_S.id]: 3 }

    expect(draftUnits([first, second])).toBe(5)
    expect(draftTotal([first, second])).toBe('350000.00')
  })
})

describe('qoralamani qayta ochish', () => {
  it('qatorlardan katakcha va umumiy tannarx tiklanadi', () => {
    const model = modelFromLines(product(), [
      line(OQ_S.id, 3, '200000.00'),
      line(OQ_M.id, 2, '200000.00'),
      line(QORA_M.id, 1, '250000.00'),
    ])

    expect(model.quantities).toEqual({ [OQ_S.id]: 3, [OQ_M.id]: 2, [QORA_M.id]: 1 })

    // Ko'pchilik qatordagi narx — modelniki, farq qilgani alohida qoladi
    expect(model.cost).toBe('200000.00')
    expect(model.overrides).toEqual({ [QORA_M.id]: '250000.00' })
    expect(modelUnits(model)).toBe(6)
  })

  it('yangi sotuv narxi ham tiklanadi', () => {
    const model = modelFromLines(product(), [line(OQ_S.id, 1, '200000.00', '320000.00')])

    expect(model.newPrice).toBe('320000.00')
  })

  it('qatorsiz model bo‘sh ochiladi', () => {
    const model = modelFromLines(product(), [])

    expect(model.quantities).toEqual({})
    expect(model.cost).toBe('')
  })
})


describe('ochilgan hujjat: qatorlar model bo‘yicha', () => {
  const lines: PurchaseLine[] = [
    {
      ...line(OQ_S.id, 3, '200000.00'),
      product_name: 'Bahorgi kurtka',
      size: 10,
      size_name: 'S',
      color: 20,
      color_name: 'Oq',
    },
    {
      ...line(QORA_M.id, 2, '200000.00'),
      product_name: 'Bahorgi kurtka',
      size: 11,
      size_name: 'M',
      color: 21,
      color_name: 'Qora',
    },
    {
      ...line(99, 1, '50000.00'),
      product: 2,
      product_name: 'Sharf',
      size: null,
      size_name: null,
      color: null,
      color_name: null,
    },
  ]

  it('har model o‘z o‘qlari va yig‘indisi bilan chiqadi', () => {
    const [kurtka, sharf] = groupLines(lines)

    expect(kurtka!.name).toBe('Bahorgi kurtka')
    expect(kurtka!.units).toBe(5)
    expect(kurtka!.total).toBe('1000000.00')
    expect(kurtka!.cost).toBe('200000.00')
    expect(kurtka!.sizes.map((size) => size.name)).toEqual(['S', 'M'])
    expect(kurtka!.colors.map((color) => color.name)).toEqual(['Oq', 'Qora'])

    expect(sharf!.name).toBe('Sharf')
    expect(sharf!.units).toBe(1)
  })

  it('katak topiladi, kelmagani bo‘sh qoladi', () => {
    const [kurtka] = groupLines(lines)

    expect(groupCell(kurtka!, 10, 20)?.quantity).toBe(3)
    expect(groupCell(kurtka!, 11, 20)).toBeUndefined()
  })

  it('tannarx har xil bo‘lsa, umumiysi ko‘rsatilmaydi', () => {
    const mixed = groupLines([
      { ...lines[0]! },
      { ...lines[1]!, unit_cost: '250000.00' },
    ])

    expect(mixed[0]!.cost).toBe('')
  })
})
