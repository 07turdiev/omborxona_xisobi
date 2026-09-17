/**
 * Chop etish regressiya testi.
 *
 * Nimani tekshiradi: chop etilgan PDF da **sahifalar soni**, **qog'oz
 * o'lchami** va **chizg'ich uzunligi** to'g'rimi.
 *
 * Nega kerak: ilgari chop etishda ilova qatlami `visibility: hidden`
 * bilan yashirilardi. Yashirilgan element joyni egallaydi, shuning
 * uchun Chromium 40 mm yorliqqa sig'dirish uchun butun chizmani ~66 %
 * ga kichraytirardi va har chop etishda 4 ta bo'sh yorliq chiqarardi.
 * Brauzerdagi o'lchov buni ko'rsatmaydi — faqat PDF ko'rsatadi.
 *
 * Ishga tushirish:  npm run test:print
 * Backend 8004 portda va namuna ma'lumot bilan ishlab turishi kerak.
 */

import { expect, test, type APIRequestContext, type Page } from '@playwright/test'

import { longestRulerMm, readPdf } from './pdf'

const API = process.env.VITE_API_TARGET ?? 'http://127.0.0.1:8004'
const LOGIN = { username: 'admin', password: 'demo12345' }

/** O'lchov bag'rikengligi: qog'oz va chizg'ich uchun ±0.5 mm */
const TOLERANCE = 0.5

/**
 * Millimetrni ±0.5 mm bilan solishtiradi.
 *
 * `toBeCloseTo(80, 1)` ishlatib bo'lmaydi: u "farq 0.05 dan kichik"
 * degani, ya'ni talab qilinganidan o'n barobar qattiq.
 */
function expectMm(actual: number, expected: number, what: string) {
  expect(Math.abs(actual - expected), `${what}: ${actual} mm (kutilgan ${expected} mm)`)
    .toBeLessThanOrEqual(TOLERANCE)
}

let access = ''
let refresh = ''

test.beforeAll(async ({ request }) => {
  const response = await request.post(`${API}/api/auth/login/`, { data: LOGIN })

  expect(response.ok(), 'backend 8004 portda ishlab turishi kerak').toBeTruthy()

  const body = await response.json()

  access = body.access
  refresh = body.refresh
})

/** Tokenlarni brauzerga qo'yadi va chop etishni "to'xtatib" turadi. */
async function openApp(page: Page, path: string) {
  await page.addInitScript(
    ([token, refreshToken]) => {
      localStorage.setItem('access_token', token as string)
      localStorage.setItem('refresh_token', refreshToken as string)

      // `window.print` xato tashlaydi: shunda `printWithPageSize` dagi
      // keyingi qatorlar bajarilmaydi va varaq `body.printing` bilan
      // birga ekranda qoladi — PDF aynan shu holatdan olinadi.
      window.print = () => {
        throw new Error('test: chop etish to‘xtatildi')
      }
    },
    [access, refresh],
  )

  await page.goto(path)
}

/** Chop etish tugmasi bosilgach PDF oladi. */
async function printToPdf(page: Page): Promise<Buffer> {
  await expect(page.locator('body.printing')).toHaveCount(1)
  await expect(page.locator('.print-sheet').first()).toBeVisible()

  return page.pdf({ preferCSSPageSize: true, printBackground: true })
}

/** Ilova qo'ygan `@page` qoidasidagi o'lchamlar. */
async function declaredPageSize(page: Page): Promise<{ width: number; height: number }> {
  const css = await page.locator('#print-page').textContent()
  const match = /size:\s*([\d.]+)mm\s+([\d.]+)mm/.exec(css ?? '')

  expect(match, `@page qoidasi topilmadi: ${css}`).not.toBeNull()

  return { width: Number(match![1]), height: Number(match![2]) }
}

test('sinov yorlig‘i: 1 sahifa, 40×30 mm, chizg‘ich 30 mm', async ({ page }) => {
  await openApp(page, '/settings/devices')

  await page.getByRole('button', { name: /Sinov yorlig/ }).click()

  const pdf = await printToPdf(page)
  const info = await readPdf(pdf)

  expect(info.pages, 'bitta yorliq — bitta sahifa').toBe(1)
  expectMm(info.size.widthMm, 40, 'yorliq eni')
  expectMm(info.size.heightMm, 30, 'yorliq bo‘yi')

  const ruler = await longestRulerMm(pdf)

  console.log(
    `    sinov yorlig‘i: ${info.pages} sahifa, ` +
      `${info.size.widthMm}×${info.size.heightMm} mm, chizg‘ich ${ruler} mm`,
  )

  expect(Math.abs(ruler - 30), `chizg‘ich ${ruler} mm`).toBeLessThanOrEqual(TOLERANCE)
})

