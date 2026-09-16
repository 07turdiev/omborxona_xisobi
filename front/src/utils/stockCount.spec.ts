import { describe, expect, it } from 'vitest'

import { differingLines, findScanned, uncountedLines, type CountLine } from './stockCount'

function line(partial: Partial<CountLine> & { variant: number; barcode: string }): CountLine {
  return {
    product_name: 'Ko‘ylak',
    variant_label: 'M / Oq',
    expected_quantity: 5,
    counted_quantity: 0,
    ...partial,
  }
}

const lines: CountLine[] = [
  line({ variant: 1, barcode: '2000000000121' }),
  line({ variant: 2, barcode: '2000000000138', counted_quantity: 5 }),
]

describe('findScanned', () => {
  it('kod bo‘yicha qatorni topadi', () => {
    const result = findScanned(lines, '2000000000138')

    expect(result).toEqual({ ok: true, index: 1 })
  })

  it('bo‘sh joylarni tashlaydi', () => {
    expect(findScanned(lines, '  2000000000121  ')).toEqual({ ok: true, index: 0 })
  })

  it('noma’lum kodda xato qaytaradi', () => {
    const result = findScanned(lines, '2000000009999')

    expect(result.ok).toBe(false)

    if (!result.ok) {
      expect(result.message).toContain('2000000009999')
    }
  })

  it('bo‘sh kodni rad etadi', () => {
    expect(findScanned(lines, '   ').ok).toBe(false)
  })
})

describe('sanoq holati', () => {
  it('sanalmagan qatorlarni sanaydi', () => {
    expect(uncountedLines(lines)).toBe(1)
  })

  it('farqli qatorlarni sanaydi', () => {
    // Birinchisi 0 sanalgan (5 kutilgan), ikkinchisi to'g'ri
    expect(differingLines(lines)).toBe(1)
  })

  it('hammasi sanalganda farq qolmaydi', () => {
    const counted = lines.map((item) => ({ ...item, counted_quantity: 5 }))

    expect(uncountedLines(counted)).toBe(0)
    expect(differingLines(counted)).toBe(0)
  })
})
