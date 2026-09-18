import assert from 'node:assert/strict'
import { describe, it, before, after } from 'node:test'

import { createServer, validateLabels, validateReceipt, VERSION } from '../src/server.js'

const ORIGIN = 'http://127.0.0.1:5173'
const TOKEN = 'sinov-token'

const CONFIG = {
  port: 0,
  origins: [ORIGIN],
  codePage: 'cp1252',
  token: TOKEN,
  printers: {
    receipt: { transport: 'file', path: 'sinov.bin', columns: 48 },
    label: { transport: 'file', path: 'sinov-label.bin' },
  },
}

const RECEIPT = {
  shopName: 'Madlen sen',
  number: 'SOT-2026-000123',
  lines: [{ name: 'Koʻylak', quantity: 1, unitPrice: '250000', lineTotal: '250000' }],
  total: '250000',
  payments: { cash: '250000' },
  barcode: '2026000123',
}

const LABELS = {
  widthMm: 40,
  heightMm: 30,
  labels: [{ name: 'Koʻylak', variant: 'M / Oq', price: '250 000', barcode: '2000000000015', quantity: 2 }],
}

const JSON_HEADERS = { 'Content-Type': 'application/json', Origin: ORIGIN }

describe('validateReceipt', () => {
  it('to‘g‘ri chekni qabul qiladi', () => {
    assert.equal(validateReceipt(RECEIPT), null)
  })

  it('qatorsiz chekni rad etadi', () => {
    assert.match(validateReceipt({ total: '1', lines: [] }), /qator/)
  })

  it('nomsiz qatorni rad etadi', () => {
    assert.match(validateReceipt({ ...RECEIPT, lines: [{ quantity: 1 }] }), /nomi/)
  })

  it('summasiz chekni rad etadi', () => {
    assert.match(validateReceipt({ ...RECEIPT, total: 'salom' }), /summa/)
  })
})

describe('validateLabels', () => {
  it('to‘g‘ri ro‘yxatni qabul qiladi', () => {
    assert.equal(validateLabels(LABELS), null)
  })

  it('bo‘sh ro‘yxatni rad etadi', () => {
    assert.match(validateLabels({ labels: [] }), /bo‘sh/)
  })

  it('shtrix-kodsiz yorliqni rad etadi', () => {
    assert.match(validateLabels({ labels: [{ name: 'Koylak' }] }), /shtrix-kod/)
  })

  it('noto‘g‘ri sonni rad etadi', () => {
    const bad = { labels: [{ name: 'A', barcode: '2000000000015', quantity: 0 }] }

    assert.match(validateLabels(bad), /soni/)
  })
})

describe('HTTP xizmat', () => {
  let server
  let base
  let printed
  let failNext

  before(async () => {
    printed = []
    failNext = null

    server = createServer(CONFIG, {
      send: async (printer, bytes) => {
        if (failNext) {
          const message = failNext

          failNext = null
          throw new Error(message)
        }

        printed.push({ printer, bytes })
      },
      probe: async () => true,
      now: () => '2026-09-18T10:00:00.000Z',
    })

    await new Promise((resolve) => server.listen(0, '127.0.0.1', resolve))

    base = `http://127.0.0.1:${server.address().port}`
  })

  after(() => server.close())

  it('/health agent versiyasi va printerlarni qaytaradi', async () => {
    const response = await fetch(`${base}/health`, { headers: { Origin: ORIGIN } })
    const body = await response.json()

    assert.equal(response.status, 200)
    assert.equal(body.version, VERSION)
    assert.equal(body.printers.length, 2)
    assert.equal(body.printers[0].responds, true)
    assert.equal(body.printers[0].lastError, null)
    assert.equal(response.headers.get('access-control-allow-origin'), ORIGIN)
  })

  it('begona manzildan kelgan so‘rovni rad etadi', async () => {
    const response = await fetch(`${base}/health`, {
      headers: { Origin: 'http://zararli.example' },
    })

    assert.equal(response.status, 403)
    assert.equal(response.headers.get('access-control-allow-origin'), null)
  })

  it('Origin bo‘lmasa token talab qilinadi', async () => {
    const withoutToken = await fetch(`${base}/health`)

    assert.equal(withoutToken.status, 403)

    const withToken = await fetch(`${base}/health`, { headers: { 'X-Agent-Token': TOKEN } })

    assert.equal(withToken.status, 200)
  })

  it('JSON bo‘lmagan so‘rovni rad etadi (415)', async () => {
    const response = await fetch(`${base}/receipt`, {
      method: 'POST',
      headers: { 'Content-Type': 'text/plain', Origin: ORIGIN },
      body: 'salom',
    })

    assert.equal(response.status, 415)
  })

  it('/receipt chekni printerga yuboradi', async () => {
    const response = await fetch(`${base}/receipt`, {
      method: 'POST',
      headers: JSON_HEADERS,
      body: JSON.stringify(RECEIPT),
    })

    const body = await response.json()

    assert.equal(response.status, 200)
    assert.equal(body.ok, true)

    const bytes = printed.at(-1).bytes

    assert.deepEqual(bytes.subarray(0, 2), Buffer.from([0x1b, 0x40]))
    assert.ok(bytes.toString('latin1').includes("Ko'ylak"))
  })

  it('/labels yorliqlarni printerga yuboradi', async () => {
    const response = await fetch(`${base}/labels`, {
      method: 'POST',
      headers: JSON_HEADERS,
      body: JSON.stringify(LABELS),
    })

    const body = await response.json()

    assert.equal(response.status, 200)
    assert.equal(body.labels, 2)

    const commands = printed.at(-1).bytes.toString('latin1')

    assert.match(commands, /SIZE 40 mm,30 mm/)
    assert.match(commands, /PRINT 2,1/)
  })

  it('noto‘g‘ri chekda 400 va sababi qaytadi', async () => {
    const response = await fetch(`${base}/receipt`, {
      method: 'POST',
      headers: JSON_HEADERS,
      body: JSON.stringify({ lines: [] }),
    })

    assert.equal(response.status, 400)
    assert.match((await response.json()).error, /qator/)
  })

  it('printer xatosi /health da ko‘rinadi', async () => {
    failNext = 'printer javob bermadi (timeout)'

    const failed = await fetch(`${base}/receipt`, {
      method: 'POST',
      headers: JSON_HEADERS,
      body: JSON.stringify(RECEIPT),
    })

    assert.equal(failed.status, 500)

    const health = await (await fetch(`${base}/health`, { headers: { Origin: ORIGIN } })).json()
    const receipt = health.printers.find((item) => item.name === 'receipt')

    assert.equal(receipt.lastError.message, 'printer javob bermadi (timeout)')
    assert.equal(receipt.lastError.at, '2026-09-18T10:00:00.000Z')
  })

  it('muvaffaqiyatli chop etish xatoni tozalaydi', async () => {
    await fetch(`${base}/receipt`, {
      method: 'POST',
      headers: JSON_HEADERS,
      body: JSON.stringify(RECEIPT),
    })

    const health = await (await fetch(`${base}/health`, { headers: { Origin: ORIGIN } })).json()
    const receipt = health.printers.find((item) => item.name === 'receipt')

    assert.equal(receipt.lastError, null)
  })

  it('noma’lum manzilda 404', async () => {
    const response = await fetch(`${base}/yoq`, { headers: { Origin: ORIGIN } })

    assert.equal(response.status, 404)
  })
})
