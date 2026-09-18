import assert from 'node:assert/strict'
import { readFileSync, writeFileSync, existsSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'
import { describe, it } from 'node:test'

import { buildReceipt, RECEIPT_DEFAULTS } from '../src/escpos.js'

const HERE = dirname(fileURLToPath(import.meta.url))
const FIXTURE = join(HERE, 'fixtures', 'receipt.hex')

/** Sinov uchun namuna chek — fixture shu ma'lumotdan tuziladi */
const SAMPLE = {
  shopName: 'Madlen sen',
  dateTime: '18.09.2026 14:35',
  number: 'SOT-2026-000123',
  cashier: 'kassir',
  lines: [
    {
      name: 'Yozgi koʻylak',
      variant: 'M / Oq',
      quantity: 2,
      unitPrice: '250000.00',
      lineTotal: '450000.00',
    },
  ],
  discount: '50000.00',
  total: '450000.00',
  payments: { cash: '500000.00', card: '0.00' },
  change: '50000.00',
  footer: 'Qaytarish uchun shu chekni saqlang',
  barcode: '2026000123',
}

function build(options = {}) {
  return buildReceipt(SAMPLE, { columns: 48, codePage: 'cp1252', ...options })
}

describe('buildReceipt — tuzilishi', () => {
  const bytes = build()

  it('printerni boshlang‘ich holatga qo‘yadi', () => {
    assert.deepEqual(bytes.subarray(0, 2), Buffer.from([0x1b, 0x40]))
  })

  it('kod sahifasini tanlaydi (ESC t 16 — CP1252)', () => {
    assert.deepEqual(bytes.subarray(2, 5), Buffer.from([0x1b, 0x74, 16]))
  })

  it('oxirida qog‘ozni to‘liq kesadi (GS V 0)', () => {
    assert.deepEqual(bytes.subarray(-3), Buffer.from([0x1d, 0x56, 0x00]))
  })

  it('CODE128 buyrug‘ini yuboradi va kodni {B bilan beradi', () => {
    const marker = Buffer.from([0x1d, 0x6b, 73])
    const at = bytes.indexOf(marker)

    assert.ok(at > 0, 'GS k 73 topilmadi')

    const length = bytes[at + 3]
    const data = bytes.subarray(at + 4, at + 4 + length).toString('latin1')

    assert.equal(data, '{B2026000123')
  })

  it('JAMI qalin shriftda chiqadi', () => {
    const boldOn = bytes.indexOf(Buffer.from([0x1b, 0x45, 1]))
    const jami = bytes.indexOf(Buffer.from('JAMI', 'ascii'))

    assert.ok(boldOn > 0 && jami > boldOn, 'JAMI qalin shrift ichida emas')
  })

  it("o'zbekcha belgilar apostrofga aylanadi", () => {
    const text = bytes.toString('latin1')

    assert.ok(text.includes("Yozgi ko'ylak"), 'nom noto‘g‘ri yozilgan')
    assert.ok(!text.includes('ʻ'), 'maxsus belgi qolib ketdi')
  })

  it('summalar va to‘lov turlari chekda bor', () => {
    const text = bytes.toString('latin1')

    assert.ok(text.includes('450 000'))
    assert.ok(text.includes('Chegirma'))
    assert.ok(text.includes('Naqd'))
    assert.ok(text.includes('Qaytim'))
  })

  it('pul qutisi faqat so‘ralganda ochiladi', () => {
    const pulse = Buffer.from([0x1b, 0x70, 0x00])

    assert.equal(bytes.indexOf(pulse), -1)
    assert.ok(build({ cashDrawer: true }).indexOf(pulse) > 0)
  })
})

describe('buildReceipt — kesish va qog‘oz tortish', () => {
  it('standart holatda 5 qator tortiladi', () => {
    // Bosh bilan pichoq orasidagi masofa: kam tortilsa oxirgi
    // qatorlar pichoqdan pastda qolib ketadi
    assert.equal(RECEIPT_DEFAULTS.feedBeforeCut, 5)

    const feed = Buffer.from([0x1b, 0x64, 5])

    assert.ok(build().indexOf(feed) > 0)
  })

  it('tortish qatorlari sozlanadi', () => {
    const bytes = build({ feedBeforeCut: 9 })

    assert.ok(bytes.indexOf(Buffer.from([0x1b, 0x64, 9])) > 0)
  })

  it('yarim kesish GS V 1 yuboradi', () => {
    assert.deepEqual(build({ cut: 'partial' }).subarray(-3), Buffer.from([0x1d, 0x56, 0x01]))
  })

  it('kesish o‘chirilsa buyruq umuman yuborilmaydi', () => {
    const bytes = build({ cut: 'none' })

    assert.equal(bytes.indexOf(Buffer.from([0x1d, 0x56])), -1)
  })
})

describe('buildReceipt — shtrix-kod o‘lchami', () => {
  it('standart balandlik 80 nuqta, kenglik 2', () => {
    const bytes = build()

    assert.ok(bytes.indexOf(Buffer.from([0x1d, 0x68, 80])) > 0)
    assert.ok(bytes.indexOf(Buffer.from([0x1d, 0x77, 2])) > 0)
  })

  it('o‘lcham sozlanadi', () => {
    const bytes = build({ barcodeHeight: 120, barcodeWidth: 3 })

    assert.ok(bytes.indexOf(Buffer.from([0x1d, 0x68, 120])) > 0)
    assert.ok(bytes.indexOf(Buffer.from([0x1d, 0x77, 3])) > 0)
  })
})

describe('buildReceipt — to‘liq bo‘lmagan sozlama', () => {
  /**
   * `config.json` da faqat `transport` va `path` bo'lsa, server aynan
   * shunday obyekt yasaydi: har bir sozlama `undefined`.
   */
  const fromMinimalConfig = {
    columns: undefined,
    codePage: undefined,
    cashDrawer: undefined,
    feedBeforeCut: undefined,
    cut: undefined,
    barcodeHeight: undefined,
    barcodeWidth: undefined,
  }

  it('standart qiymatlar saqlanadi — natija to‘liq sozlama bilan bir xil', () => {
    assert.deepEqual(buildReceipt(SAMPLE, fromMinimalConfig), build())
  })

  it('shtrix-kod va kesish o‘z joyida qoladi', () => {
    const bytes = buildReceipt(SAMPLE, fromMinimalConfig)

    // Ilgari bu qiymatlar 0 bo'lib qolardi: kod umuman bosilmasdi,
    // oxirgi qatorlar esa pichoqdan pastda qolib ketardi
    assert.ok(bytes.indexOf(Buffer.from([0x1d, 0x68, 80])) > 0, 'kod balandligi 0')
    assert.ok(bytes.indexOf(Buffer.from([0x1d, 0x77, 2])) > 0, 'kod kengligi 0')
    assert.ok(bytes.indexOf(Buffer.from([0x1b, 0x64, 5])) > 0, 'qog‘oz tortilmadi')
    assert.deepEqual(bytes.subarray(-3), Buffer.from([0x1d, 0x56, 0x00]))
  })

  it('baytlarda "undefined" yoki "NaN" bo‘lmaydi', () => {
    const text = buildReceipt(SAMPLE, fromMinimalConfig).toString('latin1')

    assert.equal(text.includes('undefined'), false)
    assert.equal(text.includes('NaN'), false)
  })
})

describe('buildReceipt — o‘zgarmaganligi (golden fixture)', () => {
  it('baytlar saqlangan namunaga aynan teng', () => {
    const current = build().toString('hex')

    if (!existsSync(FIXTURE)) {
      writeFileSync(FIXTURE, current)
      assert.fail('fixture yaratildi — testni qayta ishga tushiring')
    }

    assert.equal(current, readFileSync(FIXTURE, 'utf8').trim())
  })
})
