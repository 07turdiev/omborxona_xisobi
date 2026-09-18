/**
 * Mahsulotlar sahifasi telefon o'lchamida, sensorli ekran bilan.
 *
 * Nimani tekshiradi:
 *   1. Karta panjarasi telefonda haqiqatan ishlatsa bo'ladigan holatda:
 *      bitta ustun, barmoq uchun katta nishonlar, qidiruv bosh barmoq
 *      yetadigan joyda (ekranning pastida).
 *   2. Mahsulot sahifasida rang tanlanganda o'lcham tugmalari faqat shu
 *      rangning qoldig'ini ko'rsatadi, tugagan o'lcham o'chirilgan holda
 *      ro'yxatda qoladi, hamma ranglar bo'yicha jami esa ko'rinib turadi.
 *   3. Kameradan rasm bitta bosishda olinadi, yuklash jarayoni ko'rinadi
 *      va yuklash davomida sahifa to'silmaydi.
 *   4. Kassa ekranida (1366×768) kartalar bir necha ustunda.
 *
 * Ishga tushirish:  npm run test:print
 */

import { createCanvas } from '@napi-rs/canvas'
import { expect, test, type Page } from '@playwright/test'

import { createTestProduct, login, openApp, type Session, type TestProduct } from './data'

/** Oddiy telefon ekrani */
const PHONE = { width: 390, height: 844 }

/** Barmoq bilan bosiladigan nishonning eng kichik balandligi (Apple/Google tavsiyasi) */
const TAP = 44

let admin: Session
let product: TestProduct

test.use({ viewport: PHONE, hasTouch: true, isMobile: true })

test.beforeAll(async ({ request }) => {
  admin = await login(request)
  product = await createTestProduct(request, admin)
})

async function box(locator: ReturnType<Page['locator']>) {
  const rect = await locator.boundingBox()

  expect(rect, 'element ekranda yo‘q').not.toBeNull()

  return rect!
}

