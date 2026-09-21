/**
 * Kirim ekrani: tovar shtrix-kodsiz keladi.
 *
 * Do'konga kelgan model yo umuman yangi bo'ladi, yo yorlig'i yo'q.
 * Shuning uchun kirim ekranida: nom bo'yicha qidiruv, o'sha yerda
 * yangi mahsulot yaratish va o'lcham × rang katakchasi bo'lishi kerak.
 *
 * Ilgari ekran faqat skanerlangan kodni qabul qilardi — yangi model
 * uchun administrator Mahsulotlar sahifasida modelni yaratib, keyin
 * har variantning 13 xonali kodini qo'lda terib chiqardi.
 */

import { expect, test, type APIRequestContext, type Page } from '@playwright/test'

import { API, createTestProduct, login, openApp, type Session, type TestProduct } from './data'

// Kirim kompyuteri — kassa bilan bir xil ekran
test.use({ viewport: { width: 1366, height: 768 } })

let admin: Session
let product: TestProduct
let sizes: { id: number; name: string }[]
let colors: { id: number; name: string }[]

test.beforeAll(async ({ request }) => {
  admin = await login(request)
  product = await createTestProduct(request, admin)

  sizes = await get(request, '/api/sizes/')
  colors = await get(request, '/api/colors/')
})

async function get(request: APIRequestContext, path: string) {
  const response = await request.get(`${API}${path}`, {
    headers: { Authorization: `Bearer ${admin.access}` },
  })

  return response.json()
}

/** Nomi bo'yicha mahsulot — qoldiq va narxni tekshirish uchun */
async function findProduct(request: APIRequestContext, name: string) {
  const page = await get(request, `/api/products/?search=${encodeURIComponent(name)}`)

  expect(page.results.length, `«${name}» topilmadi`).toBeGreaterThan(0)

  return page.results[0]
}

/** Oxirgi yaratilgan hujjat (ro'yxat yangisidan boshlanadi) */
async function lastPurchase(request: APIRequestContext) {
  const page = await get(request, '/api/purchases/')

  return page.results[0]
}

/** Kirim formasi sahifada doim ochiq — tugma bosish shart emas */
async function openEditor(page: Page) {
  await openApp(page, admin, '/purchases')
  await page.getByRole('heading', { name: 'Kirim hujjati' }).waitFor()
}

test('yangi model kirim ekranida yaratiladi va qoldiqqa tushadi', async ({ page, request }) => {
  const name = `Kirim kurtkasi ${Date.now()}`

  await openEditor(page)
  await page.getByRole('button', { name: 'Yangi mahsulot' }).click()

  const form = page.getByTestId('quick-product')

  await form.getByLabel('Mahsulot nomi').fill(name)
  await form.getByLabel('Sotuv narxi').fill('500000')

  // Ikki o'lcham × bitta rang — to'rtta emas, ikkita variant
  await form
    .getByRole('group', { name: 'O‘lchamlar' })
    .getByRole('button', { name: sizes[0]!.name, exact: true })
    .click()

  await form
    .getByRole('group', { name: 'O‘lchamlar' })
    .getByRole('button', { name: sizes[1]!.name, exact: true })
    .click()

  await form
    .getByRole('group', { name: 'Ranglar' })
    .getByRole('button', { name: colors[0]!.name, exact: true })
    .click()

  await form.getByRole('button', { name: 'Saqlash va qabul qilish' }).click()
  await expect(form.locator('.load-error')).toHaveCount(0)

  // Saqlangan zahoti katakcha ochiladi — sahifadan chiqilmaydi
  const grid = page.getByTestId('model-grid')

  await expect(grid).toBeVisible()
  await expect(grid).toContainText(name)

  await grid.getByLabel('Model tannarxi').fill('200000')
  await grid.getByLabel(`${sizes[0]!.name} ${colors[0]!.name}: nechta`).fill('3')
  await grid.getByLabel(`${sizes[1]!.name} ${colors[0]!.name}: nechta`).fill('2')

  await expect(grid).toContainText('5 dona')

  await grid.getByRole('button', { name: 'Tayyor' }).click()

  await expect(page.locator('.models-table')).toContainText(name)

  await page.getByRole('button', { name: 'Tasdiqlash' }).click()

  // Xulosa: model, dona, tannarx va yorliqlar soni
  const summary = page.getByTestId('purchase-summary')

  await expect(summary).toBeVisible()
  await expect(summary).toContainText('1 000 000')
  await expect(summary.getByTestId('label-count')).toHaveText('5')

  // Qo'shimcha yorliq: yirtilganini almashtirish uchun
  await summary.getByLabel('Qo‘shimcha yorliq').fill('2')
  await expect(summary.getByTestId('label-count')).toHaveText('7')

  // Matritsa to'liq yaratilgan va qoldiq oshgan
  const saved = await findProduct(request, name)

  expect(saved.variants).toHaveLength(2)

  const stock = Object.fromEntries(
    saved.variants.map((variant: { label: string; stock_quantity: number }) => [
      variant.label,
      variant.stock_quantity,
    ]),
  )

  expect(stock[`${sizes[0]!.name} / ${colors[0]!.name}`]).toBe(3)
  expect(stock[`${sizes[1]!.name} / ${colors[0]!.name}`]).toBe(2)
})

