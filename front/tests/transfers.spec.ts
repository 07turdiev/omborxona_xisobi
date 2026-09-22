/**
 * Zalga chiqarish: ombordagi tovarni savdo zaliga ko'chirish.
 *
 * Nega kerak: tovar avval omborga tushadi, sotiladigani javonga
 * chiqariladi. Shu qadam bo'lmasa kassa «zalda yo'q» deb turaveradi.
 */

import { expect, test } from '@playwright/test'

import {
  createTestProduct,
  login,
  openApp,
  stockInWarehouseOnly,
  type Session,
  type TestProduct,
} from './data'

let admin: Session
let product: TestProduct

test.use({ viewport: { width: 1280, height: 900 } })

test.beforeAll(async ({ request }) => {
  admin = await login(request)
  product = await createTestProduct(request, admin)
})

test('ombordagi tovar zalga chiqariladi va hujjat yoziladi', async ({ page, request }) => {
  const hidden = await stockInWarehouseOnly(request, admin, product)

  await openApp(page, admin, '/transfers')

  // Ombordagi tovarlar darhol ko'rinadi — qidirish shart emas
  const card = page.getByRole('button', { name: product.name })

  await expect(card).toBeVisible()
  await card.click()

  const model = page.getByTestId('transfer-model')

  await expect(model).toBeVisible()

  const row = model.locator('tbody tr', { hasText: `${hidden.size} / ${hidden.color}` })

  await expect(row).toContainText('3')

  await row.getByLabel(/nechta chiqariladi/).fill('2')

  await expect(page.getByText('Jami: 2 dona')).toBeVisible()

  // Menyuda ham shu nomdagi band bor — sahifaning o'zidagi tugma
  await page.getByRole('main').getByRole('button', { name: 'Zalga chiqarish' }).click()

  await expect(page.locator('.notice')).toContainText('2 dona zalga chiqarildi')
  await expect(page.locator('.notice')).toContainText('KCH-')

  // Hujjat ro'yxatda ko'rinadi
  const history = page.locator('.table-card').last()

  await expect(history.locator('tbody tr').first()).toContainText('Ombor → Savdo zali')
  await expect(history.locator('tbody tr').first()).toContainText(product.name)
})

test('ombordagi qoldiqdan ortig‘i yozilmaydi', async ({ page, request }) => {
  const other = await createTestProduct(request, admin)
  const hidden = await stockInWarehouseOnly(request, admin, other)

  await openApp(page, admin, '/transfers')

  await page.getByLabel('Tovar nomi').fill(other.name)
  await page.getByRole('button', { name: other.name }).click()

  const row = page
    .getByTestId('transfer-model')
    .locator('tbody tr', { hasText: `${hidden.size} / ${hidden.color}` })

  const input = row.getByLabel(/nechta chiqariladi/)

  await input.fill('99')

  // Omborda 3 dona — shundan ortig'ini yozib bo'lmaydi
  await expect(input).toHaveValue('3')
})
