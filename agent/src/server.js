/**
 * Lokal HTTP xizmat: faqat 127.0.0.1 da tinglaydi.
 *
 * Tarmoqqa chiqmaydi va faqat ilovaning o'z manzilidan kelgan
 * so'rovlarni qabul qiladi (CORS). Boshqa sayt brauzer orqali bu
 * xizmatga murojaat qila olmaydi.
 *
 * Brauzerdan tashqari mijoz (masalan `curl`) uchun `Origin` sarlavhasi
 * bo'lmaydi — u holda sozlamadagi `token` talab qilinadi. Bitta
 * kompyuterdagi oddiy o'rnatmada token shart emas.
 */

import { createServer as createHttpServer } from 'node:http'

import { buildReceipt } from './escpos.js'
import { buildLabels } from './tspl.js'
import { probe, send } from './printer.js'

export const VERSION = '1.1.0'

const MAX_BODY = 512 * 1024
const TOKEN_HEADER = 'x-agent-token'

function readBody(request) {
  return new Promise((resolve, reject) => {
    const chunks = []
    let size = 0

    request.on('data', (chunk) => {
      size += chunk.length

      if (size > MAX_BODY) {
        reject(new Error('so‘rov juda katta'))
        request.destroy()
        return
      }

      chunks.push(chunk)
    })

    request.on('end', () => {
      const raw = Buffer.concat(chunks).toString('utf8')

      if (!raw) {
        resolve({})
        return
      }

      try {
        resolve(JSON.parse(raw))
      } catch {
        reject(new Error('JSON o‘qilmadi'))
      }
    })

    request.on('error', reject)
  })
}

function sendJson(response, status, body, origin) {
  const payload = JSON.stringify(body)

  const headers = {
    'Content-Type': 'application/json; charset=utf-8',
    'Content-Length': Buffer.byteLength(payload),
    'Cache-Control': 'no-store',
  }

  if (origin) {
    headers['Access-Control-Allow-Origin'] = origin
    headers.Vary = 'Origin'
  }

  response.writeHead(status, headers)
  response.end(payload)
}

/** Chek ma'lumotini tekshiradi. Xato bo'lsa — sababi qaytadi. */
export function validateReceipt(data) {
  if (!data || typeof data !== 'object') return 'chek ma’lumoti yo‘q'
  if (!Array.isArray(data.lines) || data.lines.length === 0) return 'chekda qator yo‘q'

  for (const line of data.lines) {
    if (!line || !line.name) return 'qatorda tovar nomi yo‘q'
    if (!Number.isFinite(Number(line.quantity))) return 'qatorda miqdor noto‘g‘ri'
  }

  if (!Number.isFinite(Number(data.total))) return 'jami summa noto‘g‘ri'

  return null
}

/** Yorliqlar ro'yxatini tekshiradi. */
export function validateLabels(data) {
  if (!data || typeof data !== 'object') return 'yorliq ma’lumoti yo‘q'
  if (!Array.isArray(data.labels) || data.labels.length === 0) return 'yorliq ro‘yxati bo‘sh'

  for (const label of data.labels) {
    if (!label || !label.name) return 'yorliqda tovar nomi yo‘q'
    if (!label.barcode) return 'yorliqda shtrix-kod yo‘q'

    const quantity = Number(label.quantity ?? 1)

    if (!Number.isFinite(quantity) || quantity < 1) return 'yorliq soni noto‘g‘ri'
  }

  return null
}

/**
 * Xizmatni yaratadi.
 *
 * `deps` sinov uchun: haqiqiy printerni chaqirmasdan baytlarni
 * tekshirish imkonini beradi.
 */
