import { afterEach, describe, expect, it, vi } from 'vitest'

import {
  health,
  labelJob,
  receiptPayload,
  sendReceipt,
  sendShelfLabels,
  SHELF_TEXT_MM,
  shelfLabelJob,
} from './agent'
import type { Sale, ShopSettings } from '@/types'

const SALE = {
  id: 1,
  number: 'SOT-2026-000123',
  created_at: '2026-09-18T14:35:00',
  cashier: 2,
  cashier_name: 'kassir',
  subtotal: '500000.00',
  discount_total: '50000.00',
  total: '450000.00',
  cash_amount: '450000.00',
  card_amount: '0.00',
  status: 'completed',
  status_display: 'Yakunlangan',
  voided_at: null,
  fiscal_receipt_id: '',
  fiscal_qr_url: '',
  lines: [
    {
      id: 10,
      variant: 5,
      product_name: 'Yozgi ko‘ylak',
      variant_label: 'M / Oq',
      sku: 'KOY-M-OQ',
      barcode: '2000000000015',
      quantity: 2,
      unit_price: '250000.00',
      discount_amount: '50000.00',
      line_total: '450000.00',
      returned_quantity: 0,
    },
  ],
} as Sale

const SHOP = {
  shop_name: 'Madlen sen',
  label_width_mm: 40,
  label_height_mm: 30,
  receipt_width_mm: 80,
  receipt_page_height_mm: 110,
  max_discount_percent: '10',
} as ShopSettings

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('receiptPayload', () => {
  it('sotuv qatorlarini chek qatorlariga o‘giradi', () => {
    const payload = receiptPayload(SALE, 'Madlen sen')

    expect(payload.shopName).toBe('Madlen sen')
    expect(payload.number).toBe('SOT-2026-000123')
    expect(payload.total).toBe('450000.00')
    expect(payload.discount).toBe('50000.00')
    expect(payload.payments).toEqual({ cash: '450000.00', card: '0.00' })

    expect(payload.lines).toEqual([
      {
        name: 'Yozgi ko‘ylak',
        variant: 'M / Oq',
        quantity: 2,
        unitPrice: '250000.00',
        lineTotal: '450000.00',
      },
    ])
  })

  it('shtrix-kod faqat raqamdan iborat', () => {
    // Harflar skaner klaviatura tiliga qarab buzilib o'qiladi
    expect(receiptPayload(SALE, '').barcode).toBe('2026000123')
  })

  it('sana brauzer tiliga bog‘liq emas', () => {
    expect(receiptPayload(SALE, '').dateTime).toBe('18.09.2026 14:35')
  })

  it('logotip bo‘lsa — agent tushunadigan shaklda qo‘shiladi', () => {
    const logo = { width: 16, height: 2, raster: '//////8=', png: 'data:image/png;base64,' }

    expect(receiptPayload(SALE, 'Madlen sen', logo).logo).toEqual({
      width: 16,
      height: 2,
      data: '//////8=',
    })
  })

  it('logotip bo‘lmasa kalit umuman yuborilmaydi — chekda nom chiqadi', () => {
    expect('logo' in receiptPayload(SALE, 'Madlen sen', null)).toBe(false)
    expect('logo' in receiptPayload(SALE, 'Madlen sen')).toBe(false)
  })

  it('aksiyadagi qator ostida izoh chiqadi', () => {
    const sale = {
      ...SALE,
      lines: [{ ...SALE.lines[0]!, promotion: 3, promotion_percent: '30.00' }],
    } as Sale

    expect(receiptPayload(sale, '').lines[0]?.promo).toBe('Aksiya -30%')
    expect(receiptPayload(SALE, '').lines[0]?.promo).toBeUndefined()
  })

  it('pul qutisi faqat naqd to‘lovda ochiladi', () => {
    expect(receiptPayload(SALE, '').openDrawer).toBe(true)

    const byCard = { ...SALE, cash_amount: '0.00', card_amount: '450000.00' } as Sale

    expect(receiptPayload(byCard, '').openDrawer).toBeUndefined()
  })
})

