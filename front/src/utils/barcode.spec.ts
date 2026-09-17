import { describe, expect, it } from 'vitest'

import {
  DOT_MM,
  EAN13_SYMBOL_MODULES,
  MODULE_MM,
  QUIET_ZONES,
  dotsPerModule,
  fitsLabel,
  fitsPrinterDots,
  totalModules,
  widthMm,
} from './barcode'

describe('printer nuqtalari', () => {
  it('203 dpi da bitta nuqta 0.125 mm', () => {
    expect(DOT_MM).toBeCloseTo(0.125, 3)
  })

  it('0.25 mm modul roppa-rosa 2 nuqta', () => {
    expect(dotsPerModule(MODULE_MM)).toBeCloseTo(2, 2)
    expect(fitsPrinterDots(MODULE_MM)).toBe(true)
  })

  it('0.5 mm ham butun (4 nuqta)', () => {
    expect(fitsPrinterDots(0.5)).toBe(true)
  })

  it('nuqtaga butun bo‘linmaydigan kenglik rad etiladi', () => {
    // 0.3 mm = 2.4 nuqta — printer yaxlitlaydi va chiziqlar teng bo'lmaydi
    expect(fitsPrinterDots(0.3)).toBe(false)
    // JsBarcode ning standart 1px moduli ~0.2646 mm = 2.1 nuqta
    expect(fitsPrinterDots(25.4 / 96)).toBe(false)
  })
})

describe('EAN-13 o‘lchami', () => {
  const modules = totalModules('EAN13', EAN13_SYMBOL_MODULES)

  it('belgi 95 modul, tinch zonalar bilan 113', () => {
    expect(EAN13_SYMBOL_MODULES).toBe(95)
    expect(QUIET_ZONES.EAN13).toEqual({ left: 11, right: 7 })
    expect(modules).toBe(113)
  })

  it('0.25 mm modulda kenglik 28.25 mm', () => {
    expect(widthMm(modules)).toBe(28.25)
  })

  it('40 mm yorliqqa sig‘adi, 20 mm yorliqqa sig‘maydi', () => {
    expect(fitsLabel(modules, 40)).toBe(true)
    expect(fitsLabel(modules, 20)).toBe(false)
  })

  it('yorliqda har tomonda kamida 5 mm hoshiya qoladi', () => {
    const margin = (40 - widthMm(modules)) / 2

    expect(margin).toBeGreaterThan(5)
  })
})

describe('CODE128 o‘lchami', () => {
  it('tinch zonalar ikki tomonda 10 modul', () => {
    expect(QUIET_ZONES.CODE128).toEqual({ left: 10, right: 10 })
  })

  it('10 xonali chek kodi 72 mm chek eniga bemalol sig‘adi', () => {
    // Code128C: start + 5 juftlik + nazorat = 7 belgi × 11 + 13 (stop)
    const symbol = 7 * 11 + 13
    const modules = totalModules('CODE128', symbol)

    expect(modules).toBe(110)
    expect(widthMm(modules)).toBe(27.5)
    expect(fitsLabel(modules, 72)).toBe(true)
  })
})
