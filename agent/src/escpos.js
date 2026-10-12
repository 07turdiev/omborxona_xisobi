/**
 * Chekni ESC/POS baytlariga o'giradi.
 *
 * ESC/POS — chek printerlarining umumiy tili. Brauzer orqali chop
 * etishdan farqi: chek aynan kerakli uzunlikda chiqadi, qog'oz o'sha
 * yerda kesiladi va hech qanday oyna ochilmaydi.
 */

import { merge } from './settings.js'
import { CODE_PAGES, encode, formatAmount, twoColumns, wrap } from './text.js'

const ESC = 0x1b
const GS = 0x1d

const ALIGN = { left: 0, center: 1, right: 2 }

export const RECEIPT_DEFAULTS = {
  columns: 48,
  codePage: 'cp1252',
  cashDrawer: false,
  /**
   * Kesishdan oldin necha qator tortiladi.
   *
   * Bosh bilan pichoq orasida 80 mm printerlarda odatda 15-20 mm
   * masofa bor. Qog'oz yetarlicha tortilmasa, oxirgi qatorlar
   * pichoqdan pastda qolib, kesilgandan keyin keyingi chekka
   * yopishib chiqadi. 5 qator ~18 mm beradi.
   */
  feedBeforeCut: 5,
  /** 'full' (GS V 0), 'partial' (GS V 1) yoki 'none' */
  cut: 'full',
  /** Shtrix-kod balandligi, nuqta (80 ~ 10 mm) */
  barcodeHeight: 80,
  /** Shtrix-kod modul kengligi (2 ~ 0.25 mm) */
  barcodeWidth: 2,
}

/** Musbat son bo'lishi shart sozlamalar */
const RECEIPT_RULES = {
  positive: ['columns', 'feedBeforeCut', 'barcodeHeight', 'barcodeWidth'],
}

/** A shriftda bitta belgining eni, nuqta: 48 ustun × 12 = 576 nuqta (72 mm) */
const CHAR_DOTS = 12

/** Logotipning eng katta bo'yi, nuqta (50 mm) */
const LOGO_MAX_HEIGHT = 400

/** Buyruqlar va matnni ketma-ket yig'adigan kichik yordamchi. */
class Builder {
  constructor(codePage) {
    this.parts = []
    this.codePage = codePage
  }

  raw(...bytes) {
    this.parts.push(Buffer.from(bytes))
    return this
  }

  text(value) {
    this.parts.push(encode(value, this.codePage))
    return this
  }

  line(value = '') {
    return this.text(value).raw(0x0a)
  }

  align(mode) {
    return this.raw(ESC, 0x61, ALIGN[mode] ?? 0)
  }

  bold(on) {
    return this.raw(ESC, 0x45, on ? 1 : 0)
  }

  /** Ikki barobar balandlik — faqat JAMI uchun */
  doubleHeight(on) {
    return this.raw(GS, 0x21, on ? 0x01 : 0x00)
  }

  feed(lines) {
    return this.raw(ESC, 0x64, lines)
  }

  /** Rasm: `GS v 0` — qatorma-qator nuqtalar, 1 — qora. */
  raster(widthBytes, height, data) {
    this.raw(GS, 0x76, 0x30, 0x00, widthBytes & 0xff, widthBytes >> 8, height & 0xff, height >> 8)
    this.parts.push(data)
    return this
  }

  build() {
    return Buffer.concat(this.parts)
  }
}

/**
 * CODE128 shtrix-kod.
 *
 * `GS k 73 n d1..dn` — printer kodni o'zi chizadi, ya'ni rasm
 * yuborilmaydi va chiziqlar printer nuqtalariga aniq tushadi.
 * Ma'lumot oldiga `{B` qo'yiladi: CODE128 ning B to'plami raqam va
 * harfni ham qabul qiladi.
 */
function barcode(builder, value, height, width) {
  const data = `{B${String(value)}`

  builder
    .raw(GS, 0x68, height) // balandlik, nuqta
    .raw(GS, 0x77, width) // modul kengligi
    .raw(GS, 0x48, 2) // raqamlar kod ostida
    .raw(GS, 0x6b, 73, data.length)
    .text(data)

  return builder
}

/**
 * Chek logotipini tekshiradi va qog'oz eniga markazlab qo'yadi.
 *
 * Logotip bezak: u buzilgan yoki qog'ozga sig'masa ham chek chiqishi
 * shart. Shunday holatda `null` qaytadi va sarlavhada do'kon nomi
 * yoziladi.
 *
 * Markazlash nuqtalarning o'zida qilinadi — chap va o'ngga oq ustunlar
 * qo'shiladi. Rasm uchun `ESC a` ni hamma printer ham hisobga olmaydi.
 *
 * @param {object} logo - { width, height, data } — eni nuqtada (8 ga
 *   karrali), `data` — qatorma-qator baytlar base64 da
 * @param {number} paperDots - qog'ozning bosiladigan eni, nuqta
 */
