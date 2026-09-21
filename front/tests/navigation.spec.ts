/**
 * Yangi tuzilma: yon menyu, bo'lim ichidagi tablar, sahifa izohlari.
 *
 * Nega kerak: mijoz eski tuzilmani chalkash deb topdi — 15 ta menyu bandi,
 * bir ma'lumot uch sahifada. Bu test tuzilmaning o'zini qotiradi: menyu
 * yana o'sib ketsa yoki biror sahifa izohsiz qolsa, darhol ko'rinadi.
 */

import { expect, test } from '@playwright/test'

import { createSale, login, openApp, type Session } from './data'

let admin: Session
let cashier: Session

test.beforeAll(async ({ request }) => {
  admin = await login(request)
  cashier = await login(request, 'kassir')
})

test('administrator menyusi: yettita band', async ({ page }) => {
  await openApp(page, admin, '/dashboard')

  await expect(page.locator('.sidebar-menu .menu-item')).toHaveText([
    'Bosh sahifa',
    'Sotish',
    'Tovarlar',
    'Tovar qabul qilish',
    'Sanoq',
    'Hisobot',
    'Sozlamalar',
  ])
})

test('kassir menyusi: uchta band, yopiq sahifadan kassaga qaytariladi', async ({ page }) => {
  await openApp(page, cashier, '/')

  await expect(page.locator('.sidebar-menu .menu-item')).toHaveText([
    'Sotish',
    'Qaytarish',
    'Tovarlar',
  ])

  await page.goto('/purchases')
  await expect(page).toHaveURL(/127\.0\.0\.1:\d+\/$/)
})

/** [manzil, sarlavha, belgilangan menyu bandi] */
const PAGES: [string, string, string][] = [
  ['/', 'Sotish', 'Sotish'],
  ['/returns', 'Qaytarish', 'Sotish'],
  ['/products', 'Tovarlar', 'Tovarlar'],
  ['/products/attributes', 'Tovarlar', 'Tovarlar'],
  ['/dashboard', 'Bosh sahifa', 'Bosh sahifa'],
  ['/purchases', 'Tovar qabul qilish', 'Tovar qabul qilish'],
  ['/suppliers', 'Tovar qabul qilish', 'Tovar qabul qilish'],
  ['/stock-counts', 'Sanoq', 'Sanoq'],
  ['/write-offs', 'Sanoq', 'Sanoq'],
  ['/reports', 'Hisobot', 'Hisobot'],
  ['/reports/stock', 'Hisobot', 'Hisobot'],
  ['/expenses', 'Hisobot', 'Hisobot'],
  ['/receipts', 'Hisobot', 'Hisobot'],
  ['/settings', 'Sozlamalar', 'Sozlamalar'],
  ['/users', 'Sozlamalar', 'Sozlamalar'],
  ['/settings/devices', 'Sozlamalar', 'Sozlamalar'],
]

test('har sahifada sarlavha ostida izoh va to‘g‘ri menyu bandi', async ({ page }) => {
  await openApp(page, admin, '/')

  for (const [path, title, menu] of PAGES) {
    await page.goto(path)

    await expect(page.locator('.page-heading h1'), path).toHaveText(title)
    await expect(page.locator('.menu-item.active'), path).toHaveText(menu)

    const lead = (await page.locator('.page-lead').textContent())?.trim() ?? ''

    expect(lead.length, `${path}: sahifa izohi yo‘q`).toBeGreaterThan(15)
  }
})

test('bo‘lim ichidagi tablar', async ({ page }, info) => {
  await openApp(page, admin, '/suppliers')

  const tabs = page.locator('.page-tab')

  await expect(tabs).toHaveText(['Qabul qilish', 'Ta’minotchilar'])
  await expect(page.locator('.page-tab.active')).toHaveText('Ta’minotchilar')
  await page.screenshot({ path: info.outputPath('tablar.png') })

  await tabs.first().click()
  await expect(page).toHaveURL(/\/purchases$/)

  const groups: [string, string[]][] = [
    ['/stock-counts', ['Sanoq', 'Hisobdan chiqarish']],
    ['/reports', ['Savdo', 'Qoldiq qiymati', 'Xarajatlar', 'Cheklar']],
    ['/settings', ['Do‘kon', 'Xodimlar', 'Qurilmalar']],
    ['/products', ['Tovarlar', 'Kategoriya, o‘lcham, rang']],
  ]

  for (const [path, labels] of groups) {
    await page.goto(path)
    await expect(tabs, path).toHaveText(labels)
  }
})

test('eski manzillar yangisiga olib boradi', async ({ page }) => {
  await openApp(page, admin, '/catalog')
  await expect(page).toHaveURL(/\/products$/)

  await page.goto('/stock')
  await expect(page).toHaveURL(/\/products$/)

  await page.goto('/catalog/1')
  await expect(page).toHaveURL(/\/products\/1$/)
})

test('qoldiq qiymati endi hisobotlarda', async ({ page }) => {
  await openApp(page, admin, '/reports/stock')

  await expect(page.getByTestId('stock-value-kpis').locator('.kpi-card > span')).toHaveText([
    'Pozitsiya',
    'Jami dona',
    'Tannarx bo‘yicha',
    'Sotuv narxida',
    'Kutilayotgan foyda',
  ])
})

test('qaytarish kassadan va cheklardan ochiladi', async ({ page, request }) => {
  const number = await createSale(request, admin)

  await openApp(page, admin, '/')

  await page.getByRole('link', { name: 'Qaytarish yoki almashtirish' }).click()
  await expect(page).toHaveURL(/\/returns$/)

  // Cheklar sahifasi raqam bo'yicha ochiladi, u yerdan chek qaytarishga o'tadi
  await page.goto(`/receipts?number=${number}`)
  await expect(page.locator('.receipt-detail h3')).toHaveText(number)

  await page.getByRole('link', { name: 'Qaytarish / almashtirish' }).click()

  await expect(page).toHaveURL(new RegExp(`/returns\\?number=${number}`))
  await expect(page.getByRole('heading', { name: new RegExp(number) })).toBeVisible()
})

test('kassir ham kassadan qaytarishga o‘tadi', async ({ page }) => {
  await openApp(page, cashier, '/')

  await page.getByRole('link', { name: 'Qaytarish yoki almashtirish' }).click()
  await expect(page).toHaveURL(/\/returns$/)
  await expect(page.locator('.menu-item.active')).toHaveText('Qaytarish')
})
