/**
 * Chek logotipi: Sozlamalarda yuklanadi va chekda do'kon nomi o'rnida
 * chiqadi.
 *
 * Testlar butun zanjirni tekshiradi: fayl serverga boradi, oq-qora
 * ko'rinishi Sozlamalarda chiqadi, sinov chekida esa nuqtalari agentga
 * yuboriladi. Agentning o'zi ishga tushirilmaydi — javoblari Playwright
 * orqali qo'yiladi (tests/agent.spec.ts dagidek).
 */

import { expect, test, type Page } from '@playwright/test'

import { API, login, openApp, type Session } from './data'

const AGENT = 'http://127.0.0.1:7777/**'

/** Brauzer boshqa manzilga so'rov yuborishi uchun CORS sarlavhalari */
const CORS = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
  'Access-Control-Allow-Headers': 'Content-Type, x-agent-token',
}

/** 60 × 30 shaffof PNG, o'rtasida 40 × 20 qora to'rtburchak */
const LOGO_PNG = Buffer.from(
  'iVBORw0KGgoAAAANSUhEUgAAADwAAAAeCAYAAABwmH1PAAAAO0lEQVR42u3RsREAMAgDMcL+O8MMqTgSfe1G5whJWtS5' +
    '2NYLlvztYWBgYGBgYGBgYGBgYGBgYGBJ0mgNqjgBKKAVgUYAAAAASUVORK5CYII=',
  'base64',
)

let admin: Session

test.beforeAll(async ({ request }) => {
  admin = await login(request)
})

// Logotip boshqa testlardagi chekka tushmasin
test.afterAll(async ({ request }) => {
  await request.delete(`${API}/api/settings/logo/`, {
    headers: { Authorization: `Bearer ${admin.access}` },
  })
})

/** Ishlayotgan agent. Qaytgan ro'yxatga yuborilgan cheklar tushadi. */
async function agentOnline(page: Page) {
  const receipts: { logo?: { width: number; height: number; data: string } }[] = []

  await page.route(AGENT, async (route) => {
    const request = route.request()
    const path = new URL(request.url()).pathname

    if (request.method() === 'OPTIONS') {
      await route.fulfill({ status: 204, headers: CORS })
      return
    }

    if (path === '/receipt') receipts.push(request.postDataJSON())

    await route.fulfill({
      status: 200,
      headers: { ...CORS, 'Content-Type': 'application/json' },
      body: JSON.stringify(
        path === '/health' ? { version: 'sinov', codePage: 'cp1252', printers: [] } : { ok: true },
      ),
    })
  })

  return receipts
}

test('logotip yuklanadi, oq-qora ko‘rinadi va olib tashlanadi', async ({ page }) => {
  await openApp(page, admin, '/settings')

  await page.getByLabel('Chek logotipi').setInputFiles({
    name: 'logo.png',
    mimeType: 'image/png',
    buffer: LOGO_PNG,
  })

  await expect(page.getByText('Logotip saqlandi.')).toBeVisible()

  // Ko'rinishi — serverda tayyorlangan oq-qora PNG, printerdagi o'lchamda
  const preview = page.getByAltText('Chek logotipi')

  await expect(preview).toBeVisible()
  await expect(preview).toHaveAttribute('src', /^data:image\/png;base64,/)

  // Bo'sh hoshiya kesilgan va logotip 48 mm gacha kattalashgan
  await expect(preview).toHaveAttribute('style', /width: 48mm/)

  await page.getByRole('button', { name: 'Olib tashlash' }).click()

  await expect(page.getByText('Logotip olib tashlandi.')).toBeVisible()
  await expect(preview).toHaveCount(0)
})

test('sinov chekida logotip nuqtalari agentga boradi', async ({ page, request }) => {
  const upload = await request.post(`${API}/api/settings/logo/`, {
    headers: { Authorization: `Bearer ${admin.access}` },
    multipart: { logo: { name: 'logo.png', mimeType: 'image/png', buffer: LOGO_PNG } },
  })

  expect(upload.ok(), await upload.text()).toBeTruthy()

  const receipts = await agentOnline(page)

  await openApp(page, admin, '/settings/devices', { agent: 'fake' })
  await page.getByRole('button', { name: 'Agent orqali sinov cheki' }).click()

  await expect.poll(() => receipts.length).toBe(1)

  const logo = receipts[0]!.logo!

  // 40 × 20 to'rtburchak 48 × 24 mm ga moslangan: 384 × 192 nuqta
  expect(logo).toMatchObject({ width: 384, height: 192 })
  expect(Buffer.from(logo.data, 'base64')).toHaveLength((384 / 8) * 192)
})
