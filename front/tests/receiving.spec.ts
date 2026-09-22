/**
 * Tovar qabul qilish — uch qadam.
 *
 * Do'konga keladigan tovarda shtrix-kod bo'lmaydi: yorliqni do'konning
 * o'zi chiqaradi. Shuning uchun ekran "qanday tovar keldi" degan
 * savoldan boshlanadi, keyin "nechtadan", oxirida yorliq.
 */

import { expect, test, type APIRequestContext, type Page } from '@playwright/test'

import { API, login, openApp, testPhoto, type Session } from './data'

// Do'kondagi kompyuter
test.use({ viewport: { width: 1366, height: 768 } })

let admin: Session
let sizes: { id: number; name: string }[]
let colors: { id: number; name: string }[]
let categories: { id: number; name: string }[]

test.beforeAll(async ({ request }) => {
  admin = await login(request)

  sizes = await get(request, '/api/sizes/')
  colors = await get(request, '/api/colors/')
  categories = await get(request, '/api/categories/')
})

function headers() {
  return { Authorization: `Bearer ${admin.access}` }
}

async function get(request: APIRequestContext, path: string) {
  return (await request.get(`${API}${path}`, { headers: headers() })).json()
}

/** Nomi bo'yicha mahsulot — qoldiq va narxni tekshirish uchun */
async function findProducts(request: APIRequestContext, name: string) {
  const page = await get(request, `/api/products/?search=${encodeURIComponent(name)}`)

  return page.results as {
    id: number
    name: string
    sale_price: string
    images: unknown[]
    variants: { id: number; label: string; stock_quantity: number }[]
  }[]
}

async function findProduct(request: APIRequestContext, name: string) {
  const [first] = await findProducts(request, name)

  expect(first, `«${name}» topilmadi`).toBeTruthy()

  return first!
}

/** Do'konda avval kelgan model (API orqali, ekrandan emas) */
async function createModel(
  request: APIRequestContext,
  name: string,
  sizeIds: number[],
  colorIds: number[],
) {
  const response = await request.post(`${API}/api/products/`, {
    headers: headers(),
    data: {
      category: categories[0]!.id,
      name,
      sale_price: '400000',
      size_ids: sizeIds,
      color_ids: colorIds,
    },
  })

  expect(response.ok(), await response.text()).toBeTruthy()

  return (await response.json()) as { id: number; name: string }
}

/** Oxirgi hujjat (ro'yxat yangisidan boshlanadi) */
async function lastPurchase(request: APIRequestContext) {
  const page = await get(request, '/api/purchases/')

  return page.results[0]
}

function panel(page: Page) {
  return page.getByTestId('quick-product')
}

function grid(page: Page) {
  return page.getByTestId('model-grid')
}

/** Menyudagi «Tovar qabul qilish» bandi bilan chalkashmasligi uchun */
function confirmButton(page: Page) {
  return page.getByTestId('step-quantities').getByRole('button', { name: 'Qabul qilish' })
}

/** 1-qadam: yangi tovarni kiritadi va 2-qadamga o'tadi */
async function fillNewProduct(
  page: Page,
  name: string,
  options: { sizes?: string[]; colors?: string[]; cost?: string; markup?: string } = {},
) {
  const form = panel(page)

  await form.getByLabel('Mahsulot nomi').fill(name)

  if (options.cost) await form.getByLabel('Tannarx').fill(options.cost)
  if (options.markup) await form.getByLabel('Ustama foizi').fill(options.markup)

  for (const size of options.sizes ?? []) {
    await form
      .getByRole('group', { name: 'O‘lchamlar' })
      .getByRole('button', { name: size, exact: true })
      .click()
  }

  for (const color of options.colors ?? []) {
    await form
      .getByRole('group', { name: 'Ranglar' })
      .getByRole('button', { name: color, exact: true })
      .click()
  }

  // Rasm majburiy: usiz «Davom etish» ochilmaydi
  await form.getByTestId('file-input').setInputFiles(testPhoto())
  await expect(form.locator('.photo-grid li')).toHaveCount(1)

  await form.getByRole('button', { name: 'Davom etish' }).click()
  await expect(form.locator('.load-error')).toHaveCount(0)
}