describe('labelJob', () => {
  const items = [
    { barcode: '2000000000015', name: 'Ko‘ylak', label: 'M / Oq', price: '250000.00', quantity: 3 },
  ]

  it('o‘lchamni do‘kon sozlamasidan oladi', () => {
    const job = labelJob(items, SHOP)

    expect(job.widthMm).toBe(40)
    expect(job.heightMm).toBe(30)
    expect(job.labels[0]?.shopName).toBe('Madlen sen')
  })

  it('sozlama yo‘q bo‘lsa 40×30 mm', () => {
    const job = labelJob(items, null)

    expect(job.widthMm).toBe(40)
    expect(job.heightMm).toBe(30)
  })

  it('narxni o‘qiladigan ko‘rinishga keltiradi', () => {
    // Minglar uzilmaydigan probel bilan ajratiladi (son qatorga
    // bo'linmasligi uchun) — solishtirishdan oldin oddiy probelga o'giramiz
    const price = labelJob(items, SHOP).labels[0]?.price.replace(/\s/g, ' ')

    expect(price).toBe("250 000 so'm")
  })

  it('shtrix-kodsiz tovar yorliqqa tushmaydi', () => {
    const mixed = [...items, { ...items[0]!, barcode: '' }]

    expect(labelJob(mixed, SHOP).labels).toHaveLength(1)
  })

  it('aksiyada eski narx chizish uchun alohida yuboriladi', () => {
    const promo = [{ ...items[0]!, price: '175000.00', oldPrice: '250000.00' }]
    const label = labelJob(promo, SHOP).labels[0]!

    expect(label.price.replace(/\s/g, ' ')).toBe("175 000 so'm")
    expect(label.oldPrice?.replace(/\s/g, ' ')).toBe('250 000')
  })

  it('aksiyasiz yorliqda eski narx yo‘q', () => {
    expect(labelJob(items, SHOP).labels[0]?.oldPrice).toBe('')
  })

  it('soni kamida bitta', () => {
    const zero = [{ ...items[0]!, quantity: 0 }]

    expect(labelJob(zero, SHOP).labels[0]?.quantity).toBe(1)
  })
})

describe('shelfLabelJob', () => {
  const cells = ['A1', 'A2']

  it('har javonga bitta yorliq', () => {
    expect(shelfLabelJob(cells, SHOP).labels).toEqual([
      { cell: 'A1', quantity: 1 },
      { cell: 'A2', quantity: 1 },
    ])
  })

  it('harf balandligini ilova beradi — agentni yangilash shart emas', () => {
    expect(shelfLabelJob(cells, SHOP).textMm).toBe(SHELF_TEXT_MM)
  })

  it('o‘lchamni do‘kon sozlamasidan oladi, yo‘q bo‘lsa 40×30 mm', () => {
    const wide = { ...SHOP, label_width_mm: 58, label_height_mm: 40 } as ShopSettings

    expect(shelfLabelJob(cells, wide)).toMatchObject({ widthMm: 58, heightMm: 40 })
    expect(shelfLabelJob(cells, null)).toMatchObject({ widthMm: 40, heightMm: 30 })
  })

  it('bo‘sh manzil yorliqqa tushmaydi', () => {
    expect(shelfLabelJob([...cells, ''], SHOP).labels).toHaveLength(2)
  })
})

describe('sendShelfLabels', () => {
  it('eski agent buyruqni bilmasa — yangilash kerakligini aytadi', async () => {
    // Eski agentning javobi «bunday manzil yo'q» — ombor sahifasida bu
    // javon manzili haqidagidek o'qilardi
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: false,
        status: 404,
        json: async () => ({ error: 'bunday manzil yo‘q' }),
      }),
    )

    await expect(sendShelfLabels(shelfLabelJob(['A1'], SHOP))).rejects.toThrow('agent eski')
  })
})

describe('health', () => {
  it('agent ishlamasa null qaytaradi', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockRejectedValue(new Error('ulanib bo‘lmadi')),
    )

    expect(await health()).toBeNull()
  })

  it('agent javob bersa holatini qaytaradi', async () => {
    const body = { version: '1.1.0', codePage: 'cp1252', printers: [] }

    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({ ok: true, json: async () => body }),
    )

    expect(await health()).toEqual(body)
  })
})

describe('sendReceipt', () => {
  it('agent xatosini matn bilan ko‘tarib beradi', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: false,
        status: 503,
        json: async () => ({ error: 'chek printeri sozlanmagan' }),
      }),
    )

    await expect(sendReceipt(receiptPayload(SALE, ''))).rejects.toThrow(
      'chek printeri sozlanmagan',
    )
  })
})
