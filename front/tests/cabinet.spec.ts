/**
 * Ombordagi shkaf: ustunlar harf, qatorlar raqam.
 *
 * Shkaf bitta savolga javob beradi — «tovarni qayerdan olaman?».
 * Shuning uchun testlar ham shu zanjirni tekshiradi: qabulda joy
 * yoziladi, shkaf jadvalida ko'rinadi, zalga chiqarishda esa xodim
 * uni o'qiydi.
 */

import { expect, test, type APIRequestContext } from '@playwright/test'

import {
  API,
  createTestProduct,
  login,
  openApp,
  stockInWarehouseOnly,
  type Session,
  type TestProduct,
} from './data'

let admin: Session
let cashier: Session

test.beforeAll(async ({ request }) => {
  admin = await login(request)
  cashier = await login(request, 'kassir')
})

/**
 * Har testga o'z tovari.
 *
 * Testlar bitta tovarni bo'lishsa, biri qo'ygan katakni ikkinchisi
 * «joyi belgilanmagan» ro'yxatida qidirib topolmay qoladi.
 */
async function ownProduct(request: APIRequestContext): Promise<TestProduct> {
  return createTestProduct(request, admin)
}

/** Tovarga shkafdan joy beradi. */
async function place(request: APIRequestContext, variant: number, cell: string) {
  const response = await request.post(`${API}/api/storage/place/`, {
    headers: { Authorization: `Bearer ${admin.access}` },
    data: { variant, cell },
  })

  expect(response.ok(), `joy belgilanmadi: ${await response.text()}`).toBeTruthy()
}

test('shkaf jadvali ustun harfi va qator raqami bilan chiziladi', async ({ page }) => {
  await openApp(page, admin, '/warehouse')

  const grid = page.locator('.grid')

  await expect(grid).toBeVisible()

  // Standart shkaf 5 × 5: A dan E gacha, 1 dan 5 gacha
  await expect(grid.locator('thead th')).toHaveText(['', 'A', 'B', 'C', 'D', 'E'])
  await expect(grid.locator('tbody tr')).toHaveCount(5)
  await expect(grid.locator('.cell')).toHaveCount(25)
})

test('katakka qo‘yilgan tovar o‘sha katakda ko‘rinadi', async ({ page, request }) => {
  const product = await ownProduct(request)
  const variant = await stockInWarehouseOnly(request, admin, product, 4)

  await place(request, variant.id, 'C3')
  await openApp(page, admin, '/warehouse')

  const cell = page.getByRole('button', { name: /^C3:/ })

  await expect(cell.locator('.cell-count')).toHaveText('4')

  await cell.click()

  // O'ng tomonda katak ichidagi tovarlar
  await expect(page.locator('.chosen-cell')).toContainText(product.name)
  await expect(page.locator('.chosen-cell')).toContainText('4 dona')
})

test('joyi belgilanmagan tovar alohida ro‘yxatda turadi va joylashtiriladi', async ({
  page,
  request,
}) => {
  const product = await ownProduct(request)
  const variant = await stockInWarehouseOnly(request, admin, product, 2)

  await openApp(page, admin, '/warehouse')

  const loose = page.locator('.loose')

  await expect(loose).toContainText(product.name)

  // Ro'yxatdan katak tanlanadi — tovar jadvalga o'tadi
  await loose
    .locator('li', { hasText: product.name })
    .first()
    .locator('select')
    .selectOption('A2')

  await expect(page.getByRole('button', { name: /^A2:/ }).locator('.cell-count')).toHaveText('2')

  // Serverda ham saqlandi
  const stored = await (
    await request.get(`${API}/api/storage/cabinet/`, {
      headers: { Authorization: `Bearer ${admin.access}` },
    })
  ).json()

  expect(stored.cells.A2.some((item: { variant: number }) => item.variant === variant.id)).toBe(
    true,
  )
})

test('zalga chiqarishda tovarning joyi ko‘rinadi', async ({ page, request }) => {
  const product = await ownProduct(request)
  const variant = await stockInWarehouseOnly(request, admin, product, 3)

  await place(request, variant.id, 'D1')
  await openApp(page, admin, '/transfers')

  await page.getByLabel('Tovar nomi').fill(product.name)

  const card = page.locator('.available li', { hasText: product.name }).first()

  await expect(card).toBeVisible()
  await card.locator('button').click()

  // Xodim shkafga borishdan oldin katakni shu yerdan o'qiydi
  await expect(page.getByTestId('transfer-model')).toContainText('D1')
})

test('kassir shkafni ko‘radi, lekin joyini o‘zgartira olmaydi', async ({ page, request }) => {
  const product = await ownProduct(request)
  const variant = await stockInWarehouseOnly(request, admin, product, 1)

  await place(request, variant.id, 'B2')
  await openApp(page, cashier, '/warehouse')

  await page.getByRole('button', { name: /^B2:/ }).click()

  await expect(page.locator('.chosen-cell')).toContainText(product.name)
  await expect(page.locator('.chosen-cell select')).toHaveCount(0)
})

test('shkafda yo‘q katak rad etiladi', async ({ request }) => {
  const product = await ownProduct(request)
  const variant = await stockInWarehouseOnly(request, admin, product, 1)

  const place = async (cell: string) =>
    request.post(`${API}/api/storage/place/`, {
      headers: { Authorization: `Bearer ${admin.access}` },
      data: { variant: variant.id, cell },
    })

  // Harfi bor, lekin besh ustunli shkafdan tashqarida
  const outside = await place('F1')

  expect(outside.status()).toBe(400)
  expect(await outside.text(), 'oxirgi katak aytilishi kerak').toContain('E5')

  // Shakli umuman noto'g'ri
  const wrong = await place('2B')

  expect(wrong.status()).toBe(400)
})