test('nom bo‘yicha qidiruv: model ro‘yxatdan tanlanadi', async ({ page }) => {
  await openEditor(page)

  const field = page.getByLabel('Tovar nomi')

  await field.fill(product.name)

  // Sichqoncha bilan: ro'yxatdagi birinchi model
  const option = page.getByRole('option', { name: new RegExp(product.name) })

  await expect(option).toBeVisible()
  await option.click()

  const grid = page.getByTestId('model-grid')

  await expect(grid).toContainText(product.name)

  await grid.getByLabel('Model tannarxi').fill('100000')
  await grid.getByLabel(`${product.sizes[0]!.name} ${product.colors[0]!.name}: nechta`).fill('4')
  await grid.getByRole('button', { name: 'Tayyor' }).click()

  const row = page.locator('.models-table tbody tr', { hasText: product.name })

  await expect(row).toContainText('4')
  await expect(row).toContainText('400 000')
})

test('klaviatura bilan: o‘q, Enter, Tab — sichqonchasiz ishlaydi', async ({ page }) => {
  await openEditor(page)

  const field = page.getByLabel('Tovar nomi')

  await field.fill(product.name)
  await expect(page.getByRole('option', { name: new RegExp(product.name) })).toBeVisible()

  // Pastga o'q ro'yxatda yuradi, Enter tanlaydi
  await field.press('ArrowDown')
  await field.press('Enter')

  const grid = page.getByTestId('model-grid')

  await expect(grid).toBeVisible()

  // Fokus birinchi katakda — qo'l klaviaturada qoladi
  const first = grid.getByLabel(`${product.sizes[0]!.name} ${product.colors[0]!.name}: nechta`)

  await expect(first).toBeFocused()

  await page.keyboard.type('2')
  await page.keyboard.press('Tab')

  const second = grid.getByLabel(`${product.sizes[1]!.name} ${product.colors[0]!.name}: nechta`)

  await expect(second, 'Tab keyingi katakka o‘tmadi').toBeFocused()

  await page.keyboard.type('3')

  // Enter katakchani yopadi — modeli ro'yxatga tushadi
  await page.keyboard.press('Enter')

  await expect(grid).toBeHidden()
  await expect(page.locator('.models-table tbody tr', { hasText: product.name })).toContainText('5')

  // 1366×768: ekran yon tomonga surilmaydi
  const overflow = await page.evaluate(
    () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
  )

  expect(overflow, 'kirim ekrani sig‘maydi').toBeLessThanOrEqual(1)
})

test('bitta tannarx hamma qatorga tushadi, alohidasi ustun turadi', async ({ page, request }) => {
  await openEditor(page)

  await page.getByLabel('Tovar nomi').fill(product.name)
  await page.getByRole('option', { name: new RegExp(product.name) }).click()

  const grid = page.getByTestId('model-grid')
  const first = `${product.sizes[0]!.name} ${product.colors[0]!.name}`
  const second = `${product.sizes[1]!.name} ${product.colors[0]!.name}`

  await grid.getByLabel('Model tannarxi').fill('200000')
  await grid.getByLabel(`${first}: nechta`).fill('2')
  await grid.getByLabel(`${second}: nechta`).fill('1')

  // Bitta qatorning narxi boshqacha. Qator nomi variant yorlig'i:
  // «M / Oq» ko'rinishida
  await grid.getByRole('button', { name: 'Alohida tannarx' }).click()
  await grid
    .getByLabel(`${product.sizes[1]!.name} / ${product.colors[0]!.name}: tannarx`)
    .fill('250000')

  await expect(grid).toContainText('650 000')

  await grid.getByRole('button', { name: 'Tayyor' }).click()
  await page.getByRole('button', { name: 'Qoralama', exact: true }).click()

  await expect(page.locator('.notice')).toContainText('qoralama')

  const saved = await lastPurchase(request)
  const costs = Object.fromEntries(
    saved.lines.map((line: { variant_label: string; unit_cost: string }) => [
      line.variant_label,
      line.unit_cost,
    ]),
  )

  // Hujjatdagi qator nomi — variant yorlig'i («M / Oq»)
  expect(costs[`${product.sizes[0]!.name} / ${product.colors[0]!.name}`]).toBe('200000.00')
  expect(costs[`${product.sizes[1]!.name} / ${product.colors[0]!.name}`]).toBe('250000.00')
  expect(saved.total).toBe('650000.00')
})

