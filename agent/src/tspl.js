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

/** Ichki shriftlarda belgining balandligi, nuqta (x1 kattalashtirishda) */
const FONT_HEIGHT = { 1: 12, 2: 20, 3: 24, 4: 32, 5: 48 }

/** TSPL belgini ko'pi bilan o'n barobar kattalashtiradi */
const MAX_SCALE = 10

/**
 * Do'kon nomi yorliqning tepa chetidan shuncha pastda, nuqta (3 mm).
 *
 * Avval 1 mm edi va do'kon nomi qog'ozdan chiqib ketardi: printer
 * yorliqni bir-ikki millimetr siljib boshlashi mumkin.
 */
const TOP_MARGIN = 24

/** Nom, o'lcham va narx qatorlari orasidagi bo'shliq, nuqta */
const LINE_GAP = 4

/** Narx bilan shtrix-kod orasidagi bo'shliq, nuqta */
const BARCODE_GAP = 6

/** Javon manzilining shrifti: 5-shrift, x1 da 32×48 nuqta (6 mm baland) */
const SHELF_FONT = 5

/** So'rovda harf balandligi bo'lmasa, mm */
const SHELF_TEXT_MM = 12

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
  const lines = header(settings)

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

    if (label.shopName) put(TOP_MARGIN, 1, label.shopName)

    // Pastda shtrix-kod (ostida raqamlari uchun 40 nuqta)
    const barcodeY = height - settings.barcodeHeight - 40

    // Nom, o'lcham va narx — bir guruh, shtrix-kodning ustida. Pastdan
    // tepaga teriladi: o'lcham bo'lmasa nom narxning ustiga tushadi va
    // orada bo'sh joy qolmaydi
    const block = [
      [2, label.name],
      [1, label.variant],
      [3, label.price],
    ].filter(([font, value]) => fit(value, width, font))

    const rows = []
    let bottom = barcodeY - BARCODE_GAP

    for (const [font, value] of block.reverse()) {
      bottom -= FONT_HEIGHT[font]
      rows.unshift([bottom, font, value])
      bottom -= LINE_GAP
    }

    for (const [y, font, value] of rows) put(y, font, value)

    // Shtrix-kodni printerning o'zi chizadi — rasm yuborilmaydi
    if (label.barcode) {
      const x = centerBarcode(width, settings.barcodeNarrow)

      lines.push(
        `BARCODE ${x},${barcodeY},"EAN13",${settings.barcodeHeight},1,0,` +
          `${settings.barcodeNarrow},${settings.barcodeWide},"${quote(label.barcode)}"`,
      )
    }

    // Nechta dona — shuncha nusxa. Orada FORMFEED yo'q.
    lines.push(`PRINT ${quantity},1`)
  }

  return Buffer.from(`${lines.join('\r\n')}\r\n`, 'latin1')
}

/**
 * Ombor javonlarining yorliqlarini TSPL ga o'giradi.
 *
 * Yorliqda faqat manzil (`A1`) bor va u yorliqning o'rtasida turadi.
 * Harf balandligini so'rov beradi (`textMm`): ko'rinishni o'zgartirish
 * uchun kassadagi agentni yangilash shart bo'lmasin, ilovaning o'zi
 * yetsin.
 *
 * Manzil 5-shriftni butun songa kattalashtirib chiziladi: x1 — 6 mm,
 * x2 — 12 mm va hokazo. O'lchanadigan shriftlar har printer modelida
 * bor emas, kattalashtirishni esa hamma TSPL printer bir xil bajaradi.
 * Yorliqqa sig'masa kichraytiriladi: `A10` eniga sig'masa harflar
 * torroq bo'ladi, pastroq emas — yorliqlar bir xil balandlikda chiqsin.
 *
 * @param {object} job - { widthMm, heightMm, gapMm, textMm, labels: [{ cell, quantity }] }
 * @param {object} options - LABEL_DEFAULTS ustidan yoziladigan qiymatlar
 * @param {string} where - ogohlantirishlarda ko'rsatiladigan printer nomi
 */
export function buildShelfLabels(job, options = {}, where = 'yorliq printeri') {
  const settings = merge(LABEL_DEFAULTS, { ...options, ...clean(job) }, LABEL_RULES, where)
  const lines = header(settings)

  const width = settings.widthMm * DOTS_PER_MM
  const height = settings.heightMm * DOTS_PER_MM

  const textMm = Number(job.textMm) > 0 ? Number(job.textMm) : SHELF_TEXT_MM

  // Balandlik hamma yorliqda bir xil: so'ralgani, lekin yorliqdan oshmasin
  const tall = scale(
    Math.min(
      Math.round((textMm * DOTS_PER_MM) / FONT_HEIGHT[SHELF_FONT]),
      (height - MARGIN * 2) / FONT_HEIGHT[SHELF_FONT],
    ),
  )

  const y = Math.max(MARGIN, Math.round((height - FONT_HEIGHT[SHELF_FONT] * tall) / 2))

  for (const label of job.labels ?? []) {
    const quantity = Math.max(1, Number(label.quantity) || 1)
    const code = quote(label.cell).toUpperCase()
    const charWidth = FONT_WIDTH[SHELF_FONT]

    const wide = scale(Math.min(tall, (width - MARGIN * 2) / (code.length * charWidth)))
    const x = Math.max(MARGIN, Math.round((width - code.length * charWidth * wide) / 2))

    lines.push('CLS')
    lines.push(`TEXT ${x},${y},"${SHELF_FONT}",0,${wide},${tall},"${code}"`)
    lines.push(`PRINT ${quantity},1`)
  }

  return Buffer.from(`${lines.join('\r\n')}\r\n`, 'latin1')
}

/** O'lcham va zichlik — butun ish uchun bir marta beriladi. */
function header(settings) {
  return [
    `SIZE ${settings.widthMm} mm,${settings.heightMm} mm`,
    `GAP ${settings.gapMm} mm,0 mm`,
    'DIRECTION 1',
    'REFERENCE 0,0',
    `DENSITY ${settings.density}`,
    `SPEED ${settings.speed}`,
    'CODEPAGE 1252',
  ]
}

/** Kattalashtirish TSPL ruxsat bergan oraliqda: 1–10 barobar. */
function scale(value) {
  return Math.min(MAX_SCALE, Math.max(1, Math.floor(value)))
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
