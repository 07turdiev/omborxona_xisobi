/**
 * Ombor javonlari: har devor alohida qator, har qatorda o'z soni.
 *
 * Sahifa bitta savolga javob beradi — «tovarni qayerdan olaman?».
 * Testlar shu zanjirni tekshiradi: qabulda manzil yoziladi, ombor
 * sahifasida ko'rinadi, zalga chiqarishda esa xodim uni o'qiydi.
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

test('har devor alohida qator bo‘lib chiziladi', async ({ page }) => {
  await openApp(page, admin, '/warehouse')

  const runs = page.locator('.run')

  await expect(runs).toHaveCount(5)
  await expect(runs.locator('.run-letter')).toHaveText(['A', 'B', 'C', 'D', 'E'])

  // Devorlarda javonlar soni teng emas: 5, 3, 6, 9, 2
  await expect(runs.nth(1).locator('.shelf')).toHaveCount(3)
  await expect(runs.nth(3).locator('.shelf')).toHaveCount(9)
  await expect(page.locator('.shelf')).toHaveCount(25)
})

test('javonga qo‘yilgan tovar o‘sha javonda ko‘rinadi', async ({ page, request }) => {
  const product = await ownProduct(request)
  const variant = await stockInWarehouseOnly(request, admin, product, 4)

  await place(request, variant.id, 'C3')
  await openApp(page, admin, '/warehouse')

  const shelf = page.getByRole('button', { name: /^C3:/ })

  await expect(shelf.locator('.shelf-count')).toHaveText('4')

  await shelf.click()

  // O'ng tomonda javondagi tovarlar
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

  await expect(page.getByRole('button', { name: /^A2:/ }).locator('.shelf-count')).toHaveText('2')

  // Serverda ham saqlandi
  const stored = await (
    await request.get(`${API}/api/storage/cabinet/`, {
      headers: { Authorization: `Bearer ${admin.access}` },
    })
  ).json()

  const shelf = stored.runs
    .flatMap((run: { shelves: { cell: string; items: { variant: number }[] }[] }) => run.shelves)
    .find((item: { cell: string }) => item.cell === 'A2')

  expect(shelf.items.some((item: { variant: number }) => item.variant === variant.id)).toBe(true)
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

test('omborda yo‘q javon rad etiladi', async ({ request }) => {
  const product = await ownProduct(request)
  const variant = await stockInWarehouseOnly(request, admin, product, 1)

  const put = async (cell: string) =>
    request.post(`${API}/api/storage/place/`, {
      headers: { Authorization: `Bearer ${admin.access}` },
      data: { variant: variant.id, cell },
    })

  // Chap devorda uchta javon bor, to'rtinchisi yo'q
  const tooHigh = await put('B4')

  expect(tooHigh.status()).toBe(400)
  expect(await tooHigh.text(), 'javonlar soni aytilishi kerak').toContain('3 ta javon')

  // Bunday qator umuman yo'q
  const unknown = await put('Z1')

  expect(unknown.status()).toBe(400)

  // Shakli noto'g'ri
  const wrong = await put('2B')

  expect(wrong.status()).toBe(400)
})
