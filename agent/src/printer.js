/**
 * Printerga ulanish: TCP (tarmoqdagi printer) yoki Windows'dagi
 * umumiy papka (USB printer "share" qilingan bo'lsa).
 *
 * Har ikkalasiga ham **tayyor baytlar** yuboriladi: drayver ham,
 * brauzer ham aralashmaydi.
 */

import { createConnection } from 'node:net'
import { access, writeFile } from 'node:fs/promises'
import { constants } from 'node:fs'

const CONNECT_TIMEOUT = 3000
const PROBE_TIMEOUT = 250

/** Baytlarni TCP orqali yuboradi (odatda 9100-port). */
function sendTcp(printer, bytes) {
  return new Promise((resolve, reject) => {
    const socket = createConnection({
      host: printer.host,
      port: printer.port ?? 9100,
    })

    const fail = (error) => {
      socket.destroy()
      reject(error)
    }

    socket.setTimeout(printer.timeout ?? CONNECT_TIMEOUT)
    socket.on('timeout', () => fail(new Error('printer javob bermadi (timeout)')))
    socket.on('error', fail)

    socket.on('connect', () => {
      socket.write(bytes, () => socket.end())
    })

    socket.on('close', resolve)
  })
}

/**
 * Windows'da umumiy qilingan printerga yozadi.
 *
 * USB printer `\\127.0.0.1\NOM` ko'rinishida ochiladi va unga oddiy
 * fayl kabi yozish mumkin — shunda baytlar drayverdan o'tmasdan
 * to'g'ridan-to'g'ri printerga boradi.
 */
async function sendWindows(printer, bytes) {
  await writeFile(printer.share, bytes)
}

/** Sinov uchun: baytlarni faylga yozadi. */
async function sendFile(printer, bytes) {
  await writeFile(printer.path, bytes)
}

const TRANSPORTS = {
  tcp: sendTcp,
  windows: sendWindows,
  file: sendFile,
}

/** Printerga baytlarni yuboradi. */
export async function send(printer, bytes) {
  const transport = TRANSPORTS[printer?.transport]

  if (!transport) {
    throw new Error(`noma'lum ulanish turi: ${printer?.transport}`)
  }

  await transport(printer, bytes)
}

/** Printer javob beradimi — tez tekshiruv (chop etmasdan). */
export function probe(printer) {
  if (printer?.transport === 'tcp') {
    return new Promise((resolve) => {
      const socket = createConnection({ host: printer.host, port: printer.port ?? 9100 })

      const finish = (ok) => {
        socket.destroy()
        resolve(ok)
      }

      socket.setTimeout(printer.probeTimeout ?? PROBE_TIMEOUT)
      socket.on('timeout', () => finish(false))
      socket.on('error', () => finish(false))
      socket.on('connect', () => finish(true))
    })
  }

  const target = printer?.share ?? printer?.path

  if (!target) return Promise.resolve(false)

  return access(target, constants.W_OK).then(
    () => true,
    () => false,
  )
}
