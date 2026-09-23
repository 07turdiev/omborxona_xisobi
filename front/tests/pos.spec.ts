/**
 * Kassa: skanersiz sotish, miqdor tugmalari, tezkor to'lov.
 *
 * Nega kerak: yorliq yirtilgan yoki o'qilmaydigan bo'lsa, kassir
 * skanersiz ham sota olishi kerak edi — ilgari u yo'lda qolardi.
 */

import { expect, test, type Page } from '@playwright/test'

import {
  createSimpleProduct,
  createTestProduct,
  login,
  moveToWarehouse,
  openApp,
  stockInWarehouseOnly,
  type Session,
  type TestProduct,
} from './data'

let admin: Session
let product: TestProduct

// Kassa kompyuteri kengroq: tanlagich yonida turadi
test.use({ viewport: { width: 1440, height: 900 } })

test.beforeAll(async ({ request }) => {
  admin = await login(request)
  product = await createTestProduct(request, admin)
})

/** Chek chop etish oynasi testni to'xtatib qo'ymasin */
async function openPos(page: Page) {
  await page.addInitScript(() => {
    window.print = () => {}
  })

  await openApp(page, admin, '/')
}

/**
 * Tanlagichdan qoldig'i bor birinchi variantni savatga qo'shadi.
 *
 * Aniq songa bog'lanmaydi: shu fayldagi sotuv testi qoldiqni kamaytiradi.
 */
async function addFromPicker(page: Page) {
  const picker = page.locator('.pos-picker')

  await picker.getByRole('searchbox', { name: 'Tovar qidirish' }).fill(product.name)
  await expect(picker.locator('.tile')).toHaveCount(1)
  await picker.locator('.tile').first().click()

  await page.locator('.variant-grid .variant-cell:not([disabled])').first().click()
}

test('tanlagich: plitka → o‘lcham va rang katakchasi → savat', async ({ page }) => {
  await openPos(page)

  const picker = page.locator('.pos-picker')

  await picker.getByRole('searchbox', { name: 'Tovar qidirish' }).fill(product.name)
  await expect(picker.locator('.tile')).toHaveCount(1)
  await picker.locator('.tile').first().click()

  const grid = page.locator('.variant-grid')

  await expect(grid).toBeVisible()

  const available = grid.getByRole('button', {
    name: `${product.sizes[0]!.name} ${product.colors[0]!.name}: 2 dona`,
  })

  const soldOut = grid.getByRole('button', {
    name: `${product.sizes[1]!.name} ${product.colors[0]!.name}: 0 dona`,
  })

  await expect(available).toBeEnabled()
  await expect(soldOut).toBeDisabled()

  // Barmoq uchun katta katak
  expect((await available.boundingBox())!.height).toBeGreaterThanOrEqual(44)

  await available.click()

  const rows = page.locator('.cart-table tbody tr')

  await expect(rows).toHaveCount(1)
  await expect(rows.first()).toContainText(product.name)

  // Fokus skaner maydoniga qaytadi — keyingi tovarni skanerlash mumkin
  await expect(page.locator('.scan-field input')).toBeFocused()
})

test('miqdor tugmalari va "Aniq summa"', async ({ page }) => {
  await openPos(page)
  await addFromPicker(page)

  const row = page.locator('.cart-table tbody tr').first()
  const quantity = row.locator('.cart-number').first()
  const plus = row.getByRole('button', { name: /ko‘paytirish/ })

  expect((await plus.boundingBox())!.height, 'tugma barmoq uchun kichik').toBeGreaterThanOrEqual(40)

  await plus.click()
  await expect(quantity).toHaveValue('2')

  // Qoldiq 2 dona — undan ortig'iga ruxsat yo'q
  await expect(plus).toBeDisabled()

  await row.getByRole('button', { name: /kamaytirish/ }).click()
  await expect(quantity).toHaveValue('1')

  await page.getByRole('button', { name: 'Aniq summa' }).click()
  // Raqamlar uchtadan ajratilgan holda ko'rinadi
  await expect(page.locator('.cash-row input')).toHaveValue(/^250\s000$/)
  await expect(page.locator('.scan-field input')).toBeFocused()
})

test('F4 to‘lov turini, F2 sotuvni, Esc savatni boshqaradi', async ({ page }) => {
  await openPos(page)
  await addFromPicker(page)

  // F4 — to'lov turi
  await page.keyboard.press('F4')
  await expect(page.getByRole('button', { name: 'Karta' })).toHaveClass(/button-gradient/)
  await page.keyboard.press('F4')
  await expect(page.getByRole('button', { name: 'Aralash' })).toHaveClass(/button-gradient/)
  await page.keyboard.press('F4')
  await expect(page.getByRole('button', { name: 'Naqd' })).toHaveClass(/button-gradient/)

  // Esc — savatni tozalaydi
  await page.keyboard.press('Escape')
  await expect(page.locator('.cart-table .empty-state')).toBeVisible()

  // Qayta qo'shib, F2 bilan yakunlaymiz
  await addFromPicker(page)
  await page.locator('.cash-row input').fill('300000')
  await page.keyboard.press('F2')

  const change = page.getByTestId('change-amount')

  await expect(change).toBeVisible()
  await expect(change).toContainText('50 000')

  // Xonaning narigi chetidan ko'rinadigan o'lcham
  const fontSize = await change.evaluate((element) =>
    Number.parseFloat(getComputedStyle(element).fontSize),
  )

  expect(fontSize, 'qaytim kichik yozilgan').toBeGreaterThanOrEqual(40)

  await page.keyboard.press('Escape')

  await expect(change).toHaveCount(0)
  await expect(page.locator('.cart-table .empty-state')).toBeVisible()
  await expect(page.locator('.scan-field input')).toBeFocused()
})

