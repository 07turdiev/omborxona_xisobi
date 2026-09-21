/**
 * Kirim ro'yxati: qarz va bekor qilish.
 *
 * Ikkita talab qotiriladi:
 *   1. Ta'minotchisiz kirim (boshlang'ich qoldiq) qarz ko'rsatmaydi.
 *   2. Qizil "Bekor" tugmasi qatorda turmaydi — u hujjat ochilganda,
 *      chop etish tugmasidan ajratilgan holda chiqadi.
 */

import { expect, test } from '@playwright/test'

import { createTestProduct, login, openApp, type Session, type TestProduct } from './data'

let admin: Session
let product: TestProduct

test.beforeAll(async ({ request }) => {
  admin = await login(request)
  // Test mahsuloti ta'minotchisiz kirim bilan keladi
  product = await createTestProduct(request, admin)
})

test('ta’minotchisiz kirimda qarz yo‘q, qatorda "Bekor" tugmasi ham yo‘q', async ({ page }) => {
  await openApp(page, admin, '/purchases')

  const row = page.locator('tbody tr', { hasText: product.purchase.number })

  await expect(row).toBeVisible()

  // Ta'minotchi hujjat raqami ostida, qarz esa summa ostida — faqat
  // ta'minotchili va to'lanmagan hujjatda
  await expect(row).toContainText('Ta’minotchisiz')
  await expect(row).not.toContainText('Qarz:')

  await expect(row.getByRole('button', { name: 'Bekor' })).toHaveCount(0)
  await expect(page.locator('tbody .button-danger')).toHaveCount(0)
})

test('kirim ochiladi: chop etish va bekor qilish ajratilgan', async ({ page }) => {
  await openApp(page, admin, '/purchases')

  // Ko'z belgisi ham, qatorning o'zi ham hujjatni ochadi
  await page
    .locator('tbody tr', { hasText: product.purchase.number })
    .getByRole('button', { name: /ochish/ })
    .click()

  const opened = page.getByTestId('opened-purchase')

  await expect(opened).toContainText(product.purchase.number)
  await expect(opened.getByRole('button', { name: /Yorliqlar chop etish/ })).toBeVisible()

  const danger = opened.locator('.danger-zone')

  await expect(danger).toContainText('Tovar ombordan chiqariladi')
  await expect(danger.getByRole('button', { name: 'Bekor qilish' })).toBeVisible()
})
