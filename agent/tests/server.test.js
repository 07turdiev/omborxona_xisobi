import assert from 'node:assert/strict'
import { describe, it, before, after } from 'node:test'

import { createServer, validateReceipt, VERSION } from '../src/server.js'

const ORIGIN = 'http://127.0.0.1:5173'

const CONFIG = {
  port: 0,
  origins: [ORIGIN],
  codePage: 'cp1252',
  printers: {
    receipt: { transport: 'file', path: 'sinov.bin', columns: 48 },
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

describe('validateReceipt', () => {
  it('to‘g‘ri chekni qabul qiladi', () => {
    assert.equal(validateReceipt(RECEIPT), null)
  })

  it('qatorsiz chekni rad etadi', () => {
    assert.match(validateReceipt({ total: '1', lines: [] }), /qator/)
  })

  it('nomsiz qatorni rad etadi', () => {
    const bad = { ...RECEIPT, lines: [{ quantity: 1 }] }

    assert.match(validateReceipt(bad), /nomi/)
  })

  it('summasiz chekni rad etadi', () => {
    const bad = { ...RECEIPT, total: 'salom' }

    assert.match(validateReceipt(bad), /summa/)
  })
})

describe('HTTP xizmat', () => {
  let server
  let base
  let printed

  before(async () => {
    printed = []

    server = createServer(CONFIG, {
      send: async (printer, bytes) => printed.push({ printer, bytes }),
      probe: async () => true,
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
    assert.equal(body.printers.length, 1)
    assert.equal(body.printers[0].name, 'receipt')
    assert.equal(body.printers[0].responds, true)
    assert.equal(response.headers.get('access-control-allow-origin'), ORIGIN)
  })

  it('begona manzildan kelgan so‘rovni rad etadi', async () => {
    const response = await fetch(`${base}/health`, {
      headers: { Origin: 'http://zararli.example' },
    })

    assert.equal(response.status, 403)
    assert.equal(response.headers.get('access-control-allow-origin'), null)
  })

  it('/receipt chekni printerga yuboradi', async () => {
    const response = await fetch(`${base}/receipt`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Origin: ORIGIN },
      body: JSON.stringify(RECEIPT),
    })

    const body = await response.json()

    assert.equal(response.status, 200)
    assert.equal(body.ok, true)
    assert.equal(printed.length, 1)

    const bytes = printed[0].bytes

    assert.ok(bytes.length > 50)
    assert.deepEqual(bytes.subarray(0, 2), Buffer.from([0x1b, 0x40]))
    assert.ok(bytes.toString('latin1').includes("Ko'ylak"))
  })

  it('noto‘g‘ri chekda 400 va sababi qaytadi', async () => {
    const response = await fetch(`${base}/receipt`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Origin: ORIGIN },
      body: JSON.stringify({ lines: [] }),
    })

    assert.equal(response.status, 400)
    assert.match((await response.json()).error, /qator/)
  })

  it('noma’lum manzilda 404', async () => {
    const response = await fetch(`${base}/yoq`, { headers: { Origin: ORIGIN } })

    assert.equal(response.status, 404)
  })
})