test('zalda qolmagan tovar bir bosishda ombordan olib chiqiladi', async ({ page, request }) => {
  // Alohida mahsulot: boshqa testlardagi qoldiqqa tegmaslik uchun
  const other = await createTestProduct(request, admin)
  const hidden = await stockInWarehouseOnly(request, admin, other)

  await openPos(page)

  const picker = page.locator('.pos-picker')

  await picker.getByRole('searchbox', { name: 'Tovar qidirish' }).fill(other.name)
  await expect(picker.locator('.tile')).toHaveCount(1)
  await picker.locator('.tile').first().click()

  // Katak zalda nol, lekin o'chirilgan emas — ombordagi zaxira ko'rinadi
  const cell = page.getByRole('button', {
    name: `${hidden.size} ${hidden.color}: 0 dona, omborda 3`,
  })

  await expect(cell).toBeEnabled()
  await cell.click()

  const offer = page.getByTestId('from-warehouse')

  await expect(offer).toBeVisible()
  await expect(offer).toContainText('Omborda 3 dona bor')

  // Savatga hali tushmagan: avval ombordan olib chiqiladi
  await expect(page.locator('.cart-table .empty-state')).toBeVisible()

  await offer.getByRole('button', { name: /Ombordan .* olib chiqish/ }).click()

  await expect(offer).toBeHidden()

  const row = page.locator('.cart-table tbody tr')

  await expect(row).toHaveCount(1)
  await expect(row.first()).toContainText(other.name)

  // Ko'chirish hujjati yozildi: ombordan bittasi kamaydi
  await picker.getByRole('searchbox', { name: 'Tovar qidirish' }).fill(other.name)
  await picker.locator('.tile').first().click()

  await expect(
    page.getByRole('button', { name: `${hidden.size} ${hidden.color}: 1 dona, omborda 2` }),
  ).toBeVisible()
})

test('butunlay omborda yotgan tovar kassada ko‘rinmaydi', async ({ page, request }) => {
  const stored = await createTestProduct(request, admin)

  await moveToWarehouse(request, admin, stored)

  await openPos(page)

  const picker = page.locator('.pos-picker')

  await picker.getByRole('searchbox', { name: 'Tovar qidirish' }).fill(stored.name)

  // Javonda yo'q tovar sotuvga tayyor emas — avval zalga chiqariladi
  await expect(picker.locator('.tile')).toHaveCount(0)
  await expect(picker).toContainText('topilmadi')
})

test('ustunlar surilib kengayadi va kenglik eslab qolinadi', async ({ page }) => {
  await openPos(page)

  const picker = page.locator('.pos-picker')
  const handle = page.locator('.pos-resizer').first()

  const before = (await picker.boundingBox())!.width
  const grip = (await handle.boundingBox())!

  await page.mouse.move(grip.x + grip.width / 2, grip.y + grip.height / 2)
  await page.mouse.down()
  await page.mouse.move(grip.x + 120, grip.y + grip.height / 2, { steps: 10 })
  await page.mouse.up()

  const after = (await picker.boundingBox())!.width

  expect(after, 'tanlagich kengaymadi').toBeGreaterThan(before + 80)

  // Kassa kompyuteri har xil — kenglik brauzerda saqlanadi
  await page.reload()
  await expect(picker).toBeVisible()

  const restored = (await picker.boundingBox())!.width

  expect(Math.abs(restored - after), 'kenglik eslab qolinmadi').toBeLessThan(2)
})

test('o‘lchamsiz va rangsiz tovar bir bosishda savatga tushadi', async ({ page, request }) => {
  const ring = await createSimpleProduct(request, admin)

  await openPos(page)

  const picker = page.locator('.pos-picker')

  await picker.getByRole('searchbox', { name: 'Tovar qidirish' }).fill(ring.name)
  await expect(picker.locator('.tile')).toHaveCount(1)

  // Varianti bitta — o'lcham × rang katakchasi umuman ochilmaydi
  await picker.locator('.tile').first().click()

  const row = page.locator('.cart-table tbody tr')

  await expect(row).toHaveCount(1)
  await expect(row.first()).toContainText(ring.name)
  await expect(page.locator('.variant-grid')).toHaveCount(0)
})

test.describe('kassa ekrani 1366×768', () => {
  test.use({ viewport: { width: 1366, height: 768 } })

  test('sahifa surilmaydi, tanlagich yonida turadi', async ({ page }, info) => {
    await openPos(page)
    await addFromPicker(page)

    await expect(page.locator('.pos-picker')).toBeVisible()
    await page.screenshot({ path: info.outputPath('kassa.png') })

    const overflow = await page.evaluate(
      () => document.documentElement.scrollHeight - window.innerHeight,
    )

    expect(overflow, 'kassa ekrani sig‘maydi — sahifa suriladi').toBeLessThanOrEqual(1)

    // Savat ro'yxatining o'zi suriladi
    const scrolls = await page
      .locator('.cart-table-wrap')
      .evaluate((element) => getComputedStyle(element).overflowY)

    expect(scrolls).toBe('auto')
  })
})

test.describe('planshet', () => {
  test.use({ viewport: { width: 820, height: 1180 }, hasTouch: true, isMobile: true })

  test('tanlagich tugma bilan ochiladi va yopiladi', async ({ page }) => {
    await openPos(page)

    const picker = page.locator('.pos-picker')

    await expect(picker).toBeHidden()

    await page.getByRole('button', { name: 'Tovar tanlash' }).tap()
    await expect(picker).toBeVisible()

    await picker.getByRole('button', { name: 'Yopish' }).tap()
    await expect(picker).toBeHidden()
  })
})
