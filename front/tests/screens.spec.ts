/**
 * Asosiy ekranlar: telefonda gorizontal surilish va konsol xatolari.
 *
 * Har ekran ikki o'lchamda ochiladi — kassa kompyuteri (1366×768) va
 * telefon (390×844). Tekshiriladigani: sahifa yon tomonga surilmaydi va
 * konsolda xato yo'q.
 *
 * Shu yurishda dizayn hujjati uchun rasm ham olinadi:
 *
 *     SCREENSHOTS=before npm run test:ui tests/screens.spec.ts
 *
 * rasm `docs/screenshots/before/` ichiga tushadi. O'zgaruvchi
 * berilmasa rasm olinmaydi — tekshiruvning o'zi qoladi.
 */

import { mkdirSync } from 'node:fs'
import { join } from 'node:path'

import { expect, test, type Page } from '@playwright/test'

import { API, login, openApp, type Session } from './data'

/** Rasm albomi: `before`, `after` yoki bo'sh (rasm olinmaydi) */
const ALBUM = process.env.SCREENSHOTS ?? ''

/** `npm run test:ui` loyihaning `front/` papkasidan yurgiziladi */
const ALBUM_DIR = join(process.cwd(), '..', 'docs', 'screenshots', ALBUM)

interface Screen {
  name: string
  path: string
  /** Ma'lumot kelganini bildiradigan element */
  ready: string
  /** Rasmga olishdan oldin bajariladigan ish (masalan, savatga tovar qo'shish) */
  prepare?: (page: Page) => Promise<void>
}

let admin: Session
let product: { id: number; name: string }

test.beforeAll(async ({ request }) => {
  admin = await login(request)

  const response = await request.get(`${API}/api/catalog/?in_stock=true&ordering=name`, {
    headers: { Authorization: `Bearer ${admin.access}` },
  })

  const catalog = await response.json()

  expect(catalog.results.length, 'qoldig‘i bor tovar kerak — seed_demo').toBeGreaterThan(0)

  product = catalog.results[0]

  if (ALBUM) mkdirSync(ALBUM_DIR, { recursive: true })
})

/** Kassa: tanlagichdan bitta tovar savatga qo'shiladi. */
async function fillCart(page: Page) {
  const picker = page.locator('.pos-picker')

  // Telefon va planshetda tanlagich tugma bilan ochiladi
  if (!(await picker.isVisible())) {
    await page.getByRole('button', { name: 'Tovar tanlash' }).click()
  }

  await picker.getByRole('searchbox', { name: 'Tovar qidirish' }).fill(product.name)
  await expect(picker.locator('.tile').first()).toBeVisible()
  await picker.locator('.tile').first().click()

  // Varianti bitta bo'lsa savatga o'zi tushadi, aks holda katakcha ochiladi
  const grid = page.locator('.variant-grid')
  const row = page.locator('.cart-table tbody tr:not(:has(.empty-state))')

  await expect(grid.or(row).first()).toBeVisible()

  if (await grid.isVisible()) await grid.locator('.variant-cell:not([disabled])').first().click()

  await expect(row.first()).toBeVisible()

  if (await picker.locator('.picker-head').isVisible()) {
    const close = page.locator('.pos-picker').getByRole('button', { name: 'Yopish' })

    if (await close.isVisible()) await close.click()
  }
}

const SCREENS: Screen[] = [
  { name: 'login', path: '/login', ready: '.login-form' },
  { name: 'dashboard', path: '/dashboard', ready: '.kpi-card' },
  { name: 'products', path: '/products', ready: '.catalog' },
  { name: 'product', path: '', ready: '.product-page' },
  { name: 'pos', path: '/', ready: '.pos', prepare: fillCart },
  { name: 'purchases', path: '/purchases', ready: '.data-table tbody' },
  { name: 'reports', path: '/reports', ready: '.kpi-card' },
]

/**
 * Chop etish agenti bu testlarda ataylab o'chirilgan (`openApp`), shuning
 * uchun uning so'rovi konsolda xato bo'lib ko'rinadi — u sanalmaydi.
 */
function ours(text: string) {
  return !text.includes('127.0.0.1:7777') && !text.includes('favicon')
}

function check(width: number, height: number) {
  test.describe(`${width}×${height}`, () => {
    test.use({ viewport: { width, height } })

    for (const screen of SCREENS) {
      test(screen.name, async ({ page }) => {
        const errors: string[] = []

        page.on('console', (message) => {
          const where = message.location().url

          if (message.type() === 'error' && ours(`${message.text()} ${where}`)) {
            errors.push(`${message.text()} — ${where}`)
          }
        })

        page.on('pageerror', (error) => errors.push(error.message))

        const path = screen.name === 'product' ? `/products/${product.id}` : screen.path

        if (screen.name === 'login') {
          await page.goto(path)
        } else {
          await openApp(page, admin, path)
        }

        // Hisobot to'plangan ma'lumot ustida hisoblanadi — sekinroq keladi
        const problem = page.locator('.load-error')

        await expect(problem.or(page.locator(screen.ready)).first()).toBeVisible({
          timeout: 15_000,
        })

        // Yuklash xatosi bo'lsa, sababi xabarda ko'rinsin
        if (await problem.count()) {
          throw new Error(`${screen.name}: ${await problem.first().innerText()}`)
        }
        await screen.prepare?.(page)

        // Sahifa kirish animatsiyasi tugasin
        await page.waitForTimeout(400)

        // Rasm tekshiruvdan oldin olinadi — tekshiruv yiqilsa ham
        // nima ko'ringanini ko'rish mumkin bo'lsin
        if (ALBUM) {
          await page.screenshot({ path: join(ALBUM_DIR, `${screen.name}-${width}x${height}.png`) })
        }

        const overflow = await page.evaluate(
          () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
        )

        expect(overflow, `${screen.name}: sahifa yon tomonga suriladi`).toBeLessThanOrEqual(1)

        expect(errors, `${screen.name}: konsolda xato`).toEqual([])
      })
    }
  })
}

check(1366, 768)
check(390, 844)