test('yangi tovar: kiritiladi, soni yoziladi, yorliq chiqadi', async ({ page, request }) => {
  const name = `Kirim kurtkasi ${Date.now()}`
  const [first, second] = [sizes[0]!.name, sizes[1]!.name]
  const color = colors[0]!.name

  await openApp(page, admin, '/purchases')

  // 1-qadam
  await expect(page.getByTestId('receiving-steps')).toContainText('Qanday tovar')
  await fillNewProduct(page, name, {
    sizes: [first, second],
    colors: [color],
    cost: '200000',
    markup: '60',
  })

  // 2-qadam: tannarx birinchi qadamdan ko'chadi
  await expect(page.getByTestId('step-quantities')).toBeVisible()
  await expect(grid(page).getByLabel('Model tannarxi')).toHaveValue(/^200\s000$/)

  await grid(page).getByLabel(`${first} ${color}: nechta`).fill('3')
  await grid(page).getByLabel(`${second} ${color}: nechta`).fill('2')

  await expect(page.getByTestId('step-quantities')).toContainText('5 dona')

  await confirmButton(page).click()

  // 3-qadam: yorliqlar
  const summary = page.getByTestId('purchase-summary')

  await expect(summary).toBeVisible()
  await expect(summary).toContainText('1 000 000')
  await expect(summary.getByTestId('label-count')).toHaveText('5')

  await summary.getByLabel('Qo‘shimcha yorliq').fill('2')
  await expect(summary.getByTestId('label-count')).toHaveText('7')

  // Qoldiq oshdi, matritsa faqat kelgan juftliklardan iborat
  const saved = await findProduct(request, name)

  expect(saved.variants).toHaveLength(2)

  const stock = Object.fromEntries(
    saved.variants.map((variant) => [variant.label, variant.stock_quantity]),
  )

  expect(stock[`${first} / ${color}`]).toBe(3)
  expect(stock[`${second} / ${color}`]).toBe(2)
})

test('bitta o‘lcham va bitta rang: jadval bitta katakdan iborat', async ({ page }) => {
  const name = `Bitta variant ${Date.now()}`

  await openApp(page, admin, '/purchases')

  const form = panel(page)

  await expect(form).toContainText('Qaysi o‘lchamlar keldi?')
  await expect(form).toContainText('Qaysi ranglar keldi?')

  await fillNewProduct(page, name, { sizes: [sizes[0]!.name], colors: [colors[0]!.name] })

  await expect(grid(page).locator('.cell')).toHaveCount(1)
  await expect(grid(page).getByLabel(`${sizes[0]!.name} ${colors[0]!.name}: nechta`)).toBeFocused()

  await page.keyboard.type('5')
  await expect(page.getByTestId('step-quantities')).toContainText('5 dona')
})

test('qabulda joy tanlanadi: tovar to‘g‘ridan-to‘g‘ri zalga tushadi', async ({
  page,
  request,
}) => {
  const name = `Zalga kirim ${Date.now()}`

  await openApp(page, admin, '/purchases')
  await fillNewProduct(page, name, { sizes: [sizes[0]!.name], colors: [colors[0]!.name] })

  await grid(page).getByLabel('Model tannarxi').fill('100000')
  await page.keyboard.press('Tab')
  await grid(page).getByLabel(`${sizes[0]!.name} ${colors[0]!.name}: nechta`).fill('4')

  // Standart — ombor; bu safar javonga qo'yamiz
  await page.getByLabel('Qayerga tushsin').selectOption({ label: 'Savdo zali' })
  await confirmButton(page).click()

  const summary = page.getByTestId('purchase-summary')

  await expect(summary).toBeVisible()
  await expect(summary.getByTestId('summary-location')).toHaveText('Savdo zali')

  // Qoldiq ombordan o'tmay zalga tushdi
  const saved = await findProduct(request, name)
  const variant = saved.variants[0]!
  const at = (kind: string) =>
    variant.stocks?.find((stock: { kind: string }) => stock.kind === kind)?.quantity ?? 0

  expect(at('shop')).toBe(4)
  expect(at('warehouse')).toBe(0)
})

test('rasm majburiy, narx ustamadan taklif qilinadi', async ({ page, request }) => {
  const name = `Ustamali ko‘ylak ${Date.now()}`

  await openApp(page, admin, '/purchases')

  const form = panel(page)

  await form.getByLabel('Mahsulot nomi').fill(name)
  await form.getByLabel('Tannarx').fill('100000')
  await form.getByLabel('Ustama foizi').fill('50')

  // 100 000 + 50 % = 150 000
  await expect(form.getByLabel('Sotuv narxi')).toHaveValue(/150.000/)

  // Rasmsiz davom etib bo'lmaydi: rasmsiz tovarni ro'yxatdan tanib bo'lmaydi
  const next = form.getByRole('button', { name: 'Davom etish' })

  await expect(form.locator('.drop-empty')).toContainText('majburiy')
  await expect(next).toBeDisabled()

  await form.getByTestId('file-input').setInputFiles(testPhoto())
  await expect(next).toBeEnabled()

  await next.click()

  await expect(grid(page)).toContainText(name)

  const saved = await findProduct(request, name)

  expect(saved.sale_price).toBe('150000.00')
  expect(saved.images).toHaveLength(1)
})

