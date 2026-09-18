import assert from 'node:assert/strict'
import { mkdtempSync, rmSync, writeFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import { describe, it } from 'node:test'

import { loadConfig } from '../src/config.js'

/** Vaqtinchalik `config.json` yozib, uni o'qiydi va ogohlantirishlarni ushlaydi. */
function load(content) {
  const directory = mkdtempSync(join(tmpdir(), 'agent-config-'))
  const path = join(directory, 'config.json')

  writeFileSync(path, JSON.stringify(content))

  const original = console.warn
  const messages = []

  console.warn = (message) => messages.push(message)

  try {
    return { config: loadConfig(path), messages }
  } finally {
    console.warn = original
    rmSync(directory, { recursive: true, force: true })
  }
}

describe('loadConfig', () => {
  it('fayl yo‘q bo‘lsa standart qiymatlar olinadi', () => {
    const config = loadConfig(join(tmpdir(), 'yo-q-bunday-fayl.json'))

    assert.equal(config.port, 7777)
    assert.equal(config.codePage, 'cp1252')
    assert.deepEqual(config.printers, {})
  })

  it('fayldagi qiymat standartdan ustun', () => {
    const { config } = load({ port: 8888, printers: { receipt: { transport: 'tcp' } } })

    assert.equal(config.port, 8888)
    assert.equal(config.printers.receipt.transport, 'tcp')
  })

  it('to‘g‘ri sozlamalar ogohlantirmaydi', () => {
    const { messages } = load({
      printers: {
        receipt: { transport: 'tcp', host: '192.0.2.10', port: 9100, columns: 48, cut: 'full' },
      },
    })

    assert.deepEqual(messages, [])
  })

  it('noma’lum sozlama haqida ogohlantiradi', () => {
    const { messages } = load({
      printers: { receipt: { transport: 'tcp', rangi: 'qora' } },
    })

    assert.equal(messages.length, 1)
    assert.match(messages[0], /receipt/)
    assert.match(messages[0], /"rangi"/)
  })

  it('katta-kichik harf xatosida to‘g‘ri nomni taklif qiladi', () => {
    // Bunday kalit jimgina e'tiborsiz qolardi
    const { messages } = load({
      printers: { receipt: { transport: 'tcp', barcodeheight: 120 } },
    })

    assert.equal(messages.length, 1)
    assert.match(messages[0], /"barcodeheight"/)
    assert.match(messages[0], /"barcodeHeight"/)
  })
})