test('kirim yorliqlari: 3 dona — 3 sahifa', async ({ page, request }) => {
  const purchase = await createPurchaseWithThreeUnits(request)

  await openApp(page, '/purchases')

  const row = page.locator('tr', { hasText: purchase.number })

  await expect(row).toBeVisible()
  await row.getByRole('button', { name: /Yorliqlar/ }).click()

  const pdf = await printToPdf(page)
  const info = await readPdf(pdf)

  console.log(
    `    kirim yorliqlari: ${info.pages} sahifa, ` +
      `${info.size.widthMm}×${info.size.heightMm} mm`,
  )

  expect(info.pages, '3 dona tovar — 3 ta yorliq').toBe(3)
  expectMm(info.size.widthMm, 40, 'yorliq eni')
  expectMm(info.size.heightMm, 30, 'yorliq bo‘yi')
})

test('sinov cheki: 1 sahifa, 80 mm en, chizg‘ich 50 mm', async ({ page }) => {
  await openApp(page, '/settings/devices')

  await page.getByRole('button', { name: /Sinov cheki/ }).click()

  const pdf = await printToPdf(page)
  const info = await readPdf(pdf)

  expect(info.pages).toBe(1)
  expectMm(info.size.widthMm, 80, 'chek eni')

  const ruler = await longestRulerMm(pdf)

  console.log(
    `    sinov cheki: ${info.pages} sahifa, ` +
      `${info.size.widthMm}×${info.size.heightMm} mm, chizg‘ich ${ruler} mm`,
  )

  expect(Math.abs(ruler - 50), `chizg‘ich ${ruler} mm`).toBeLessThanOrEqual(TOLERANCE)
})

test('haqiqiy chek: 1 sahifa, balandligi mazmunga teng', async ({ page, request }) => {
  const barcode = await firstBarcodeInStock(request)

  await openApp(page, '/')

  await page.getByPlaceholder('Shtrix-kodni skanerlang').fill(barcode)
  await page.getByPlaceholder('Shtrix-kodni skanerlang').press('Enter')

  // Savatda qator paydo bo'lishini kutamiz
  await expect(page.locator('.cart-table tbody tr').first()).toBeVisible()

  await page.getByRole('button', { name: 'Yakunlash' }).click()

  const pdf = await printToPdf(page)
  const info = await readPdf(pdf)
  const declared = await declaredPageSize(page)

  expect(info.pages, 'chek bitta sahifada').toBe(1)
  expectMm(info.size.widthMm, 80, 'chek eni')

  // Qog'oz balandligi ilova hisoblagan balandlikka teng
  expect(Math.abs(info.size.heightMm - declared.height)).toBeLessThanOrEqual(TOLERANCE)

  // Va u chek mazmunidan sezilarli uzun emas — oxirida bo'sh lenta qolmasin
  const contentMm = await page.evaluate(() => {
    const sheet = document.querySelector('.print-sheet.receipt') as HTMLElement | null

    return sheet ? (sheet.scrollHeight / 96) * 25.4 : 0
  })

  console.log(
    `    haqiqiy chek: ${info.pages} sahifa, ` +
      `${info.size.widthMm}×${info.size.heightMm} mm ` +
      `(ilova hisobladi ${declared.width}×${declared.height} mm, ` +
      `mazmun ${Math.round(contentMm * 10) / 10} mm)`,
  )

  expect(contentMm).toBeGreaterThan(0)
  expect(info.size.heightMm - contentMm, 'chek oxirida uzun bo‘sh joy').toBeLessThan(8)
})

// --- Ma'lumot tayyorlash ---------------------------------------------

async function authHeaders() {
  return { Authorization: `Bearer ${access}` }
}

/** Uch dona tovarli tasdiqlangan kirim yaratadi. */
async function createPurchaseWithThreeUnits(request: APIRequestContext) {
  const headers = await authHeaders()

  const categories = await (await request.get(`${API}/api/categories/`, { headers })).json()
  const stamp = Date.now()

  const product = await (
    await request.post(`${API}/api/products/`, {
      headers,
      data: {
        category: categories[0].id,
        name: `Chop etish sinovi ${stamp}`,
        sale_price: '100000',
      },
    })
  ).json()

  const variant = product.variants[0]

  const purchase = await (
    await request.post(`${API}/api/purchases/`, {
      headers,
      data: {
        date: new Date().toISOString().slice(0, 10),
        supplier: null,
        note: 'Chop etish testi',
        lines: [{ variant: variant.id, quantity: 3, unit_cost: '50000' }],
      },
    })
  ).json()

  const confirmed = await request.post(`${API}/api/purchases/${purchase.id}/confirm/`, { headers })

  expect(confirmed.ok(), 'kirim tasdiqlanishi kerak').toBeTruthy()

  return purchase
}

/** Qoldig'i bor birinchi tovarning shtrix-kodi. */
async function firstBarcodeInStock(request: APIRequestContext) {
  const headers = await authHeaders()
  const page = await (await request.get(`${API}/api/variants/`, { headers })).json()

  const variant = page.results.find((item: { stock_quantity: number }) => item.stock_quantity > 0)

  expect(variant, 'qoldig‘i bor tovar kerak — seed_demo ishga tushiring').toBeTruthy()

  return variant.barcode as string
}