export function prepareLogo(logo, paperDots) {
  if (!logo || typeof logo !== 'object' || typeof logo.data !== 'string') return null

  const width = Number(logo.width)
  const height = Number(logo.height)

  if (!Number.isInteger(width) || width < 8 || width % 8 !== 0 || width > paperDots) return null
  if (!Number.isInteger(height) || height < 1 || height > LOGO_MAX_HEIGHT) return null

  const source = Buffer.from(logo.data, 'base64')
  const rowBytes = width / 8

  if (source.length !== rowBytes * height) return null

  const paperBytes = Math.floor(paperDots / 8)
  const left = Math.floor((paperBytes - rowBytes) / 2)
  const data = Buffer.alloc(paperBytes * height)

  for (let row = 0; row < height; row += 1) {
    source.copy(data, row * paperBytes + left, row * rowBytes, (row + 1) * rowBytes)
  }

  return { widthBytes: paperBytes, height, data }
}

/** Kesish buyrug'i. */
function cutCommand(builder, mode) {
  if (mode === 'none') return builder
  if (mode === 'partial') return builder.raw(GS, 0x56, 0x01)

  return builder.raw(GS, 0x56, 0x00)
}

/**
 * Chek baytlari.
 *
 * @param {object} receipt - chek ma'lumoti (shopName, number, lines...)
 * @param {object} options - RECEIPT_DEFAULTS ga qarang; yo'q qiymatlar
 *   standart bilan to'ldiriladi
 * @param {string} where - ogohlantirishlarda ko'rsatiladigan printer nomi
 */
export function buildReceipt(receipt, options = {}, where = 'chek printeri') {
  const settings = merge(RECEIPT_DEFAULTS, options, RECEIPT_RULES, where)
  const { columns, codePage } = settings
  const page = CODE_PAGES[codePage] ?? CODE_PAGES.cp1252

  const builder = new Builder(codePage)

  builder
    .raw(ESC, 0x40) // boshlang'ich holat
    .raw(ESC, 0x74, page) // kod sahifasi

  // --- Sarlavha: logotip bo'lsa — u, bo'lmasa do'kon nomi
  const logo = prepareLogo(receipt.logo, columns * CHAR_DOTS)

  builder.align('center')

  if (logo) {
    builder.raster(logo.widthBytes, logo.height, logo.data).line()
  } else {
    builder.bold(true)
    for (const row of wrap(receipt.shopName ?? '', columns)) builder.line(row)
    builder.bold(false)
  }

  if (receipt.dateTime) builder.line(receipt.dateTime)
  if (receipt.number) builder.line(`Chek: ${receipt.number}`)
  if (receipt.cashier) builder.line(`Kassir: ${receipt.cashier}`)

  builder.align('left').line('-'.repeat(columns))

  // --- Qatorlar
  for (const line of receipt.lines ?? []) {
    const title = line.variant ? `${line.name} · ${line.variant}` : String(line.name ?? '')

    for (const row of wrap(title, columns)) builder.line(row)

    const left = `  ${line.quantity} x ${formatAmount(line.unitPrice)}`

    for (const row of twoColumns(left, formatAmount(line.lineTotal), columns)) {
      builder.line(row)
    }
  }

  builder.line('-'.repeat(columns))

  // --- Jami
  if (Number(receipt.discount ?? 0) > 0) {
    for (const row of twoColumns('Chegirma', formatAmount(receipt.discount), columns)) {
      builder.line(row)
    }
  }

  builder.bold(true).doubleHeight(true)
  // Ikki barobar kenglikda ustun soni yarmiga tushadi
  for (const row of twoColumns('JAMI', formatAmount(receipt.total), Math.floor(columns / 2))) {
    builder.line(row)
  }
  builder.doubleHeight(false).bold(false)

  const payments = receipt.payments ?? {}

  if (Number(payments.cash ?? 0) > 0) {
    for (const row of twoColumns('Naqd', formatAmount(payments.cash), columns)) builder.line(row)
  }

  if (Number(payments.card ?? 0) > 0) {
    for (const row of twoColumns('Karta', formatAmount(payments.card), columns)) builder.line(row)
  }

  if (Number(receipt.change ?? 0) > 0) {
    for (const row of twoColumns('Qaytim', formatAmount(receipt.change), columns)) {
      builder.line(row)
    }
  }

  // --- Shtrix-kod
  if (receipt.barcode) {
    builder.line().align('center')
    barcode(builder, receipt.barcode, settings.barcodeHeight, settings.barcodeWidth)
    builder.line()
  }

  if (receipt.footer) {
    builder.align('center')
    for (const row of wrap(receipt.footer, columns)) builder.line(row)
  }

  // --- Yakun
  builder.feed(settings.feedBeforeCut)

  if (settings.cashDrawer) {
    // ESC p 0 t1 t2 — pul qutisini ochadigan impuls
    builder.raw(ESC, 0x70, 0x00, 0x19, 0xfa)
  }

  cutCommand(builder, settings.cut)

  return builder.build()
}
