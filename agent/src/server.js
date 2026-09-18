/**
 * Lokal HTTP xizmat: faqat 127.0.0.1 da tinglaydi.
 *
 * Tarmoqqa chiqmaydi va faqat ilovaning o'z manzilidan kelgan
 * so'rovlarni qabul qiladi (CORS). Boshqa sayt brauzer orqali bu
 * xizmatga murojaat qila olmaydi.
 */

import { createServer as createHttpServer } from 'node:http'

import { buildReceipt } from './escpos.js'
import { probe, send } from './printer.js'

export const VERSION = '1.0.0'

const MAX_BODY = 512 * 1024

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

/**
 * Xizmatni yaratadi.
 *
 * `deps` sinov uchun: haqiqiy printerni chaqirmasdan baytlarni
 * tekshirish imkonini beradi.
 */
export function createServer(config, deps = {}) {
  const printBytes = deps.send ?? send
  const probePrinter = deps.probe ?? probe

  const allowed = new Set(config.origins ?? [])

  const server = createHttpServer(async (request, response) => {
    const origin = request.headers.origin
    const allowedOrigin = origin && allowed.has(origin) ? origin : null

    // Boshqa saytdan kelgan so'rov — rad etiladi
    if (origin && !allowedOrigin) {
      sendJson(response, 403, { error: 'bu manzilga ruxsat yo‘q' }, null)
      return
    }

    if (request.method === 'OPTIONS') {
      response.writeHead(204, {
        'Access-Control-Allow-Origin': allowedOrigin ?? '',
        'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
        'Access-Control-Allow-Headers': 'Content-Type',
        'Access-Control-Max-Age': '600',
        Vary: 'Origin',
      })
      response.end()
      return
    }

    const url = new URL(request.url, 'http://127.0.0.1')

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
            }
          }),
        )

        sendJson(response, 200, { version: VERSION, codePage: config.codePage, printers }, allowedOrigin)
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

        const bytes = buildReceipt(data, {
          columns: printer.columns ?? 48,
          codePage: config.codePage,
          cashDrawer: data.openDrawer ?? printer.cashDrawer ?? false,
        })

        await printBytes(printer, bytes)

        sendJson(response, 200, { ok: true, bytes: bytes.length }, allowedOrigin)
        return
      }

      sendJson(response, 404, { error: 'bunday manzil yo‘q' }, allowedOrigin)
    } catch (error) {
      sendJson(response, 500, { error: error.message }, allowedOrigin)
    }
  })

  return server
}
