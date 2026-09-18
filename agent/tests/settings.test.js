import assert from 'node:assert/strict'
import { describe, it } from 'node:test'

import { defined, merge } from '../src/settings.js'

const DEFAULTS = { columns: 48, feedBeforeCut: 5, gapMm: 2, cut: 'full' }
const RULES = { positive: ['columns', 'feedBeforeCut'], nonNegative: ['gapMm'] }

/** Ogohlantirishlarni ushlab qoladi — testda konsol toza qolsin. */
function warnings(run) {
  const original = console.warn
  const messages = []

  console.warn = (message) => messages.push(message)

  try {
    run()
  } finally {
    console.warn = original
  }

  return messages
}

describe('defined', () => {
  it('undefined va null tashlanadi', () => {
    assert.deepEqual(defined({ a: 1, b: undefined, c: null }), { a: 1 })
  })

  it('0 va false qoladi — ular ham qiymat', () => {
    assert.deepEqual(defined({ a: 0, b: false, c: '' }), { a: 0, b: false, c: '' })
  })
})

describe('merge', () => {
  it('sozlamada yo‘q kalit standartni bosib ketmaydi', () => {
    // Aynan shu xato bor edi: server `{ columns: undefined }` uzatardi
    const settings = merge(DEFAULTS, { columns: undefined, feedBeforeCut: undefined }, RULES)

    assert.equal(settings.columns, 48)
    assert.equal(settings.feedBeforeCut, 5)
  })

  it('berilgan qiymat standartdan ustun', () => {
    assert.equal(merge(DEFAULTS, { columns: 32 }, RULES).columns, 32)
  })

  it('matn ko‘rinishidagi son qabul qilinadi', () => {
    assert.equal(merge(DEFAULTS, { columns: '32' }, RULES).columns, 32)
  })

  it('noto‘g‘ri son standart bilan almashtiriladi', () => {
    let settings

    const messages = warnings(() => {
      settings = merge(DEFAULTS, { columns: 'katta', feedBeforeCut: -3 }, RULES, 'chek printeri')
    })

    assert.equal(settings.columns, 48)
    assert.equal(settings.feedBeforeCut, 5)
    assert.equal(messages.length, 2)
  })

  it('ogohlantirishda printer nomi va sozlama nomi bo‘ladi', () => {
    const [message] = warnings(() => merge(DEFAULTS, { columns: 0 }, RULES, 'chek printeri'))

    assert.match(message, /chek printeri/)
    assert.match(message, /"columns"/)
    assert.match(message, /48/)
  })

  it('nolga ruxsat berilgan sozlama ogohlantirmaydi', () => {
    let settings

    const messages = warnings(() => {
      settings = merge(DEFAULTS, { gapMm: 0 }, RULES)
    })

    assert.equal(settings.gapMm, 0)
    assert.deepEqual(messages, [])
  })

  it('son bo‘lmagan sozlamalarga tegilmaydi', () => {
    assert.equal(merge(DEFAULTS, { cut: 'partial' }, RULES).cut, 'partial')
  })
})
