/**
 * Yorliqni TSPL buyruqlariga o'giradi (Xprinter XP-365B).
 *
 * TSPL — yorliq printerlarining tili. Brauzer orqali chop etishdan
 * farqi: o'lcham printerga aniq aytiladi, EAN-13 ni printerning o'zi
 * chizadi (chiziqlar nuqtalarga tushadi) va yorliqlar orasida bo'sh
 * yorliq chiqmaydi.
 *
 * Nega bo'sh yorliq chiqadi: har yorliqdan keyin `FORMFEED` yuborilsa
 * yoki `SIZE`/`GAP` qayta yuborilsa, printer qog'ozni bir yorliqqa
 * surib qo'yadi. Shuning uchun bu yerda o'lcham **bir marta**
 * beriladi, keyin har yorliq uchun `CLS` + chizish + `PRINT n,1`.
 */

import { normalize } from './text.js'

/** 203 dpi da bitta millimetr necha nuqta */
export const DOTS_PER_MM = 8

export const LABEL_DEFAULTS = {
  widthMm: 40,
  heightMm: 30,
  gapMm: 2,
  /** Qoraligi: 0-15. Chiziqlar oqarib chiqsa oshiring */
  density: 8,
  /** Tezlik, dyuym/soniya. Pastroq tezlik — aniqroq chiziq */
  speed: 4,
  /** Shtrix-kod balandligi, nuqta (90 ~ 11 mm) */
  barcodeHeight: 90,
  /** Tor va keng chiziq nisbati */
  barcodeNarrow: 2,
  barcodeWide: 2,
}

/** TSPL matni qo'shtirnoq ichida yuboriladi — ichidagisini tozalaymiz. */
function quote(value) {
  return normalize(value).replace(/["\\]/g, '').replace(/[\r\n]+/g, ' ').trim()
}

/** Matnni belgilangan uzunlikka qisqartiradi (yorliq tor). */
function fit(value, limit) {
  const text = quote(value)

  return text.length <= limit ? text : `${text.slice(0, Math.max(0, limit - 1))}.`
}

/**
 * Yorliqlar to'plamini TSPL ga o'giradi.
 *
 * @param {object} job - { widthMm, heightMm, gapMm, density, speed, labels[] }
 * @param {object} options - LABEL_DEFAULTS ustidan yoziladigan qiymatlar
 */
export function buildLabels(job, options = {}) {
  const settings = { ...LABEL_DEFAULTS, ...options, ...clean(job) }
  const lines = []

  // O'lcham va zichlik — butun ish uchun bir marta
  lines.push(`SIZE ${settings.widthMm} mm,${settings.heightMm} mm`)
  lines.push(`GAP ${settings.gapMm} mm,0 mm`)
  lines.push('DIRECTION 1')
  lines.push('REFERENCE 0,0')
  lines.push(`DENSITY ${settings.density}`)
  lines.push(`SPEED ${settings.speed}`)
  lines.push('CODEPAGE 1252')

  const width = settings.widthMm * DOTS_PER_MM
  const height = settings.heightMm * DOTS_PER_MM

  // Yorliqqa sig'adigan taxminiy belgi soni (2-shrift ~12 nuqta keng)
  const nameLimit = Math.floor(width / 12)
  const smallLimit = Math.floor(width / 9)

  for (const label of job.labels ?? []) {
    const quantity = Math.max(1, Number(label.quantity) || 1)

    lines.push('CLS')

    if (label.shopName) {
      lines.push(`TEXT 12,8,"1",0,1,1,"${fit(label.shopName, smallLimit)}"`)
    }

    lines.push(`TEXT 12,30,"2",0,1,1,"${fit(label.name, nameLimit)}"`)

    if (label.variant) {
      lines.push(`TEXT 12,58,"1",0,1,1,"${fit(label.variant, smallLimit)}"`)
    }

    if (label.price) {
      lines.push(`TEXT 12,80,"3",0,1,1,"${fit(label.price, nameLimit)}"`)
    }

    // Shtrix-kodni printerning o'zi chizadi — rasm yuborilmaydi
    if (label.barcode) {
      const barcodeY = height - settings.barcodeHeight - 40

      lines.push(
        `BARCODE 20,${barcodeY},"EAN13",${settings.barcodeHeight},1,0,` +
          `${settings.barcodeNarrow},${settings.barcodeWide},"${quote(label.barcode)}"`,
      )
    }

    // Nechta dona — shuncha nusxa. Orada FORMFEED yo'q.
    lines.push(`PRINT ${quantity},1`)
  }

  return Buffer.from(`${lines.join('\r\n')}\r\n`, 'latin1')
}

/** So'rovdan faqat ma'lum sozlamalarni oladi. */
function clean(job = {}) {
  const allowed = ['widthMm', 'heightMm', 'gapMm', 'density', 'speed']
  const result = {}

  for (const key of allowed) {
    const value = Number(job[key])

    if (Number.isFinite(value) && value > 0) result[key] = value
  }

  return result
}
