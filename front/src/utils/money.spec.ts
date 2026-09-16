import { describe, expect, it } from 'vitest'

import {
  addMoney,
  compareMoney,
  formatMoney,
  formatSum,
  fromCents,
  isZero,
  multiplyMoney,
  normalizeMoneyInput,
  percentOf,
  subtractMoney,
  toCents,
} from './money'

describe('tiyinga o‘girish', () => {
  it('butun va kasr qismni oladi', () => {
    expect(toCents('450000')).toBe(45000000n)
    expect(toCents('450000.50')).toBe(45000050n)
    expect(toCents('0.05')).toBe(5n)
    expect(toCents('')).toBe(0n)
    expect(toCents(null)).toBe(0n)
  })

  it('probel va vergulni tushunadi', () => {
    expect(toCents('450 000,50')).toBe(45000050n)
    expect(toCents('1 250')).toBe(125000n)
  })

  it('noto‘g‘ri qiymatda xato beradi', () => {
    expect(() => toCents('ellik ming')).toThrow()
  })

  it('orqaga qaytaradi', () => {
    expect(fromCents(45000050n)).toBe('450000.50')
    expect(fromCents(5n)).toBe('0.05')
    expect(fromCents(-125000n)).toBe('-1250.00')
  })
})

describe('arifmetika', () => {
  it('qo‘shadi va ayiradi', () => {
    expect(addMoney('450000.50', '0.50')).toBe('450001.00')
    expect(subtractMoney('500000', '50000')).toBe('450000.00')
  })

  it('suzuvchi nuqta xatosiga tushmaydi', () => {
    // 0.1 + 0.2 === 0.30000000000000004 muammosi bu yerda yo'q
    expect(addMoney('0.10', '0.20')).toBe('0.30')
  })

  it('miqdorga ko‘paytiradi', () => {
    expect(multiplyMoney('250000', 2)).toBe('500000.00')
    expect(multiplyMoney('33.33', 3)).toBe('99.99')
  })

  it('foizni yarmi yuqoriga yaxlitlaydi', () => {
    expect(percentOf('500000', '10')).toBe('50000.00')
    expect(percentOf('99.99', '10')).toBe('10.00')
    // 12.345 → 12.35
    expect(percentOf('246.90', '5')).toBe('12.35')
  })

  it('solishtiradi', () => {
    expect(compareMoney('100', '100.00')).toBe(0)
    expect(compareMoney('100', '200')).toBe(-1)
    expect(compareMoney('300', '200')).toBe(1)
    expect(isZero('0.00')).toBe(true)
  })
})

describe('ko‘rsatish', () => {
  it('uch xonadan guruhlaydi', () => {
    expect(formatMoney('450000.00')).toBe('450 000')
    expect(formatMoney('1250000')).toBe('1 250 000')
    expect(formatMoney('999')).toBe('999')
  })

  it('tiyin faqat kerak bo‘lganda chiqadi', () => {
    expect(formatMoney('450000.50')).toBe('450 000,50')
    expect(formatMoney('0.05')).toBe('0,05')
  })

  it('bo‘sh qiymat chiziqcha bo‘ladi', () => {
    expect(formatMoney(null)).toBe('—')
    expect(formatSum(undefined)).toBe('—')
  })

  it('manfiy summani belgilaydi', () => {
    expect(formatMoney('-50000')).toBe('−50 000')
  })

  it('valyuta bilan chiqaradi', () => {
    expect(formatSum('450000')).toBe("450 000 so'm")
  })
})

describe('kiritishni tozalash', () => {
  it('serverga yuboriladigan ko‘rinishga keltiradi', () => {
    expect(normalizeMoneyInput('450 000,50')).toBe('450000.50')
    expect(normalizeMoneyInput('  ')).toBe('0')
    expect(normalizeMoneyInput('250000')).toBe('250000.00')
  })
})