test('shu nomli tovar bor: yangisi yaratilmaydi', async ({ page, request }) => {
  const name = `Takror kurtka ${Date.now()}`

  await createModel(request, name, [sizes[0]!.id], [colors[0]!.id])

  await openApp(page, admin, '/purchases')
  await panel(page).getByLabel('Mahsulot nomi').fill(name)

  const warning = panel(page).locator('.same-product')

  await expect(warning).toContainText(name)
  await warning.getByRole('button', { name: 'Shu tovar yana keldi' }).click()

  await expect(grid(page)).toContainText(name)

  // Bazada baribir bitta tovar
  expect(await findProducts(request, name)).toHaveLength(1)
})

test('tovar sahifasidagi «Yana keldi» qabul qilishga olib boradi', async ({ page, request }) => {
  const name = `Yana kelgan shim ${Date.now()}`
  const model = await createModel(request, name, [sizes[0]!.id], [colors[0]!.id])

  await openApp(page, admin, `/products/${model.id}`)
  await page.getByRole('link', { name: 'Yana keldi' }).click()

  await expect(page).toHaveURL(new RegExp(`/purchases\\?model=${model.id}`))
  await expect(grid(page)).toContainText(name)
})

test('model yangi rangda keldi: variant shu yerda qo‘shiladi', async ({ page, request }) => {
  const name = `Ko‘k kurtka ${Date.now()}`
  const model = await createModel(request, name, [sizes[0]!.id, sizes[1]!.id], [colors[0]!.id])

  const newSize = sizes[2]!.name
  const newColor = colors[1]!.name

  await openApp(page, admin, `/purchases?model=${model.id}`)
  await expect(grid(page)).toContainText(name)

  await grid(page).getByRole('button', { name: /O‘lcham yoki rang/ }).click()

  await grid(page)
    .getByRole('group', { name: 'O‘lcham tanlash' })
    .getByRole('button', { name: newSize, exact: true })
    .click()

  await grid(page)
    .getByRole('group', { name: 'Rang tanlash' })
    .getByRole('button', { name: newColor, exact: true })
    .click()

  await grid(page).getByRole('button', { name: 'Qo‘shish' }).click()

  // Yangi katak darhol fokusda
  await expect(grid(page).getByLabel(`${newSize} ${newColor}: nechta`)).toBeFocused()
  await page.keyboard.type('20')

  await grid(page).getByLabel('Model tannarxi').fill('150000')
  await confirmButton(page).click()

  await expect(page.getByTestId('purchase-summary')).toBeVisible()

  // Faqat bitta yangi variant — qizil M, qizil L va ko'k XL yaratilmagan
  const saved = await findProduct(request, name)

  expect(saved.variants).toHaveLength(3)

  const stock = Object.fromEntries(
    saved.variants.map((variant) => [variant.label, variant.stock_quantity]),
  )

  expect(stock[`${newSize} / ${newColor}`]).toBe(20)
})

test('bo‘sh katakdagi «+» aynan o‘sha juftlikni yaratadi', async ({ page, request }) => {
  const name = `Bitta juftlik ${Date.now()}`
  const model = await createModel(request, name, [sizes[0]!.id, sizes[1]!.id], [colors[0]!.id])

  await openApp(page, admin, `/purchases?model=${model.id}`)

  // Ikkinchi rangni bitta juftlik bilan qo'shamiz
  await grid(page).getByRole('button', { name: /O‘lcham yoki rang/ }).click()

  await grid(page)
    .getByRole('group', { name: 'O‘lcham tanlash' })
    .getByRole('button', { name: sizes[0]!.name, exact: true })
    .click()

  await grid(page)
    .getByRole('group', { name: 'Rang tanlash' })
    .getByRole('button', { name: colors[1]!.name, exact: true })
    .click()

  await grid(page).getByRole('button', { name: 'Qo‘shish' }).click()
  await expect(grid(page).getByLabel(`${sizes[0]!.name} ${colors[1]!.name}: nechta`)).toBeFocused()

  // Endi bo'sh katak: ikkinchi o'lcham × ikkinchi rang
  const empty = grid(page).getByRole('button', {
    name: `${sizes[1]!.name} ${colors[1]!.name}: variantni qo‘shish`,
  })

  await expect(empty).toBeVisible()
  await empty.click()

  await expect(grid(page).getByLabel(`${sizes[1]!.name} ${colors[1]!.name}: nechta`)).toBeFocused()

  // 2 ta boshlang'ich + 2 ta qo'lda qo'shilgan (to'liq matritsa 4 emas, 6 bo'lardi)
  expect((await findProduct(request, name)).variants).toHaveLength(4)
})

