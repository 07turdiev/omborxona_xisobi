/**
 * Aksiyalar: administrator sahifada e'lon qiladi, kassa narxni o'zi oladi.
 *
 * Zanjir: aksiya yaratiladi → tovar skanerlanadi → savatda aksiya
 * belgisi va arzon narx → sotuv yakunlanadi → chekda aksiya chegirmasi.
 */

import { expect, test } from '@playwright/test'

import { API, createSimpleProduct, login, openApp, type Session } from './data'

let admin: Session

test.beforeAll(async ({ request }) => {
  admin = await login(request)
})

/** Shu testda yaratilgan aksiyalar keyingi testlarning narxiga ta'sir qilmasin */
const created: number[] = []

test.afterAll(async ({ request }) => {
  for (const id of created) {
    await request.patch(`${API}/api/promotions/${id}/`, {
      headers: { Authorization: `Bearer ${admin.access}` },
      data: { is_active: false },
    })
  }
})

test('aksiya sahifada yaratiladi va kassada narx o‘zi arzonlashadi', async ({ page, request }) => {
  const product = await createSimpleProduct(request, admin)
  const name = `Sinov aksiyasi ${Date.now()}`

  await openApp(page, admin, '/products/promotions')

  await page.getByLabel('Nomi').fill(name)
  await page.getByLabel('Chegirma').fill('30')
  await page.getByLabel('Yoki alohida tovarlar').fill(product.name)
  await page.locator('.found').getByRole('button', { name: product.name }).click()

  await expect(page.locator('.chosen-products')).toContainText(product.name)

  const saved = page.waitForResponse(
    (response) =>
      response.url().includes('/api/promotions/') && response.request().method() === 'POST',
  )

  await page.getByRole('button', { name: 'Aksiyani boshlash' }).click()

  created.push((await (await saved).json()).id)

  const row = page.locator('tr', { hasText: name })

  await expect(row).toContainText('−30 %')
  await expect(row).toContainText('Amalda')

  // Kassa: 150 000 so'mlik tovar 30 % arzon — 105 000
  await page.goto('/')

  const field = page.getByPlaceholder('Shtrix-kodni skanerlang')

  await field.fill(product.barcode)
  await field.press('Enter')

  const line = page.locator('.cart-table tbody tr').first()

  await expect(line.locator('.promo-badge')).toHaveText(/Aksiya −30 %/)
  await expect(page.locator('.summary-total')).toContainText(/105\s000/)

  const sale = page.waitForResponse(
    (response) => response.url().endsWith('/api/sales/') && response.request().method() === 'POST',
  )

  await page.getByRole('button', { name: 'Yakunlash' }).click()

  const body = await (await sale).json()

  expect(body.total).toBe('105000.00')
  expect(body.lines[0].promotion_name).toBe(name)
  expect(body.lines[0].promotion_discount).toBe('45000.00')
})

test('to‘xtatilgan aksiya narxga ta‘sir qilmaydi', async ({ page, request }) => {
  const product = await createSimpleProduct(request, admin)
  const today = new Date().toISOString().slice(0, 10)

  const promo = await (
    await request.post(`${API}/api/promotions/`, {
      headers: { Authorization: `Bearer ${admin.access}` },
      data: {
        name: `To‘xtatiladigan ${Date.now()}`,
        percent: '50',
        starts_on: today,
        ends_on: today,
        products: [product.id],
      },
    })
  ).json()

  created.push(promo.id)

  await openApp(page, admin, '/products/promotions')

  page.once('dialog', (dialog) => void dialog.accept())

  await page
    .locator('tr', { hasText: promo.name })
    .getByRole('button', { name: 'Tahrirlash' })
    .click()
  await page.getByRole('button', { name: 'Aksiyani to‘xtatish' }).click()

  await expect(page.locator('tr', { hasText: promo.name })).toContainText('To‘xtatilgan')

  const scanned = await (
    await request.get(`${API}/api/variants/by-barcode/`, {
      headers: { Authorization: `Bearer ${admin.access}` },
      params: { code: product.barcode },
    })
  ).json()

  expect(scanned.promotion).toBeNull()
})
