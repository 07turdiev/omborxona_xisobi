import { describe, expect, it } from 'vitest'

import { formatDate, formatDayMonth, formatTime } from './date'

describe('sana ko‘rinishi', () => {
  it('to‘liq sana kun.oy.yil', () => {
    expect(formatDate('2026-09-21')).toBe('21.09.2026')
    expect(formatDate(null)).toBe('—')
  })

  it('qisqa sana: kun va oyning nomi', () => {
    expect(formatDayMonth('2026-09-21')).toBe('21-sen')
    expect(formatDayMonth('2026-01-05')).toBe('5-yan')
    expect(formatDayMonth('2026-12-31')).toBe('31-dek')
    expect(formatDayMonth(null)).toBe('—')
  })

  it('vaqt soat:daqiqa', () => {
    // Mahalliy vaqtdan yasaladi — test qaysi mintaqada yurishidan qat'i nazar
    const at = new Date(2026, 8, 21, 17, 40)

    expect(formatTime(at.toISOString())).toBe('17:40')
    expect(formatTime(null)).toBe('')
  })
})