export function createServer(config, deps = {}) {
  const printBytes = deps.send ?? send
  const probePrinter = deps.probe ?? probe
  const now = deps.now ?? (() => new Date().toISOString())

  const allowed = new Set(config.origins ?? [])
  const token = config.token ?? null

  /** Har printer bo'yicha oxirgi xato — Sozlamalarda ko'rsatiladi */
  const lastErrors = new Map()

  async function printTo(name, bytes) {
    const printer = config.printers?.[name]

    try {
      await printBytes(printer, bytes)
      lastErrors.delete(name)
    } catch (error) {
      lastErrors.set(name, { at: now(), message: error.message })
      throw error
    }
  }

  const server = createHttpServer(async (request, response) => {
    const origin = request.headers.origin
    const hasToken = Boolean(token) && request.headers[TOKEN_HEADER] === token

    const allowedOrigin = origin && allowed.has(origin) ? origin : null

    // Brauzerdan kelgan so'rov faqat ruxsat etilgan manzildan bo'lsin;
    // Origin umuman bo'lmasa (curl, skript) — token talab qilinadi
    if (origin ? !allowedOrigin && !hasToken : !hasToken) {
      sendJson(response, 403, { error: 'bu manzilga ruxsat yo‘q' }, null)
      return
    }

    if (request.method === 'OPTIONS') {
      response.writeHead(204, {
        'Access-Control-Allow-Origin': allowedOrigin ?? '',
        'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
        'Access-Control-Allow-Headers': `Content-Type, ${TOKEN_HEADER}`,
        'Access-Control-Max-Age': '600',
        Vary: 'Origin',
      })
      response.end()
      return
    }

    const url = new URL(request.url, 'http://127.0.0.1')

    // POST so'rovlar faqat JSON qabul qiladi
    if (request.method === 'POST') {
      const type = String(request.headers['content-type'] ?? '')

      if (!type.toLowerCase().startsWith('application/json')) {
        sendJson(response, 415, { error: 'Content-Type: application/json bo‘lishi kerak' }, allowedOrigin)
        return
      }
    }

    try {
      if (request.method === 'GET' && url.pathname === '/health') {
        const names = Object.keys(config.printers ?? {})

        const printers = await Promise.all(
          names.map(async (name) => {
            const printer = config.printers[name]

            return {
              name,
              transport: printer.transport,
              target: printer.host ?? printer.share ?? printer.path ?? null,
              responds: await probePrinter(printer),
              lastError: lastErrors.get(name) ?? null,
            }
          }),
        )

        sendJson(
          response,
          200,
          { version: VERSION, codePage: config.codePage, printers },
          allowedOrigin,
        )
        return
      }

      if (request.method === 'POST' && url.pathname === '/receipt') {
        const data = await readBody(request)
        const problem = validateReceipt(data)

        if (problem) {
          sendJson(response, 400, { error: problem }, allowedOrigin)
          return
        }

        const printer = config.printers?.receipt

        if (!printer) {
          sendJson(response, 503, { error: 'chek printeri sozlanmagan' }, allowedOrigin)
          return
        }

        // Sozlamada yo'q qiymatlar shu yerda `undefined` bo'lib ketadi —
        // ularni `buildReceipt` standart qiymat bilan to'ldiradi
        const bytes = buildReceipt(
          data,
          {
            columns: printer.columns,
            codePage: config.codePage,
            cashDrawer: data.openDrawer ?? printer.cashDrawer ?? false,
            feedBeforeCut: printer.feedBeforeCut,
            cut: printer.cut,
            barcodeHeight: printer.barcodeHeight,
            barcodeWidth: printer.barcodeWidth,
          },
          'chek printeri',
        )

        await printTo('receipt', bytes)

        sendJson(response, 200, { ok: true, bytes: bytes.length }, allowedOrigin)
        return
      }

      if (request.method === 'POST' && url.pathname === '/labels') {
        const data = await readBody(request)
        const problem = validateLabels(data)

        if (problem) {
          sendJson(response, 400, { error: problem }, allowedOrigin)
          return
        }

        const printer = config.printers?.label

        if (!printer) {
          sendJson(response, 503, { error: 'yorliq printeri sozlanmagan' }, allowedOrigin)
          return
        }

        const bytes = buildLabels(
          data,
          {
            density: printer.density,
            speed: printer.speed,
            barcodeHeight: printer.barcodeHeight,
          },
          'yorliq printeri',
        )

        await printTo('label', bytes)

        const count = data.labels.reduce(
          (sum, label) => sum + Math.max(1, Number(label.quantity) || 1),
          0,
        )

        sendJson(response, 200, { ok: true, labels: count, bytes: bytes.length }, allowedOrigin)
        return
      }

      sendJson(response, 404, { error: 'bunday manzil yo‘q' }, allowedOrigin)
    } catch (error) {
      sendJson(response, 500, { error: error.message }, allowedOrigin)
    }
  })

  return server
}
