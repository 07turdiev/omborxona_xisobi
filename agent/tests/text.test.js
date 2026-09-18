import assert from 'node:assert/strict'
import { describe, it } from 'node:test'

import { encode, formatAmount, normalize, twoColumns, wrap } from '../src/text.js'

describe('normalize', () => {
  it("o'zbekcha tutuq belgilarini oddiy apostrofga keltiradi", () => {
    assert.equal(normalize('Yozgi koʻylak'), "Yozgi ko'ylak")
    assert.equal(normalize('gʻisht'), "g'isht")
    assert.equal(normalize('Toʼliq'), "To'liq")
  })

  it('tipografik qo‘shtirnoq va tirelarni almashtiradi', () => {
    assert.equal(normalize('“Madlen sen”'), '"Madlen sen"')
    assert.equal(normalize('«Madlen»'), '"Madlen"')
    assert.equal(normalize('2026–2027'), '2026-2027')
  })

  it('uzilmas bo‘shliqni oddiy bo‘shliqqa aylantiradi', () => {
    assert.equal(normalize('450 000'), '450 000')
  })

  it('bo‘sh qiymatdan bo‘sh satr chiqadi', () => {
    assert.equal(normalize(null), '')
    assert.equal(normalize(undefined), '')
  })
})

describe('encode', () => {
  it('ASCII matnni o‘zgartirmaydi', () => {
    assert.deepEqual(encode('JAMI 450 000'), Buffer.from('JAMI 450 000', 'ascii'))
  })

  it('o‘zbekcha belgilar apostrofga aylanib, bir baytdan joy oladi', () => {
    const bytes = encode('koʻylak')

    assert.equal(bytes.toString('latin1'), "ko'ylak")
    assert.equal(bytes.length, 7)
  })

  it('ascii rejimida kod sahifasidagi belgilar tashlanadi', () => {
    // é — CP1252 da bor, ASCII da yo'q
    assert.equal(encode('café', 'cp1252').length, 4)
    assert.equal(encode('café', 'ascii').toString('ascii'), 'caf')
  })

  it('kirill harflari ikkala sahifada ham tashlanadi', () => {
    // Printer bu belgilarni bilmaydi — yarim tanilgan belgidan
    // ko'ra yo'qligi tushunarliroq
    assert.equal(encode('Чек', 'cp1252').length, 0)
  })
})

describe('wrap', () => {
  it('uzun matnni ustun kengligiga bo‘ladi', () => {
    assert.deepEqual(wrap('bir ikki uch tort besh', 9), ['bir ikki', 'uch tort', 'besh'])
  })

  it('ustundan uzun so‘zni kesadi', () => {
    assert.deepEqual(wrap('aaaaaaaaaaaa', 5), ['aaaaa', 'aaaaa', 'aa'])
  })

  it('bo‘sh matndan bitta bo‘sh satr', () => {
    assert.deepEqual(wrap('', 10), [''])
  })
})

describe('twoColumns', () => {
  it('summani o‘ng chekkaga tekislaydi', () => {
    assert.deepEqual(twoColumns('JAMI', '450 000', 20), ['JAMI         450 000'])
  })

  it('sig‘masa, summa keyingi satrda o‘ngda qoladi', () => {
    const rows = twoColumns('Juda uzun mahsulot nomi', '450 000', 12)

    assert.ok(rows.length > 1)
    assert.equal(rows.at(-1), '     450 000')
    assert.equal(rows.at(-1).length, 12)
  })
})

describe('formatAmount', () => {
  it('minglarni bo‘shliq bilan ajratadi', () => {
    assert.equal(formatAmount('450000.00'), '450 000')
    assert.equal(formatAmount(1234567), '1 234 567')
  })

  it('tiyin bo‘lsa vergul bilan ko‘rsatadi', () => {
    assert.equal(formatAmount('1000.50'), '1 000,50')
  })

  it('noto‘g‘ri qiymatda nol qaytaradi', () => {
    assert.equal(formatAmount('salom'), '0')
    assert.equal(formatAmount(null), '0')
  })
})
