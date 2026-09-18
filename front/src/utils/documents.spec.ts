import { describe, expect, it } from 'vitest'

import { documentLabel, documentLink } from './documents'

function movement(
  document_type: string,
  document_id: number | null,
  document_number: string | null = null,
  document_sale_number: string | null = null,
) {
  return { document_type, document_id, document_number, document_sale_number }
}

describe('documentLink', () => {
  it('sotuv — o‘sha chek', () => {
    expect(documentLink(movement('sale', 5, 'SOT-2026-000005'))).toBe(
      '/receipts?number=SOT-2026-000005',
    )
  })

  it('qaytarish — qaytgan chek', () => {
    expect(documentLink(movement('salereturn', 2, 'QAY-2026-000002', 'SOT-2026-000005'))).toBe(
      '/receipts?number=SOT-2026-000005',
    )
  })

  it('kirim va inventarizatsiya — id bo‘yicha ochiladi', () => {
    expect(documentLink(movement('purchase', 7, 'KIR-2026-000007'))).toBe('/purchases?open=7')
    expect(documentLink(movement('stockcount', 3, 'INV-2026-000003'))).toBe('/stock-counts?open=3')
  })

  it('hisobdan chiqarish — ro‘yxat', () => {
    expect(documentLink(movement('writeoff', 4))).toBe('/write-offs')
  })

  it('hujjatsiz yozuvda havola yo‘q', () => {
    expect(documentLink(movement('', null))).toBeNull()
    expect(documentLink(movement('sale', 5))).toBeNull()
  })
})

describe('documentLabel', () => {
  it('raqam bo‘lsa — raqam', () => {
    expect(documentLabel(movement('purchase', 7, 'KIR-2026-000007'))).toBe('KIR-2026-000007')
  })

  it('hisobdan chiqarish — turi', () => {
    expect(documentLabel(movement('writeoff', 4))).toBe('Hisobdan chiqarish')
  })
})