test('telefonda: bitta ustun, katta nishonlar, qidiruv pastda', async ({ page }, info) => {
  await openApp(page, admin, '/products')

  const cards = page.locator('.product-card')

  await expect(cards.nth(2)).toBeVisible()

  // Bitta ustun: kartalar bir chiziqda, biri ostida biri
  const rects = await Promise.all([0, 1, 2].map((index) => box(cards.nth(index))))

  for (const rect of rects) {
    expect(Math.abs(rect.x - rects[0]!.x), 'kartalar bir ustunda emas').toBeLessThanOrEqual(1)
    expect(rect.width, 'karta ekran eniga yoyilmagan').toBeGreaterThan(PHONE.width * 0.8)
    expect(rect.height, 'karta barmoq uchun kichik').toBeGreaterThanOrEqual(TAP)
  }

  expect(rects[1]!.y).toBeGreaterThan(rects[0]!.y)

  // Qidiruv bosh barmoq yetadigan joyda: ekranning pastki qismida va
  // **ekran ichida**. Faqat "pastda" deb tekshirish yetmaydi — panel
  // ro'yxatning oxiriga tushib qolsa ham "pastda" bo'ladi.
  const search = page.getByRole('searchbox', { name: 'Mahsulot qidirish' })

  const inThumbZone = async (moment: string) => {
    const rect = await box(search)

    expect(rect.y, `${moment}: qidiruv ekranning pastida emas`).toBeGreaterThan(PHONE.height * 0.75)
    expect(rect.y + rect.height, `${moment}: qidiruv ekrandan chiqib ketgan`).toBeLessThanOrEqual(
      PHONE.height,
    )

    return rect
  }

  const searchRect = await inThumbZone('ochilganda')

  // Ro'yxat surilganda ham joyida qoladi
  await page.evaluate(() => window.scrollBy(0, 1500))
  await inThumbZone('pastga surilganda')
  await page.evaluate(() => window.scrollTo(0, 0))

  const filterButton = page.getByRole('button', { name: /Filtr/ })

  expect(searchRect.height, 'qidiruv maydoni kichik').toBeGreaterThanOrEqual(TAP)
  expect((await box(filterButton)).height, 'Filtr tugmasi kichik').toBeGreaterThanOrEqual(TAP)

  // Grid'da kichik rasm va kechiktirib yuklash
  const image = cards.locator('.card-image img').first()

  if (await image.count()) {
    await expect(image).toHaveAttribute('loading', 'lazy')
    await expect(image).toHaveAttribute('src', /\/thumb\//)
  }

  await page.screenshot({ path: info.outputPath('telefon-mahsulotlar.png') })

  console.log(
    `    telefon: karta ${Math.round(rects[0]!.width)}×${Math.round(rects[0]!.height)} px, ` +
      `qidiruv ${Math.round(searchRect.height)} px balandlikda, ekranning ` +
      `${Math.round((searchRect.y / PHONE.height) * 100)}% qismida`,
  )

  // Filtrlar qidiruv ustida ochiladi — bosh barmoqdan uzoqqa ketmaydi
  await filterButton.tap()

  const onlyInStock = page.locator('.check', { hasText: 'Faqat qoldig‘i bor' })

  await expect(onlyInStock).toBeVisible()
  expect((await box(onlyInStock)).height, 'filtr nishoni kichik').toBeGreaterThanOrEqual(TAP)
  expect((await box(onlyInStock)).y, 'filtr qidiruv ustida emas').toBeLessThan(searchRect.y)

  await onlyInStock.tap()

  await expect(filterButton).toContainText('1')
  await expect(page.locator('.card-stock.out')).toHaveCount(0)

  // "Qaysi o'lcham qoldi" — mahsulotni ochmasdan kartada ko'rinadi
  await search.fill(product.name)

  await expect(cards).toHaveCount(1)
  await expect(cards.first().locator('.size-entry')).toHaveText([
    `${product.sizes[0]!.name} 3`,
    `${product.sizes[1]!.name} 0`,
    `${product.sizes[2]!.name} 5`,
  ])
})

test('mahsulot sahifasi: rang tanlanganda o‘lcham qoldig‘i shu rangniki', async ({ page }, info) => {
  await openApp(page, admin, `/products/${product.id}`)

  const [first, second] = product.colors as [TestProduct['colors'][0], TestProduct['colors'][0]]
  const sizeButtons = page.locator('.size-button')

  await expect(sizeButtons).toHaveCount(3)

  // Ikkinchi rang: faqat birinchi o'lchamda 1 dona
  await page.locator('.swatch', { hasText: second.name }).tap()

  await expect(sizeButtons.nth(0)).toBeEnabled()
  await expect(sizeButtons.nth(0)).toContainText('1 dona')
  await expect(sizeButtons.nth(1)).toBeDisabled()
  await expect(sizeButtons.nth(2)).toBeDisabled()

  // Birinchi rang: 2 · 0 · 5
  await page.locator('.swatch', { hasText: first.name }).tap()

  await expect(sizeButtons.nth(0)).toContainText('2 dona')
  await expect(sizeButtons.nth(1)).toBeDisabled()
  await expect(sizeButtons.nth(2)).toContainText('5 dona')

  // Tugagan o'lcham ham ro'yxatda — o'chirilgan holda
  await expect(sizeButtons.nth(1)).toContainText(product.sizes[1]!.name)

  // Hamma ranglar bo'yicha jami rang tanlangan bo'lsa ham ko'rinadi
  await expect(page.getByTestId('all-colors')).toContainText('jami 8 dona')

  for (const index of [0, 2]) {
    expect((await box(sizeButtons.nth(index))).height).toBeGreaterThanOrEqual(TAP)
  }

  // O'lcham tanlansa — variant shtrix-kodi
  await sizeButtons.nth(2).tap()
  await expect(page.locator('.barcode-text')).toHaveText(/^\d{13}$/)

  await page.screenshot({ path: info.outputPath('telefon-mahsulot.png'), fullPage: true })
})

test('telefondan rasm: yuklash ko‘rinadi, sahifa to‘silmaydi', async ({ page }) => {
  // Lokal tarmoqda yuklash bir zumda tugaydi va jarayonni ko'rib bo'lmaydi —
  // shuning uchun so'rov ataylab sekinlatiladi
  await page.route('**/api/product-images/', async (route) => {
    if (route.request().method() === 'POST') await new Promise((done) => setTimeout(done, 2500))

    await route.continue()
  })

  await openApp(page, admin, `/products/${product.id}`)

  // Bitta bosish — telefonda to'g'ridan-to'g'ri orqa kamera ochiladi
  const camera = page.getByTestId('camera-input')

  await expect(camera).toHaveAttribute('capture', 'environment')
  await expect(camera).toHaveAttribute('accept', 'image/*')

  await camera.setInputFiles({ name: 'surat.jpg', mimeType: 'image/jpeg', buffer: photo() })

  const uploading = page.locator('.image-item.uploading')

  await expect(uploading).toBeVisible()
  await expect(uploading.locator('progress')).toBeVisible()

  // Yuklash davom etayotganda sahifa ishlaydi: tahrirlash oynasi ochiladi
  // va maydon to'ldiriladi
  await page.getByRole('button', { name: 'Tahrirlash' }).tap()

  const brand = page.locator('.overlay-card .field:has(> label:text-is("Brend")) input')

  await brand.fill('Sinov brendi')
  await expect(brand).toHaveValue('Sinov brendi')
  await page.getByRole('button', { name: 'Bekor qilish' }).tap()

  // Yuklash tugaydi: navbat bo'shaydi, rasm asosiy bo'ladi, galereya yangilanadi
  await expect(uploading).toHaveCount(0, { timeout: 20_000 })
  await expect(page.locator('.image-item.primary img')).toHaveAttribute('src', /\/thumb\//)
  await expect(page.locator('.gallery-slide img').first()).toHaveAttribute('src', /\/medium\//)

  // Ro'yxat kartasida endi rasm bor va u haqiqatan ochiladi
  await page.goto('/products')
  await page.getByRole('searchbox', { name: 'Mahsulot qidirish' }).fill(product.name)

  const cardImage = page.locator('.product-card .card-image img')

  await expect(cardImage).toHaveCount(1)
  await expect
    .poll(() => cardImage.evaluate((element) => (element as HTMLImageElement).naturalWidth))
    .toBeGreaterThan(0)
})

test.describe('kassa ekrani', () => {
  // Kassa kompyuteri: 1366×768, sichqoncha
  test.use({ viewport: { width: 1366, height: 768 }, hasTouch: false, isMobile: false })

  test('kartalar bir necha ustunda, qidiruv tepada', async ({ page }, info) => {
    await openApp(page, admin, '/products')

    const cards = page.locator('.product-card')

    await expect(cards.nth(3)).toBeVisible()

    const [first, second] = await Promise.all([box(cards.nth(0)), box(cards.nth(1))])

    expect(Math.abs(first.y - second.y), 'kartalar bir qatorda emas').toBeLessThanOrEqual(1)
    expect(second.x).toBeGreaterThan(first.x)

    const columns = await page
      .locator('.card-grid')
      .evaluate((grid) => getComputedStyle(grid).gridTemplateColumns.split(' ').length)

    expect(columns, 'kassa ekranida ustunlar kam').toBeGreaterThanOrEqual(4)

    const search = await box(page.getByRole('searchbox', { name: 'Mahsulot qidirish' }))

    expect(search.y, 'kassa ekranida qidiruv tepada bo‘lishi kerak').toBeLessThan(200)

    await page.screenshot({ path: info.outputPath('kassa-mahsulotlar.png') })

    console.log(`    kassa ekrani: ${columns} ustun, karta ${Math.round(first.width)} px`)
  })
})

/** Telefonda olingan surat o'rnida: 1200×1500 JPEG */
function photo(): Buffer {
  const canvas = createCanvas(1200, 1500)
  const context = canvas.getContext('2d')

  context.fillStyle = '#c2185b'
  context.fillRect(0, 0, 1200, 1500)
  context.fillStyle = '#ffffff'
  context.fillRect(300, 300, 600, 900)

  return canvas.toBuffer('image/jpeg')
}
