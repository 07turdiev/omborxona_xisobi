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

import { stockedVariants } from './data'
import { firstInkRowMm, longestRulerMm, pageHasInk, readPdf } from './pdf'

/** Backend manzili — `playwright.config.ts` dagi bilan bir xil manba */
const API = process.env.VITE_API_TARGET ?? 'http://127.0.0.1:8000'
const LOGIN = { username: 'admin', password: 'demo12345' }

const HOW_TO_START =
  `Backend ${API} da javob bermayapti.\n\n` +
  '  1) Ishga tushiring:   cd back && .venv/Scripts/python.exe manage.py runserver\n' +
  '  2) Namuna ma’lumot:   .venv/Scripts/python.exe manage.py seed_demo\n' +
  '  3) Boshqa portda bo‘lsa:\n' +
  '     VITE_API_TARGET=http://127.0.0.1:8004 npm run test:print\n'

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
let settings: { receipt_width_mm: number; receipt_page_height_mm: number }

test.beforeAll(async ({ request }) => {
  let response

  try {
    response = await request.post(`${API}/api/auth/login/`, { data: LOGIN })
  } catch {
    throw new Error(HOW_TO_START)
  }

  if (!response.ok()) {
    throw new Error(
      `${HOW_TO_START}\n(server javob berdi, lekin kirish bo‘lmadi: ` +
        `${response.status()} — admin/demo12345 hisobi bormi?)`,
    )
  }

  const body = await response.json()

  access = body.access
  refresh = body.refresh

  // Chek qog'ozi o'lchami sozlamalardan olinadi: test ham, ilova ham
  // bitta manbaga qaraydi
  settings = await (
    await request.get(`${API}/api/settings/`, {
      headers: { Authorization: `Bearer ${access}` },
    })
  ).json()
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

  // Chop etish agenti bu testda qatnashmasligi kerak: u kompyuterda
  // ishlab tursa chek brauzerga emas, to'g'ridan-to'g'ri printerga
  // ketadi va PDF umuman olinmaydi. Agent yo'li `agent.spec.ts` da
  // alohida tekshiriladi.
  await page.route('http://127.0.0.1:7777/**', (route) => route.abort('connectionrefused'))

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

test('begona element qo‘shilsa ham 1 sahifa', async ({ page }) => {
  await openApp(page, '/settings/devices')

  // Ishlab chiqish serverida Vue DevTools <body> ga o'z konteynerlarini
  // qo'shadi va ular bo'sh sahifalar hosil qilardi. Shunga o'xshash
  // baland elementni ataylab qo'shamiz.
  await page.evaluate(() => {
    const intruder = document.createElement('div')

    intruder.id = 'sinov-begona-element'
    // `pointer-events: none` — element tugmani to'smasin. Joylashuvga
    // ta'sir qilmaydi, ya'ni sahifalash uchun xavf o'zgarmaydi.
    intruder.style.cssText =
      'position: fixed; top: 0; left: 0; width: 3000px; height: 5000px;' +
      'background: #000; pointer-events: none'

    document.body.append(intruder)
  })

  await page.getByRole('button', { name: /Sinov yorlig/ }).click()

  const pdf = await printToPdf(page)
  const info = await readPdf(pdf)

  console.log(
    `    begona element bilan: ${info.pages} sahifa, ` +
      `${info.size.widthMm}×${info.size.heightMm} mm`,
  )

  expect(info.pages, 'begona element qo‘shimcha sahifa bermasligi kerak').toBe(1)
  expectMm(info.size.widthMm, 40, 'yorliq eni')
  expectMm(info.size.heightMm, 30, 'yorliq bo‘yi')
})

test('kirim yorliqlari: 3 dona — 3 sahifa', async ({ page, request }) => {
  const purchase = await createPurchaseWithThreeUnits(request)

  await openApp(page, '/purchases')

  const row = page.locator('tr', { hasText: purchase.number })

  await expect(row).toBeVisible()
  await row.click()

  // Yorliqlar hujjatning ichida: ro'yxat qatorida faqat ochish belgisi
  await page.getByTestId('opened-purchase').getByRole('button', { name: /Yorliqlar chop etish/ }).click()

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

/**
 * Yorliq yopishtirishda bir nechtasi yirtiladi, shuning uchun kirim
 * tasdiqlangandan keyin "qo'shimcha yorliq" so'raladi. Qo'shimchalar
 * qatorlar bo'ylab navbat bilan taqsimlanadi.
 */
test('kirim yorliqlari: 3 dona + 2 qo‘shimcha — 5 sahifa', async ({ page, request }) => {
  const purchase = await createPurchaseWithThreeUnits(request, { confirm: false })

  await openApp(page, '/purchases')

  // Qoralama chip orqali formaga yuklanadi va shu yerda tasdiqlanadi
  const chip = page.getByRole('button', { name: new RegExp(`${purchase.number} qoralamasi`) })

  await expect(chip).toBeVisible()
  await chip.click()

  await expect(page.locator('.draft-note')).toContainText(purchase.number)
  await page
    .getByTestId('step-quantities')
    .getByRole('button', { name: 'Qabul qilish' })
    .click()

  const summary = page.getByTestId('purchase-summary')

  await expect(summary.getByTestId('label-count')).toHaveText('3')

  await summary.getByLabel('Qo‘shimcha yorliq').fill('2')
  await expect(summary.getByTestId('label-count')).toHaveText('5')

  await summary.getByRole('button', { name: /Yorliqlarni chop etish/ }).click()

  const pdf = await printToPdf(page)
  const info = await readPdf(pdf)

  console.log(`    qo‘shimcha yorliq: ${info.pages} sahifa`)

  expect(info.pages, '3 dona + 2 qo‘shimcha = 5 yorliq').toBe(5)
})

test('sinov cheki: 1 sahifa, 80 mm en, chizg‘ich 50 mm', async ({ page }) => {
  await openApp(page, '/settings/devices')

  await page.getByRole('button', { name: /Sinov cheki/ }).click()

  const pdf = await printToPdf(page)
  const info = await readPdf(pdf)

  const ruler = await longestRulerMm(pdf)
  const topMm = await firstInkRowMm(pdf)

  console.log(
    `    sinov cheki: ${info.pages} sahifa, ` +
      `${info.size.widthMm}×${info.size.heightMm} mm, chizg‘ich ${ruler} mm, ` +
      `mazmun tepadan ${topMm} mm`,
  )

  expect(info.pages).toBe(1)
  expectMm(info.size.widthMm, settings.receipt_width_mm, 'chek eni')
  expectMm(info.size.heightMm, settings.receipt_page_height_mm, 'chek sahifasi bo‘yi')

  expect(Math.abs(ruler - 50), `chizg‘ich ${ruler} mm`).toBeLessThanOrEqual(TOLERANCE)
  expect(topMm, 'mazmun sahifa tepasidan boshlanishi kerak').toBeLessThanOrEqual(5)
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

  const topMm = await firstInkRowMm(pdf)

  console.log(
    `    haqiqiy chek: ${info.pages} sahifa, ` +
      `${info.size.widthMm}×${info.size.heightMm} mm ` +
      `(ilova @page: ${declared.width}×${declared.height} mm), ` +
      `mazmun tepadan ${topMm} mm`,
  )

  expect(info.pages, 'chek bitta sahifada').toBe(1)

  // Qog'oz o'lchami sozlamadagidek — mazmunga qarab hisoblanmaydi
  expectMm(info.size.widthMm, settings.receipt_width_mm, 'chek eni')
  expectMm(info.size.heightMm, settings.receipt_page_height_mm, 'chek sahifasi bo‘yi')
  expect(declared.width).toBe(settings.receipt_width_mm)
  expect(declared.height).toBe(settings.receipt_page_height_mm)

  expect(topMm, 'mazmun sahifa tepasidan boshlanishi kerak').toBeLessThanOrEqual(5)
})

test('uzun chek: 2 sahifa, mazmun kesilmaydi', async ({ page, request }) => {
  const sale = await createSaleWithManyLines(request)

  await openApp(page, '/receipts')

  const row = page.locator('tr', { hasText: sale.number })

  await expect(row).toBeVisible()
  await row.click()

  await page.getByRole('button', { name: 'Chop etish' }).click()

  const pdf = await printToPdf(page)
  const info = await readPdf(pdf)
  const topMm = await firstInkRowMm(pdf)
  const secondPageHasContent = await pageHasInk(pdf, 2)

  console.log(
    `    uzun chek (${sale.lines.length} qator): ${info.pages} sahifa, ` +
      `${info.size.widthMm}×${info.size.heightMm} mm, ` +
      `2-sahifada mazmun: ${secondPageHasContent ? 'bor' : 'yo‘q'}`,
  )

  expect(info.pages, 'uzun chek ikkinchi sahifaga o‘tadi').toBe(2)
  expectMm(info.size.widthMm, settings.receipt_width_mm, 'chek eni')
  expectMm(info.size.heightMm, settings.receipt_page_height_mm, 'chek sahifasi bo‘yi')

  expect(topMm, 'mazmun sahifa tepasidan boshlanishi kerak').toBeLessThanOrEqual(5)
  expect(secondPageHasContent, 'ikkinchi sahifa bo‘sh bo‘lmasligi kerak').toBe(true)
})

// --- Ma'lumot tayyorlash ---------------------------------------------

async function authHeaders() {
  return { Authorization: `Bearer ${access}` }
}

/** Uch dona tovarli tasdiqlangan kirim yaratadi. */
async function createPurchaseWithThreeUnits(
  request: APIRequestContext,
  { confirm = true } = {},
) {
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

  if (confirm) {
    const confirmed = await request.post(`${API}/api/purchases/${purchase.id}/confirm/`, {
      headers,
    })

    expect(confirmed.ok(), 'kirim tasdiqlanishi kerak').toBeTruthy()
  }

  return purchase
}

/** O'n qatorli sotuv — bitta sahifaga sig'maydi. */
async function createSaleWithManyLines(request: APIRequestContext) {
  const headers = await authHeaders()
  const variants = await stockedVariants(request, API, access, 10)

  const total = variants.reduce(
    (sum: number, item: { price: string }) => sum + Number(item.price),
    0,
  )

  const response = await request.post(`${API}/api/sales/`, {
    headers,
    data: {
      lines: variants.map((item: { id: number }) => ({ variant: item.id, quantity: 1 })),
      cash_amount: total.toFixed(2),
      card_amount: '0.00',
      request_key: crypto.randomUUID(),
    },
  })

  expect(response.ok(), `sotuv yaratilmadi: ${await response.text()}`).toBeTruthy()

  return response.json()
}

/** Qoldig'i bor birinchi tovarning shtrix-kodi. */
async function firstBarcodeInStock(request: APIRequestContext) {
  const [variant] = await stockedVariants(request, API, access, 1)

  return variant!.barcode
}