test('bitta tannarx hamma qatorga tushadi, alohidasi ustun turadi', async ({ page, request }) => {
  const name = `Tannarx sinovi ${Date.now()}`
  const model = await createModel(request, name, [sizes[0]!.id, sizes[1]!.id], [colors[0]!.id])

  const first = `${sizes[0]!.name} ${colors[0]!.name}`
  const second = `${sizes[1]!.name} ${colors[0]!.name}`

  await openApp(page, admin, `/purchases?model=${model.id}`)

  await grid(page).getByLabel('Model tannarxi').fill('200000')
  await grid(page).getByLabel(`${first}: nechta`).fill('2')
  await grid(page).getByLabel(`${second}: nechta`).fill('1')

  // Bitta qatorning narxi boshqacha. Qator nomi variant yorlig'i: «M / Oq»
  await grid(page).getByRole('button', { name: 'Alohida tannarx' }).click()
  await grid(page)
    .getByLabel(`${sizes[1]!.name} / ${colors[0]!.name}: tannarx`)
    .fill('250000')

  await expect(page.getByTestId('step-quantities')).toContainText('650 000')

  await page.getByRole('button', { name: 'Keyinroq tugataman' }).click()
  await expect(page.locator('.notice')).toContainText('saqlandi')

  const saved = await lastPurchase(request)
  const costs = Object.fromEntries(
    saved.lines.map((line: { variant_label: string; unit_cost: string }) => [
      line.variant_label,
      line.unit_cost,
    ]),
  )

  expect(costs[`${sizes[0]!.name} / ${colors[0]!.name}`]).toBe('200000.00')
  expect(costs[`${sizes[1]!.name} / ${colors[0]!.name}`]).toBe('250000.00')
  expect(saved.total).toBe('650000.00')
})

test('ustama narxni taklif qiladi, narx faqat qabul qilinganda saqlanadi', async ({
  page,
  request,
}) => {
  const name = `Narx sinovi ${Date.now()}`
  const model = await createModel(request, name, [sizes[0]!.id], [colors[0]!.id])
  const before = await findProduct(request, name)

  await openApp(page, admin, `/purchases?model=${model.id}`)

  await grid(page).getByLabel('Model tannarxi').fill('33333')
  await grid(page).getByLabel('Ustama foizi').fill('60')

  // 33 333 + 60 % = 53 332,80 → qadam 1 000 bo'lgani uchun 54 000
  await expect(grid(page).getByLabel('Yangi sotuv narxi')).toHaveValue(/54.000/)

  await grid(page).getByLabel(`${sizes[0]!.name} ${colors[0]!.name}: nechta`).fill('1')

  await page.getByRole('button', { name: 'Keyinroq tugataman' }).click()
  await expect(page.locator('.notice')).toContainText('saqlandi')

  // Tugallanmagan — do'konda hali eski narx
  expect((await findProduct(request, name)).sale_price).toBe(before.sale_price)

  // Chipdan davom ettirib, qabul qilamiz
  const saved = await lastPurchase(request)

  await page.getByRole('button', { name: new RegExp(`${saved.number} qoralamasi`) }).click()
  await expect(page.locator('.draft-note')).toContainText(saved.number)

  await confirmButton(page).click()
  await expect(page.getByTestId('purchase-summary')).toBeVisible()

  expect((await findProduct(request, name)).sale_price).toBe('54000.00')
})

