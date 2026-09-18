/**
 * Chop etish agenti bilan integratsiya testi.
 *
 * Nimani tekshiradi: agent ishlayotganda chek **brauzer oynasisiz**
 * ketadimi va agent yo'q bo'lganda ilova jimgina brauzer orqali chop
 * etishga qaytadimi.
 *
 * Nega kerak: agent yo'li butunlay boshqa (fetch → 127.0.0.1:7777), va
 * uning eng muhim sharti — kassirning ishini to'xtatmaslik. Agent
 * o'chirilgan bo'lsa ham sotuv yakunlanib, chek chiqishi kerak.
 *
 * Agentning o'zi bu yerda ishga tushirilmaydi: uning javoblari
 * Playwright orqali qo'yiladi, shunda test har qanday kompyuterda
 * bir xil ishlaydi.
 *
 * Ishga tushirish:  npm run test:print
 */

import { expect, test, type APIRequestContext, type Page } from '@playwright/test'

const API = process.env.VITE_API_TARGET ?? 'http://127.0.0.1:8000'
const AGENT = 'http://127.0.0.1:7777'
const LOGIN = { username: 'admin', password: 'demo12345' }

const HEALTH = {
  version: '1.1.0',
  codePage: 'cp1252',
  printers: [
    { name: 'receipt', transport: 'tcp', target: '192.0.2.10', responds: true, lastError: null },
    {
      name: 'label',
      transport: 'windows',
      target: '\\\\127.0.0.1\\XP365B',
      responds: false,
      lastError: { at: '2026-09-18T10:00:00.000Z', message: 'ulanib bo‘lmadi' },
    },
  ],
}

/** Brauzer boshqa manzilga so'rov yuborishi uchun CORS sarlavhalari */
const CORS = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
  'Access-Control-Allow-Headers': 'Content-Type, x-agent-token',
}

let access = ''
let refresh = ''

test.beforeAll(async ({ request }) => {
  const response = await request.post(`${API}/api/auth/login/`, { data: LOGIN })

  expect(response.ok(), `Backend ${API} da kirish bo‘lmadi — seed_demo ishga tushirilganmi?`)
    .toBeTruthy()

  const body = await response.json()

  access = body.access
  refresh = body.refresh
})

/**
 * Ilovani ochadi va `window.print` chaqiruvlarini sanaydi.
 *
 * Chaqiruv xato tashlaydi — shunda brauzer yo'li haqiqiy chop etish
 * oynasini ochmaydi, lekin sanoq oshib qoladi.
 */
async function openApp(page: Page, path: string) {
  await page.addInitScript(
    ([token, refreshToken]) => {
      localStorage.setItem('access_token', token as string)
      localStorage.setItem('refresh_token', refreshToken as string)

      const counter = window as unknown as { printCalls: number }

      counter.printCalls = 0

      window.print = () => {
        counter.printCalls += 1
        throw new Error('test: chop etish to‘xtatildi')
      }
    },
    [access, refresh],
  )

  await page.goto(path)
}

function printCalls(page: Page) {
  return page.evaluate(() => (window as unknown as { printCalls: number }).printCalls)
}

/** Agent o'chirilgan: ulanish rad etiladi. */
async function agentOffline(page: Page) {
  await page.route(`${AGENT}/**`, (route) => route.abort('connectionrefused'))
}

/** Agent ishlayapti. Qaytgan ro'yxatga yuborilgan so'rovlar tushadi. */
async function agentOnline(page: Page) {
  const sent: { path: string; body: unknown }[] = []

  await page.route(`${AGENT}/**`, async (route) => {
    const request = route.request()
    const path = new URL(request.url()).pathname

    if (request.method() === 'OPTIONS') {
      await route.fulfill({ status: 204, headers: CORS })
      return
    }

    const json = (status: number, body: unknown) =>
      route.fulfill({
        status,
        headers: { ...CORS, 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      })

    if (path === '/health') {
      await json(200, HEALTH)
      return
    }

    sent.push({ path, body: request.postDataJSON() })

    await json(200, { ok: true })
  })

  return sent
}

/** Savatga bitta tovar qo'shib, sotuvni yakunlaydi. */
async function completeSale(page: Page, barcode: string) {
  const field = page.getByPlaceholder('Shtrix-kodni skanerlang')

  await field.fill(barcode)
  await field.press('Enter')

  await expect(page.locator('.cart-table tbody tr').first()).toBeVisible()
  await page.getByRole('button', { name: 'Yakunlash' }).click()
}

test('agent yo‘q bo‘lsa chek brauzer orqali chiqadi', async ({ page, request }) => {
  await agentOffline(page)

  const barcode = await firstBarcodeInStock(request)

  await openApp(page, '/')
  await completeSale(page, barcode)

  // Brauzer yo'li: varaq ekranga chiqadi va `window.print` chaqiriladi
  await expect(page.locator('.print-sheet.receipt')).toBeVisible()

  expect(await printCalls(page), 'agent yo‘q — brauzer chop etishi kerak').toBeGreaterThan(0)
})

test('agent ishlasa brauzer oynasi ochilmaydi', async ({ page, request }) => {
  const sent = await agentOnline(page)

  const barcode = await firstBarcodeInStock(request)

  await openApp(page, '/')
  await completeSale(page, barcode)

  await expect(page.locator('.toast')).toContainText('printerga yuborildi')

  expect(await printCalls(page), 'agent chop etdi — brauzer oynasi ochilmasligi kerak').toBe(0)

  const receipts = sent.filter((item) => item.path === '/receipt')

  expect(receipts, 'chek agentga yuborilishi kerak').toHaveLength(1)

  const receipt = receipts[0]!.body as { lines: unknown[]; barcode: string; total: string }

  expect(receipt.lines.length).toBeGreaterThan(0)
  expect(receipt.barcode, 'chek kodi faqat raqam').toMatch(/^\d+$/)

  console.log(`    agent orqali chek: ${receipts.length} ta so‘rov, jami ${receipt.total}`)
})

test('qurilmalar sahifasida agent holati ko‘rinadi', async ({ page }) => {
  await agentOnline(page)

  await openApp(page, '/settings/devices')

  const card = page.locator('.agent-card')

  await expect(card).toContainText('Agent ishlayapti')
  await expect(card).toContainText(HEALTH.version)

  // Printerning oxirgi xatosi ham ko'rinishi kerak — Sozlamalardan
  // nima uchun chop etilmaganini bilish uchun
  await expect(card).toContainText('ulanib bo‘lmadi')
})

test('agent orqali sinov yorlig‘i yuboriladi', async ({ page }) => {
  const sent = await agentOnline(page)

  await openApp(page, '/settings/devices')

  await page.getByRole('button', { name: /Agent orqali sinov yorlig/ }).click()

  await expect(page.locator('.toast')).toBeVisible()

  const labels = sent.filter((item) => item.path === '/labels')

  expect(labels, 'yorliq agentga yuborilishi kerak').toHaveLength(1)

  expect(await printCalls(page), 'brauzer oynasi ochilmasligi kerak').toBe(0)
})

/** Qoldig'i bor birinchi tovarning shtrix-kodi. */
async function firstBarcodeInStock(request: APIRequestContext) {
  const response = await request.get(`${API}/api/variants/`, {
    headers: { Authorization: `Bearer ${access}` },
  })

  const page = await response.json()
  const variant = page.results.find((item: { stock_quantity: number }) => item.stock_quantity > 0)

  expect(variant, 'qoldig‘i bor tovar kerak — seed_demo ishga tushiring').toBeTruthy()

  return variant.barcode as string
}