test('ustama sotuv narxini taklif qiladi, narx faqat tasdiqlanganda saqlanadi', async ({
  page,
  request,
}) => {
  const before = await findProduct(request, product.name)

  await openEditor(page)

  await page.getByLabel('Tovar nomi').fill(product.name)
  await page.getByRole('option', { name: new RegExp(product.name) }).click()

  const grid = page.getByTestId('model-grid')

  await grid.getByLabel('Model tannarxi').fill('33333')
  await grid.getByLabel('Ustama foizi').fill('60')

  // 33 333 + 60 % = 53 332,80 → qadam 1 000 bo'lgani uchun 54 000
  await expect(grid.getByLabel('Yangi sotuv narxi')).toHaveValue(/54.000/)

  await grid.getByLabel(`${product.sizes[0]!.name} ${product.colors[0]!.name}: nechta`).fill('1')
  await grid.getByRole('button', { name: 'Tayyor' }).click()

  await page.getByRole('button', { name: 'Qoralama', exact: true }).click()
  await expect(page.locator('.notice')).toContainText('qoralama')

  // Qoralama — do'konda hali eski narx
  const draft = await findProduct(request, product.name)

  expect(draft.sale_price).toBe(before.sale_price)

  // Qoralamani chipdan qaytarib yuklaymiz va tasdiqlaymiz. Chip aynan
  // shu hujjatniki: boshqa testlar ham qoralama qoldiradi.
  const saved = await lastPurchase(request)

  await page.getByRole('button', { name: new RegExp(`${saved.number} qoralamasi`) }).click()
  await expect(page.locator('.draft-note')).toContainText(saved.number)

  await page.getByRole('button', { name: 'Tasdiqlash' }).click()
  await expect(page.getByTestId('purchase-summary')).toBeVisible()

  const confirmed = await findProduct(request, product.name)

  expect(confirmed.sale_price).toBe('54000.00')
})

test('noma’lum shtrix-kod: shu kod bilan yangi mahsulot yaratiladi', async ({ page, request }) => {
  const code = `21${Date.now().toString().slice(-11)}`
  const name = `Skanerlangan sumka ${Date.now()}`

  await openEditor(page)

  const field = page.getByLabel('Tovar nomi')

  await field.fill(code)
  await field.press('Enter')

  const unknown = page.getByTestId('unknown-barcode')

  await expect(unknown).toContainText(code)
  await unknown.getByRole('button', { name: 'Shu kod bilan yangi mahsulot' }).click()

  const form = page.getByTestId('quick-product')

  await expect(form).toContainText(code)

  await form.getByLabel('Mahsulot nomi').fill(name)
  await form.getByLabel('Sotuv narxi').fill('150000')
  await form.getByRole('button', { name: 'Saqlash va qabul qilish' }).click()
  await expect(form.locator('.load-error')).toHaveCount(0)

  // O'lchamsiz mahsulot — bitta katak, dona darhol bittaga qo'yiladi
  const grid = page.getByTestId('model-grid')

  await expect(grid).toContainText(name)

  await grid.getByLabel('Model tannarxi').fill('90000')
  await grid.getByRole('button', { name: 'Tayyor' }).click()
  await page.getByRole('button', { name: 'Tasdiqlash' }).click()

  await expect(page.getByTestId('purchase-summary')).toBeVisible()

  // Endi shu kod skanerlansa, tovar topiladi
  const found = await get(request, `/api/variants/by-barcode/?code=${code}`)

  expect(found.product_name).toBe(name)
  expect(found.stock_quantity).toBe(1)
})

