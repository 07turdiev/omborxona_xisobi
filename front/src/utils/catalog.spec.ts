import { describe, expect, it } from 'vitest'

import { colorStock, findVariant, galleryImages, initialColor, sizeOptions } from './catalog'
import type { CatalogProduct, CatalogVariant, ProductImage } from '@/types'

const BLACK = { id: 1, name: 'Qora', hex_code: '#1A1A1A' }
const WHITE = { id: 2, name: 'Oq', hex_code: '#FFFFFF' }
const S = { id: 10, name: 'S', position: 1 }
const M = { id: 11, name: 'M', position: 2 }
const L = { id: 12, name: 'L', position: 3 }

function variant(id: number, size: number, color: number, stock: number): CatalogVariant {
  return {
    id,
    size,
    size_name: null,
    color,
    color_name: null,
    barcode: `20000000000${id}`,
    price: '250000.00',
    stock_quantity: stock,
    is_active: true,
  }
}

function image(id: number, color: number | null, primary = false): ProductImage {
  return {
    id,
    color,
    thumb: `t${id}`,
    medium: `m${id}`,
    large: `l${id}`,
    is_primary: primary,
    sort_order: id,
  }
}

function product(overrides: Partial<CatalogProduct> = {}): CatalogProduct {
  return {
    id: 1,
    name: 'Ko‘ylak',
    slug: 'koylak',
    category: 1,
    category_name: 'Ko‘ylaklar',
    brand: '',
    sale_price: '250000.00',
    total_stock: 8,
    shop_stock: 3,
    warehouse_stock: 5,
    size_stock: [],
    primary_image: null,
    description: '',
    material: '',
    care: '',
    colors: [WHITE, BLACK],
    sizes: [S, M, L],
    // Qora: S 2, M 0, L 5; Oq: S 1, M 0, L 0
    variants: [
      variant(1, S.id, BLACK.id, 2),
      variant(2, M.id, BLACK.id, 0),
      variant(3, L.id, BLACK.id, 5),
      variant(4, S.id, WHITE.id, 1),
      variant(5, M.id, WHITE.id, 0),
      variant(6, L.id, WHITE.id, 0),
    ],
    image_groups: [],
    ...overrides,
  }
}

describe('sizeOptions', () => {
  it('tanlangan rang bo‘yicha qoldiq', () => {
    expect(sizeOptions(product(), WHITE.id).map((option) => option.quantity)).toEqual([1, 0, 0])
    expect(sizeOptions(product(), BLACK.id).map((option) => option.quantity)).toEqual([2, 0, 5])
  })

  it('qoldig‘i yo‘q o‘lcham ham ro‘yxatda qoladi', () => {
    expect(sizeOptions(product(), WHITE.id).map((option) => option.name)).toEqual(['S', 'M', 'L'])
  })

  it('rang tanlanmasa hamma ranglar qo‘shiladi', () => {
    expect(sizeOptions(product(), null).map((option) => option.quantity)).toEqual([3, 0, 5])
  })
})

describe('colorStock', () => {
  it('rangning hamma o‘lchamdagi qoldig‘i', () => {
    expect(colorStock(product(), BLACK.id)).toBe(7)
    expect(colorStock(product(), WHITE.id)).toBe(1)
  })
})

describe('galleryImages', () => {
  const groups = [
    { color: null, color_name: null, hex_code: null, images: [image(1, null)] },
    { color: BLACK.id, color_name: 'Qora', hex_code: '#1A1A1A', images: [image(2, BLACK.id), image(3, BLACK.id)] },
  ]

  it('rangning o‘z rasmlari, keyin umumiylari', () => {
    expect(galleryImages(groups, BLACK.id).map((item) => item.id)).toEqual([2, 3, 1])
  })

  it('rangda rasm bo‘lmasa umumiylari chiqadi', () => {
    expect(galleryImages(groups, WHITE.id).map((item) => item.id)).toEqual([1])
  })

  it('hech narsa bo‘lmasa boshqa rangning rasmi chiqadi', () => {
    const onlyBlack = [groups[1]!]

    expect(galleryImages(onlyBlack, WHITE.id).map((item) => item.id)).toEqual([2, 3])
  })

  it('rang tanlanmasa asosiy rasm birinchi', () => {
    const withPrimary = [
      { color: null, color_name: null, hex_code: null, images: [image(1, null), image(2, null, true)] },
    ]

    expect(galleryImages(withPrimary, null)[0]!.id).toBe(2)
  })
})

describe('initialColor', () => {
  it('asosiy rasmning rangi tanlanadi', () => {
    const groups = [
      { color: WHITE.id, color_name: 'Oq', hex_code: '#FFFFFF', images: [image(1, WHITE.id, true)] },
    ]

    expect(initialColor(product({ image_groups: groups }))).toBe(WHITE.id)
  })

  it('asosiy rasm bo‘lmasa qoldig‘i bor birinchi rang', () => {
    const empty = product({
      variants: [variant(1, S.id, WHITE.id, 0), variant(2, S.id, BLACK.id, 4)],
    })

    expect(initialColor(empty)).toBe(BLACK.id)
  })

  it('rangsiz mahsulotda null', () => {
    expect(initialColor(product({ colors: [] }))).toBeNull()
  })
})

describe('findVariant', () => {
  it('o‘lcham va rang tanlansa variant topiladi', () => {
    expect(findVariant(product(), L.id, BLACK.id)?.id).toBe(3)
  })

  it('tanlov to‘liq bo‘lmasa null', () => {
    expect(findVariant(product(), null, BLACK.id)).toBeNull()
  })

  it('o‘lchamsiz va rangsiz mahsulotda yagona variant', () => {
    const single = product({ colors: [], sizes: [], variants: [variant(9, 0, 0, 3)] })

    expect(findVariant(single, null, null)?.id).toBe(9)
  })
})
