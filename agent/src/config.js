/**
 * Sozlamalar: `config.json` dan o'qiladi, yo'q bo'lsa standart qiymatlar.
 *
 * Fayl repoga kirmaydi — unda printerning tarmoqdagi manzili bo'ladi.
 * Namuna: `config.example.json`.
 */

import { readFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..')

export const DEFAULTS = {
  port: 7777,
  // Faqat ilovaning o'zi murojaat qila oladi
  origins: ['http://127.0.0.1:5173', 'http://localhost:5173'],
  codePage: 'cp1252',
  printers: {},
}

/** Printer sozlamasida bo'lishi mumkin bo'lgan kalitlar */
const PRINTER_KEYS = [
  'transport',
  'host',
  'port',
  'share',
  'path',
  'timeout',
  'probeTimeout',
  'columns',
  'cashDrawer',
  'feedBeforeCut',
  'cut',
  'barcodeHeight',
  'barcodeWidth',
  'density',
  'speed',
]

/**
 * Noma'lum sozlama nomi haqida ogohlantiradi.
 *
 * Xato yozilgan kalit (masalan `barcodeheight`) jimgina e'tiborsiz
 * qoladi: sozlama yozilgandek ko'rinadi, lekin hech narsaga ta'sir
 * qilmaydi va buni faqat chop etilgan chekdan bilib olish mumkin.
 */
function checkPrinter(name, printer) {
  for (const key of Object.keys(printer ?? {})) {
    if (PRINTER_KEYS.includes(key)) continue

    const similar = PRINTER_KEYS.find((known) => known.toLowerCase() === key.toLowerCase())

    console.warn(
      similar
        ? `config.json: "${name}" printerida "${key}" — "${similar}" bo'lishi kerakmi?`
        : `config.json: "${name}" printerida noma'lum sozlama: "${key}"`,
    )
  }
}

export function loadConfig(path = join(ROOT, 'config.json')) {
  let file = {}

  try {
    file = JSON.parse(readFileSync(path, 'utf8'))
  } catch (error) {
    if (error.code !== 'ENOENT') {
      throw new Error(`config.json o'qilmadi: ${error.message}`)
    }
  }

  const config = { ...DEFAULTS, ...file }

  config.printers = { ...DEFAULTS.printers, ...(file.printers ?? {}) }

  for (const [name, printer] of Object.entries(config.printers)) {
    checkPrinter(name, printer)
  }

  return config
}