test('qoralama davom ettiriladi: qatorlar katakchaga qaytadi', async ({ page }) => {
  await openEditor(page)

  await page.getByLabel('Tovar nomi').fill(product.name)
  await page.getByRole('option', { name: new RegExp(product.name) }).click()

  const grid = page.getByTestId('model-grid')
  const cell = `${product.sizes[0]!.name} ${product.colors[0]!.name}: nechta`

  await grid.getByLabel('Model tannarxi').fill('120000')
  await grid.getByLabel(cell).fill('6')
  await grid.getByRole('button', { name: 'Tayyor' }).click()
  await page.getByRole('button', { name: 'Qoralama', exact: true }).click()

  const notice = page.locator('.notice')

  await expect(notice).toContainText('qoralama')

  const number = (await notice.textContent())?.match(/KIR-[\d-]+/)?.[0] ?? ''

  expect(number, 'qoralama raqami ko‘rinmadi').not.toBe('')

  // Qoralamalar kartasidagi chip bosilsa — forma qayta to'ladi.
  // Chip aynan shu hujjatniki: boshqa testlar ham qoralama qoldiradi.
  const chip = page.getByRole('button', { name: new RegExp(`${number} qoralamasi`) })

  await expect(chip).toBeVisible()
  await chip.click()

  await expect(page.locator('.draft-note')).toContainText(number)
  await expect(page.locator('.models-table tbody tr', { hasText: product.name })).toContainText('6')

  await page.locator('.models-table').getByRole('button', { name: 'Tahrirlash' }).click()

  await expect(page.getByTestId('model-grid').getByLabel(cell)).toHaveValue('6')
})

test('tasdiqlangan kirimda bitta qatorning yorlig‘i qayta chiqadi', async ({ page }) => {
  // Chop etish oynasi testni to'xtatib qo'ymasin
  await page.addInitScript(() => {
    window.print = () => {}
  })

  await openApp(page, admin, '/purchases')
  await page.locator('tbody tr', { hasText: product.purchase.number }).click()

  const opened = page.getByTestId('opened-purchase')

  // To'liq ro'yxat "Batafsil" ostida — shtrix-kod va qator yorlig'i
  await opened.getByRole('button', { name: 'Batafsil' }).click()

  const first = opened.locator('.table-scroll tbody tr').first()

  await expect(first).toBeVisible()
  await first.getByRole('button', { name: /yorliqni qayta chop etish/ }).click()

  // Faqat o'sha qatorning donasi chiqadi (2 dona), butun hujjat emas
  await expect(page.locator('.print-sheet .label')).toHaveCount(2)
})


test('tezkor qator: oxirgi modeldan katakcha ochiladi', async ({ page }) => {
  await openEditor(page)

  const chip = page.getByTestId('model-strip').locator('.model-chip').first()

  await expect(chip).toBeVisible()

  const name = (await chip.locator('strong').textContent())?.trim() ?? ''

  await chip.click()

  await expect(page.getByTestId('model-grid')).toContainText(name)
})

test('yangi mahsulot rasmsiz ham saqlanadi', async ({ page, request }) => {
  const name = `Rasmsiz ko‘ylak ${Date.now()}`

  await openEditor(page)
  await page.getByRole('button', { name: 'Yangi mahsulot' }).click()

  const form = page.getByTestId('quick-product')

  // Rasm maydoni bo'sh turadi — u majburiy emas
  await expect(form.locator('.drop-empty')).toBeVisible()

  await form.getByLabel('Mahsulot nomi').fill(name)
  await form.getByLabel('Tannarx').fill('100000')
  await form.getByLabel('Ustama foizi').fill('50')

  // 100 000 + 50 % = 150 000
  await expect(form.getByLabel('Sotuv narxi')).toHaveValue(/150.000/)

  await form.getByRole('button', { name: 'Saqlash va qabul qilish' }).click()
  await expect(form.locator('.load-error')).toHaveCount(0)

  const grid = page.getByTestId('model-grid')

  await expect(grid).toContainText(name)

  // Tannarx oynadan katakchaga ko'chadi — qayta yozish shart emas
  await expect(grid.getByLabel('Model tannarxi')).toHaveValue('100000')

  const saved = await findProduct(request, name)

  expect(saved.sale_price).toBe('150000.00')
  expect(saved.images).toHaveLength(0)
})

test('ochilgan hujjatda qatorlar model bo‘yicha katakchada', async ({ page }) => {
  await openApp(page, admin, '/purchases')
  await page.locator('tbody tr', { hasText: product.purchase.number }).click()

  const opened = page.getByTestId('opened-purchase')
  const model = opened.locator('.doc-model', { hasText: product.name })

  await expect(model).toBeVisible()
  await expect(model).toContainText('8 dona')

  // Kelgan katak — soni bilan, kelmagani — chiziqcha
  await expect(
    model.getByLabel(`${product.sizes[0]!.name} ${product.colors[0]!.name}: 2 dona`),
  ).toHaveText('2')

  await expect(
    model.getByLabel(`${product.sizes[2]!.name} ${product.colors[1]!.name}: 0 dona`),
  ).toHaveText('—')
})
