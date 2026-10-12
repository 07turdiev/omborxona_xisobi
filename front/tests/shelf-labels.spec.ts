/**
 * Ombor javonlarining yorliqlari: yorliqning o'rtasida manzil (`A1`).
 *
 * Yorliq javonga yopishtiriladi va xodim tovarni shu manzil bo'yicha
 * topadi. Testlar uch yo'lni tekshiradi — hamma javon, bitta qator,
 * bitta javon — va agent yo'q kunda yorliq brauzer orqali chiqishini.
 *
 * Agentning o'zi ishga tushirilmaydi: javoblari Playwright orqali
 * qo'yiladi (tests/agent.spec.ts dagidek).
 */

import { expect, test, type Page } from '@playwright/test'

import { login, openApp, type Session } from './data'

const AGENT = 'http://127.0.0.1:7777/**'

/** Brauzer boshqa manzilga so'rov yuborishi uchun CORS sarlavhalari */
const CORS = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
  'Access-Control-Allow-Headers': 'Content-Type, x-agent-token',
}

interface ShelfJob {
  widthMm: number
  heightMm: number
  textMm: number
  labels: { cell: string; quantity: number }[]
}

let admin: Session

test.beforeAll(async ({ request }) => {
  admin = await login(request)
})

/** Ishlayotgan agent. Qaytgan ro'yxatga yuborilgan yorliq ishlari tushadi. */
async function agentOnline(page: Page) {
  const sent: { path: string; body: ShelfJob }[] = []

  await page.route(AGENT, async (route) => {
    const request = route.request()
    const path = new URL(request.url()).pathname

    if (request.method() === 'OPTIONS') {
      await route.fulfill({ status: 204, headers: CORS })
      return
    }

    if (request.method() === 'POST') sent.push({ path, body: request.postDataJSON() })

    await route.fulfill({
      status: 200,
      headers: { ...CORS, 'Content-Type': 'application/json' },
      body: JSON.stringify(
        path === '/health' ? { version: 'sinov', codePage: 'cp1252', printers: [] } : { ok: true },
      ),
    })
  })

  return sent
}

/** `window.print` chaqiruvlarini sanaydi — haqiqiy oyna ochilmaydi. */
async function countPrints(page: Page) {
  await page.addInitScript(() => {
    const counter = window as unknown as { printCalls: number }

    counter.printCalls = 0
    window.print = () => {
      counter.printCalls += 1
    }
  })
}

function printCalls(page: Page) {
  return page.evaluate(() => (window as unknown as { printCalls: number }).printCalls)
}

/** Sahifadagi qatorning javon manzillari: `D1`, `D2`… */
async function runCells(page: Page, code: string) {
  const run = page.locator('.run', { has: page.locator('.run-letter', { hasText: code }) })

  return (await run.locator('.shelf-cell').allTextContents()).map((cell) => cell.trim())
}

test('hamma javonning yorlig‘i bitta bosishda printerga ketadi', async ({ page }) => {
  const sent = await agentOnline(page)

  await countPrints(page)
  await openApp(page, admin, '/warehouse', { agent: 'fake' })
  await expect(page.locator('.shelf').first()).toBeVisible()

  const total = await page.locator('.shelf').count()

  // Ko'p yorliq so'ralmasdan chiqib ketmasin
  let question = ''

  page.once('dialog', (dialog) => {
    question = dialog.message()
    void dialog.accept()
  })

  await page.getByRole('button', { name: 'Yorliqlarni chop etish' }).click()

  await expect(page.getByText(`${total} ta javon yorlig‘i printerga yuborildi`)).toBeVisible()
  expect(question).toContain(`${total} ta yorliq`)

  const jobs = sent.filter((item) => item.path === '/shelf-labels')

  expect(jobs).toHaveLength(1)
  expect(jobs[0]!.body.labels).toHaveLength(total)
  expect(jobs[0]!.body.labels[0]).toEqual({ cell: 'A1', quantity: 1 })
  expect(jobs[0]!.body).toMatchObject({ widthMm: 40, heightMm: 30, textMm: 12 })

  // Agent ishlagan — brauzer oynasi ochilmaydi
  expect(await printCalls(page)).toBe(0)
})

test('bitta qatorning yorliqlari', async ({ page }) => {
  const sent = await agentOnline(page)

  await openApp(page, admin, '/warehouse', { agent: 'fake' })
  await expect(page.locator('.shelf').first()).toBeVisible()

  const cells = await runCells(page, 'D')

  page.once('dialog', (dialog) => void dialog.accept())

  await page.getByRole('button', { name: 'D qatorining yorliqlarini chop etish' }).click()

  await expect(page.getByText(`${cells.length} ta javon yorlig‘i`)).toBeVisible()

  const job = sent.find((item) => item.path === '/shelf-labels')!.body

  expect(job.labels.map((label) => label.cell)).toEqual(cells)
})

test('bitta javonning yorlig‘i so‘ramasdan chiqadi', async ({ page }) => {
  const sent = await agentOnline(page)

  await openApp(page, admin, '/warehouse', { agent: 'fake' })

  // Bitta yorliq uchun tasdiq so'ralmaydi
  const questions: string[] = []

  page.on('dialog', (dialog) => {
    questions.push(dialog.message())
    void dialog.accept()
  })

  await page.getByRole('button', { name: /^C3:/ }).click()
  await page.getByRole('button', { name: 'Yorlig‘ini chop etish' }).click()

  await expect(page.getByText('1 ta javon yorlig‘i printerga yuborildi')).toBeVisible()

  const job = sent.find((item) => item.path === '/shelf-labels')!.body

  expect(job.labels).toEqual([{ cell: 'C3', quantity: 1 }])
  expect(questions).toEqual([])
})

test('tasdiqlanmasa hech narsa chiqmaydi', async ({ page }) => {
  const sent = await agentOnline(page)

  await countPrints(page)
  await openApp(page, admin, '/warehouse', { agent: 'fake' })
  await expect(page.locator('.shelf').first()).toBeVisible()

  page.once('dialog', (dialog) => void dialog.dismiss())

  await page.getByRole('button', { name: 'Yorliqlarni chop etish' }).click()

  // Bekor qilingan — agentga ham, brauzerga ham hech narsa bormaydi
  await page.waitForTimeout(300)

  expect(sent.filter((item) => item.path === '/shelf-labels')).toHaveLength(0)
  expect(await printCalls(page)).toBe(0)
})

test('agent bo‘lmasa yorliq brauzer orqali chiqadi', async ({ page }) => {
  await countPrints(page)
  await openApp(page, admin, '/warehouse')

  await page.getByRole('button', { name: /^B2:/ }).click()
  await page.getByRole('button', { name: 'Yorlig‘ini chop etish' }).click()

  await expect.poll(() => printCalls(page)).toBe(1)

  // Varaqda bitta yorliq va unda faqat manzil
  const label = page.locator('.shelf-labels .shelf-label')

  await expect(label).toHaveCount(1)
  await expect(label).toHaveText('B2')

  // Qog'oz o'lchami yorliq o'lchamiga teng. <head> dagi <style> ko'rinmaydi,
  // shuning uchun matni to'g'ridan-to'g'ri o'qiladi
  const pageCss = await page.evaluate(() => document.getElementById('print-page')?.textContent)

  expect(pageCss).toContain('size: 40mm 30mm')
})