test('tugallanmagan qabul chipdan davom etadi', async ({ page, request }) => {
  const name = `Tugallanmagan ${Date.now()}`
  const model = await createModel(request, name, [sizes[0]!.id], [colors[0]!.id])
  const cell = `${sizes[0]!.name} ${colors[0]!.name}: nechta`

  await openApp(page, admin, `/purchases?model=${model.id}`)

  await grid(page).getByLabel('Model tannarxi').fill('120000')
  await grid(page).getByLabel(cell).fill('6')

  await page.getByRole('button', { name: 'Keyinroq tugataman' }).click()
  await expect(page.locator('.notice')).toContainText('saqlandi')

  const saved = await lastPurchase(request)

  await page.getByRole('button', { name: new RegExp(`${saved.number} qoralamasi`) }).click()

  await expect(page.locator('.draft-note')).toContainText(saved.number)
  await expect(grid(page).getByLabel(cell)).toHaveValue('6')
})

test('klaviatura: Tab katakdan katakka o‘tadi', async ({ page, request }) => {
  const name = `Klaviatura ${Date.now()}`
  const model = await createModel(
    request,
    name,
    [sizes[0]!.id, sizes[1]!.id],
    [colors[0]!.id],
  )

  await openApp(page, admin, `/purchases?model=${model.id}`)

  const first = grid(page).getByLabel(`${sizes[0]!.name} ${colors[0]!.name}: nechta`)

  await expect(first).toBeFocused()
  await page.keyboard.type('2')
  await page.keyboard.press('Tab')

  await expect(
    grid(page).getByLabel(`${sizes[1]!.name} ${colors[0]!.name}: nechta`),
    'Tab keyingi katakka o‘tmadi',
  ).toBeFocused()

  await page.keyboard.type('3')
  await expect(page.getByTestId('step-quantities')).toContainText('5 dona')
})

test('ochilgan hujjatda qatorlar model bo‘yicha katakchada', async ({ page, request }) => {
  const name = `Hujjat ${Date.now()}`
  const model = await createModel(
    request,
    name,
    [sizes[0]!.id, sizes[1]!.id],
    [colors[0]!.id, colors[1]!.id],
  )

  await openApp(page, admin, `/purchases?model=${model.id}`)

  await grid(page).getByLabel('Model tannarxi').fill('100000')

  // To'rt juftlikning uchtasi keldi — to'rtinchisi hujjatda bo'sh qoladi
  await grid(page).getByLabel(`${sizes[0]!.name} ${colors[0]!.name}: nechta`).fill('4')
  await grid(page).getByLabel(`${sizes[1]!.name} ${colors[0]!.name}: nechta`).fill('2')
  await grid(page).getByLabel(`${sizes[0]!.name} ${colors[1]!.name}: nechta`).fill('1')

  await confirmButton(page).click()
  await expect(page.getByTestId('purchase-summary')).toBeVisible()

  const saved = await lastPurchase(request)

  await page.locator('tbody tr', { hasText: saved.number }).click()

  const opened = page.getByTestId('opened-purchase')
  const group = opened.locator('.doc-model', { hasText: name })

  await expect(group).toContainText('7 dona')
  await expect(
    group.getByLabel(`${sizes[0]!.name} ${colors[0]!.name}: 4 dona`),
  ).toHaveText('4')

  // Kelmagan juftlik bo'sh qoladi
  await expect(
    group.getByLabel(`${sizes[1]!.name} ${colors[1]!.name}: 0 dona`),
  ).toHaveText('—')
})

test('tugallangan hujjatda bitta qatorning yorlig‘i qayta chiqadi', async ({ page, request }) => {
  // Chop etish oynasi testni to'xtatib qo'ymasin
  await page.addInitScript(() => {
    window.print = () => {}
  })

  const name = `Yorliq ${Date.now()}`
  const model = await createModel(request, name, [sizes[0]!.id], [colors[0]!.id])

  await openApp(page, admin, `/purchases?model=${model.id}`)

  await grid(page).getByLabel('Model tannarxi').fill('100000')
  await grid(page).getByLabel(`${sizes[0]!.name} ${colors[0]!.name}: nechta`).fill('2')

  await confirmButton(page).click()
  await expect(page.getByTestId('purchase-summary')).toBeVisible()

  const saved = await lastPurchase(request)

  await page.locator('tbody tr', { hasText: saved.number }).click()

  const opened = page.getByTestId('opened-purchase')

  await opened.getByRole('button', { name: 'Batafsil' }).click()

  const row = opened.locator('.table-scroll tbody tr').first()

  await row.getByRole('button', { name: /yorliqni qayta chop etish/ }).click()

  // Faqat o'sha qatorning donasi chiqadi
  await expect(page.locator('.print-sheet .label')).toHaveCount(2)
})
