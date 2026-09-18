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
 *
 * TSPL da matnni markazga qo'yish buyrug'i yo'q — x koordinatasi
 * shrift kengligidan hisoblab chiqariladi.
 */

import { merge } from './settings.js'
import { normalize } from './text.js'

/** 203 dpi da bitta millimetr necha nuqta */
export const DOTS_PER_MM = 8

/** Ichki shriftlarda bitta belgi necha nuqta (x1 kattalashtirishda) */
const FONT_WIDTH = { 1: 8, 2: 12, 3: 16, 4: 24, 5: 32 }

/** Yorliq chetidan qoldiriladigan eng kam bo'shliq, nuqta */
const MARGIN = 8

/** EAN-13 doim 95 modul (tinch zonasiz) */
const EAN13_MODULES = 95

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

const LABEL_RULES = {
  positive: [
    'widthMm',
    'heightMm',
    'density',
    'speed',
    'barcodeHeight',
    'barcodeNarrow',
    'barcodeWide',
  ],
  // Uzluksiz lentada yorliqlar orasida oraliq bo'lmaydi
  nonNegative: ['gapMm'],
}

/** TSPL matni qo'shtirnoq ichida yuboriladi — ichidagisini tozalaymiz. */
function quote(value) {
  return normalize(value).replace(/["\\]/g, '').replace(/[\r\n]+/g, ' ').trim()
}

/** Matnni yorliqqa sig'adigan uzunlikka qisqartiradi. */
function fit(value, labelWidth, font) {
  const limit = Math.floor((labelWidth - MARGIN * 2) / FONT_WIDTH[font])
  const text = quote(value)

  return text.length <= limit ? text : `${text.slice(0, Math.max(0, limit - 1))}.`
}

/** Matn yorliq o'rtasida turishi uchun x koordinatasi. */
function centerText(labelWidth, text, font) {
  return Math.max(MARGIN, Math.round((labelWidth - text.length * FONT_WIDTH[font]) / 2))
}

/** Shtrix-kod yorliq o'rtasida turishi uchun x koordinatasi. */
function centerBarcode(labelWidth, narrow) {
  return Math.max(MARGIN, Math.round((labelWidth - EAN13_MODULES * narrow) / 2))
}

/**
 * Yorliqlar to'plamini TSPL ga o'giradi.
 *
 * @param {object} job - { widthMm, heightMm, gapMm, density, speed, labels[] }
 * @param {object} options - LABEL_DEFAULTS ustidan yoziladigan qiymatlar;
 *   yo'q qiymatlar standart bilan to'ldiriladi
 * @param {string} where - ogohlantirishlarda ko'rsatiladigan printer nomi
 */
export function buildLabels(job, options = {}, where = 'yorliq printeri') {
  const settings = merge(LABEL_DEFAULTS, { ...options, ...clean(job) }, LABEL_RULES, where)
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

  for (const label of job.labels ?? []) {
    const quantity = Math.max(1, Number(label.quantity) || 1)

    lines.push('CLS')

    /** Bitta qatorni yorliq o'rtasiga yozadi */
    const put = (y, font, value) => {
      const text = fit(value, width, font)

      if (!text) return

      lines.push(`TEXT ${centerText(width, text, font)},${y},"${font}",0,1,1,"${text}"`)
    }

    if (label.shopName) put(8, 1, label.shopName)

    put(30, 2, label.name)

    if (label.variant) put(58, 1, label.variant)
    if (label.price) put(80, 3, label.price)

    // Shtrix-kodni printerning o'zi chizadi — rasm yuborilmaydi
    if (label.barcode) {
      const y = height - settings.barcodeHeight - 40
      const x = centerBarcode(width, settings.barcodeNarrow)

      lines.push(
        `BARCODE ${x},${y},"EAN13",${settings.barcodeHeight},1,0,` +
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

    // `0` ham to'g'ri qiymat (uzluksiz lentada oraliq yo'q); butunlay
    // noto'g'ri qiymatni quyida `merge` ushlaydi
    if (Number.isFinite(value) && value >= 0) result[key] = value
  }

  return result
}
