/**
 * Chop etish agenti — ishga tushirish nuqtasi.
 *
 *   node index.js
 *
 * Faqat 127.0.0.1 da tinglaydi: tarmoqdagi boshqa kompyuter bu
 * xizmatga ulana olmaydi.
 */

import { loadConfig } from './src/config.js'
import { createServer, VERSION } from './src/server.js'

const config = loadConfig()
const server = createServer(config)

server.listen(config.port, '127.0.0.1', () => {
  const printers = Object.keys(config.printers)

  console.log(`Chop etish agenti ${VERSION} — http://127.0.0.1:${config.port}`)
  console.log(`Kod sahifasi: ${config.codePage}`)
  console.log(
    printers.length
      ? `Printerlar: ${printers.join(', ')}`
      : 'DIQQAT: printer sozlanmagan (config.json)',
  )
})

server.on('error', (error) => {
  if (error.code === 'EADDRINUSE') {
    console.error(`${config.port} port band — agent allaqachon ishlayaptimi?`)
    process.exit(1)
  }

  throw error
})
