/**
 * UI testlarini **alohida bazada** yurgizadi.
 *
 * Playwright testlari ilovaga haqiqiy so'rovlar yuboradi va mahsulot,
 * kirim, sotuv yaratadi. Ilgari ular ishlab chiqish backendiga
 * ulanardi va sinov ma'lumoti haqiqiy ro'yxatlarga tushib qolardi.
 *
 * Bu skript:
 *   1. ishlab chiqish bazasining nomiga `_test_ui` qo'shib, alohida
 *      bazani qaytadan yaratadi (migratsiya + namuna ma'lumot);
 *   2. ilovani quradi;
 *   3. backendni o'z portida ko'taradi (standart 8010);
 *   4. Playwright'ni o'sha backendga qarshi yurgizadi va serverni yopadi.
 *
 *   npm run test:ui                  — hamma UI testlari
 *   npm run test:ui tests/pos.spec.ts — bittasi
 *
 * Foydalanuvchi va parol ishlab chiqish sozlamasidan olinadi, hech
 * qayerga yozilmaydi. Boshqa bazaga ulanish kerak bo'lsa:
 *   UI_TEST_DATABASE_URL=postgres://…/dokon_test_ui npm run test:ui
 */

import { spawn, spawnSync } from 'node:child_process'
import { existsSync, readFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

const FRONT = dirname(dirname(fileURLToPath(import.meta.url)))
const BACK = join(dirname(FRONT), 'back')
const MANAGE = join(BACK, 'manage.py')

const PORT = process.env.UI_TEST_PORT ?? '8010'

const PYTHON =
  [join(BACK, '.venv', 'Scripts', 'python.exe'), join(BACK, '.venv', 'bin', 'python')].find(
    (candidate) => existsSync(candidate),
  ) ?? 'python'

// `npm` va `npx` o'rniga ularning JS kirish nuqtalari Node bilan
// chaqiriladi: Windows'da ham, Git Bash'da ham bir xil ishlaydi va
// qobiq (shell) kerak bo'lmaydi
const VITE = join(FRONT, 'node_modules', 'vite', 'bin', 'vite.js')
const PLAYWRIGHT = join(FRONT, 'node_modules', '@playwright', 'test', 'cli.js')

function fail(message) {
  console.error(`\n${message}\n`)
  process.exit(1)
}

/** `back/.env` dagi ishlab chiqish bazasi manzili */
function developmentDatabaseUrl() {
  const file = join(BACK, '.env')

  if (!existsSync(file)) fail('back/.env topilmadi — avval uni .env.example dan yarating.')

  const match = /^DATABASE_URL=(.+)$/m.exec(readFileSync(file, 'utf8'))

  if (!match) fail('back/.env da DATABASE_URL yo‘q.')

  return match[1].trim()
}

/** Test bazasi: o'sha server va foydalanuvchi, lekin boshqa baza. */
function testDatabaseUrl() {
  const explicit = process.env.UI_TEST_DATABASE_URL
  const url = new URL(explicit ?? developmentDatabaseUrl())

  if (!explicit) url.pathname = `${url.pathname}_test_ui`

  // Ikkinchi himoya (birinchisi — `reset_test_db` buyrug'ida)
  if (!url.pathname.includes('test')) {
    fail(`«${url.pathname.slice(1)}» test bazasi emas — nomida "test" bo‘lishi kerak.`)
  }

  return url.toString()
}

function run(command, args, options = {}) {
  const result = spawnSync(command, args, { stdio: 'inherit', ...options })

  if (result.error) fail(`${command} ishga tushmadi: ${result.error.message}`)

  if (result.status !== 0) process.exit(result.status ?? 1)

  return result
}

async function waitForBackend(url) {
  const deadline = Date.now() + 40_000

  while (Date.now() < deadline) {
    try {
      // Har qanday javob yetarli: 401 ham server ko'tarilganini bildiradi
      await fetch(url)
      return
    } catch {
      await new Promise((done) => setTimeout(done, 250))
    }
  }

  fail(`Backend ${url} da ko‘tarilmadi.`)
}

const databaseUrl = testDatabaseUrl()
const database = new URL(databaseUrl).pathname.slice(1)

const env = { ...process.env, DATABASE_URL: databaseUrl, UI_TEST: '1' }

console.log(`\n[1/4] Test bazasi: ${database}`)
run(PYTHON, [MANAGE, 'reset_test_db'], { cwd: BACK, env })

console.log('\n[2/4] Ilova qurilmoqda')
run(process.execPath, [VITE, 'build'], { cwd: FRONT, env })

console.log(`\n[3/4] Backend: http://127.0.0.1:${PORT}`)
const server = spawn(PYTHON, [MANAGE, 'runserver', `127.0.0.1:${PORT}`, '--noreload'], {
  cwd: BACK,
  env,
  stdio: 'ignore',
})

server.on('error', (error) => fail(`Backendni ishga tushirib bo‘lmadi: ${error.message}`))

await waitForBackend(`http://127.0.0.1:${PORT}/api/catalog/`)

console.log('\n[4/4] Playwright\n')
const tests = spawnSync(process.execPath, [PLAYWRIGHT, 'test', ...process.argv.slice(2)], {
  cwd: FRONT,
  env: { ...env, VITE_API_TARGET: `http://127.0.0.1:${PORT}` },
  stdio: 'inherit',
})

server.kill()

process.exit(tests.status ?? 1)
