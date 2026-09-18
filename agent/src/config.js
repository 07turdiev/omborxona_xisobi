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

  return config
}
