/**
 * Birlashtirilgan mahsulotlar sahifasi (kompyuter ekrani).
 *
 * Ilgari katalog, mahsulotlar va qoldiq — uchta alohida sahifa edi. Endi
 * bitta ro'yxat va bitta mahsulot sahifasi: administrator uchun amallar
 * (tahrirlash, yorliq, hisobdan chiqarish, qoldiq tarixi) shu yerda,
 * kassir esa o'sha sahifani tannarx va amallarsiz ko'radi.
 */

import { expect, test, type Page } from '@playwright/test'

import {
  createTestProduct,
  login,
  moveToWarehouse,
  openApp,
  type Session,
  type TestProduct,
} from './data'

let admin: Session
let cashier: Session
let product: TestProduct

test.beforeAll(async ({ request }) => {
  admin = await login(request)
  cashier = await login(request, 'kassir')
  product = await createTestProduct(request, admin)
})

/** Variantlar jadvalidagi qator: "O'lcham / Rang" */
function variantRow(page: Page, size: number, color: number) {
  const label = `${product.sizes[size]!.name} / ${product.colors[color]!.name}`

  return page.getByTestId('variants').locator('tbody tr', { hasText: label })
}

test('administrator: ixcham jadval', async ({ page }) => {
  await openApp(page, admin, '/products')

  await page.getByRole('button', { name: 'Jadval' }).click()

  const table = page.locator('.product-table')

  await expect(table).toBeVisible()
  await expect(table.locator('th')).toContainText(['Nomi', 'Narxi', 'O‘lchamlar', 'Qoldiq'])

  await page.getByRole('searchbox', { name: 'Mahsulot qidirish' }).fill(product.name)

  const rows = table.locator('tbody tr')

  await expect(rows).toHaveCount(1)

  // Jami 8, hammasi zalda — kirim qabul qilingandan keyin chiqarilgan
  const stock = rows.first().locator('td').nth(4)

  await expect(stock).toContainText('8')
  await expect(stock).toContainText('zal 8 · ombor 0')

  await rows.first().click()
  await expect(page).toHaveURL(new RegExp(`/products/${product.id}$`))
})

test('joy filtri: zaldagi va ombordagi tovar alohida ko‘rinadi', async ({ page, request }) => {
  const hidden = await createTestProduct(request, admin)

  // Bu tovarning hammasi omborda qoladi
  await moveToWarehouse(request, admin, hidden)

  await openApp(page, admin, '/products')

  const search = page.getByRole('searchbox', { name: 'Mahsulot qidirish' })
  const cards = page.locator('.product-card')

  await search.fill(hidden.name)
  await expect(cards).toHaveCount(1)

  await page.getByLabel('Joy').selectOption('warehouse')
  await expect(cards).toHaveCount(1)

  await page.getByLabel('Joy').selectOption('shop')
  await expect(cards).toHaveCount(0)
})

test('administrator: amallar va qoldiq tarixi hujjatga olib boradi', async ({ page }, info) => {
  await openApp(page, admin, `/products/${product.id}`)

  await expect(page.getByRole('button', { name: 'Tahrirlash' })).toBeVisible()
  await expect(page.getByRole('button', { name: /yorliq/i })).toBeVisible()
  await expect(page.getByRole('button', { name: 'Hisobdan chiqarish' })).toBeVisible()

  const headers = await page.getByTestId('variants').locator('th').allTextContents()

  expect(headers.map((text) => text.trim())).toContain('Tannarx')

  // Jadvaldagi qator tanlanadi — tarix shu variant bo'yicha
  await variantRow(page, 2, 0).click()

  const history = page.getByTestId('stock-history')
  const link = history.getByRole('link', { name: product.purchase.number })

  await expect(link).toBeVisible()
  await expect(history.locator('tbody tr').first()).toContainText('+5')

  await page.screenshot({ path: info.outputPath('mahsulot-sahifasi.png'), fullPage: true })

  await link.click()

  await expect(page).toHaveURL(new RegExp(`/purchases\\?open=${product.purchase.id}$`))
  await expect(page.getByTestId('opened-purchase')).toContainText(product.purchase.number)
})

test('yorliq soni so‘raladi: bo‘sh qoldirilsa qoldiq bo‘yicha chiqadi', async ({ page }) => {
  await openApp(page, admin, `/products/${product.id}`)

  // Bitta variant tanlanadi: uning qoldig'i 2 dona
  await variantRow(page, 0, 0).click()
  await page.getByRole('button', { name: /yorliq/i }).click()

  const dialog = page.getByTestId('label-dialog')
  const total = dialog.getByTestId('label-total')

  await expect(dialog).toBeVisible()

  // Boshida qoldiq turadi: bu variantda 2 dona
  await expect(total).toHaveText('2')

  // Yozilgan son — aynan shuncha yorliq, ko'paytirilmaydi
  const label = `${product.sizes[0]!.name} / ${product.colors[0]!.name}`

  await dialog.getByLabel(`${label}: nechta`).fill('5')
  await expect(total).toHaveText('5')

  await dialog.getByRole('button', { name: 'Bekor qilish' }).click()
  await expect(dialog).toHaveCount(0)
})

test('administrator: hisobdan chiqarish qoldiqni kamaytiradi', async ({ page }) => {
  await openApp(page, admin, `/products/${product.id}`)

  const row = variantRow(page, 0, 0)

  await row.click()
  await expect(row.locator('td').nth(3)).toContainText('zal 2 · ombor 0')

  await page.getByRole('button', { name: 'Hisobdan chiqarish' }).click()

  const dialog = page.getByRole('dialog', { name: 'Hisobdan chiqarish' })

  await dialog.getByPlaceholder('Yaroqsiz, yo‘qolgan…').fill('Sinov: yirtilgan')
  await dialog.getByRole('button', { name: 'Hisobdan chiqarish' }).click()

  await expect(dialog).toHaveCount(0)
  await expect(row.locator('td').nth(3)).toContainText('zal 1 · ombor 0')
  await expect(page.getByTestId('stock-history')).toContainText('Hisobdan chiqarish')
})

test('kassir: o‘sha sahifa, lekin tannarx va amallarsiz', async ({ page }) => {
  await openApp(page, cashier, `/products/${product.id}`)

  await expect(page.getByRole('heading', { name: product.name })).toBeVisible()
  await expect(page.locator('.swatch')).toHaveCount(2)
  await expect(page.getByTestId('variants')).toBeVisible()

  await expect(page.getByRole('button', { name: 'Tahrirlash' })).toHaveCount(0)
  await expect(page.getByRole('button', { name: 'Hisobdan chiqarish' })).toHaveCount(0)
  await expect(page.getByTestId('stock-history')).toHaveCount(0)

  const headers = await page.getByTestId('variants').locator('th').allTextContents()

  expect(headers.map((text) => text.trim())).not.toContain('Tannarx')

  // Ro'yxatda ham administrator vositalari yo'q
  await page.goto('/products')

  await expect(page.locator('.product-card').first()).toBeVisible()
  await expect(page.getByRole('button', { name: 'Jadval' })).toHaveCount(0)
  await expect(page.getByRole('button', { name: /Yangi mahsulot/ })).toHaveCount(0)
})

test('boshqaruv panelidan tugayotganlar ro‘yxatiga', async ({ page }) => {
  await openApp(page, admin, '/dashboard')

  await page.getByRole('link', { name: 'Tugayotganlarni ko‘rish' }).click()

  await expect(page).toHaveURL(/\/products$/)
  await expect(page.locator('.check', { hasText: 'Tugayotganlar' }).locator('input')).toBeChecked()
})
