/**
 * UI testlari uchun umumiy yordamchilar: kirish, ilovani ochish va
 * testning o'z ma'lumoti (mahsulot, qoldiq, sotuv).
 *
 * Namuna ma'lumotdagi qoldiq har yurgizishda sotuv bilan kamayadi va bir
 * necha yurgizishdan keyin tugab qoladi — testlar esa "tovar yo'q" deb
 * yiqiladi (shunday bo'ldi: bazada 4 ta qoldiqli variant qolgan edi).
 * Shuning uchun kerakli ma'lumotni test o'zi yaratadi.
 *
 * Diqqat: testlar ular ulangan bazada mahsulot, kirim va sotuv yaratadi —
 * faqat ishlab chiqish bazasiga qarshi yurgiziladi.
 */

import { expect, type APIRequestContext, type Page } from '@playwright/test'

/** Backend manzili — `playwright.config.ts` dagi bilan bir xil manba */
export const API = process.env.VITE_API_TARGET ?? 'http://127.0.0.1:8000'

/** seed_demo dagi parol */
const PASSWORD = 'demo12345'

export interface Session {
  access: string
  refresh: string
}

export interface Named {
  id: number
  name: string
}

export interface StockAt {
  location: number
  kind: 'warehouse' | 'shop'
  quantity: number
}

export interface TestVariant {
  id: number
  barcode: string
  price: string
  /** Ikkala joyning yig'indisi */
  stock_quantity: number
  stocks: StockAt[]
}

/** Savdo zalidagi qoldiq — kassa faqat shuni sotadi. */
export function shopQuantity(variant: TestVariant): number {
  return (variant.stocks ?? [])
    .filter((stock) => stock.kind === 'shop')
    .reduce((sum, stock) => sum + stock.quantity, 0)
}

export interface TestProduct extends Named {
  sizes: Named[]
  colors: Named[]
  /** Qoldiq kiritilgan kirim — tarixdagi havolani tekshirish uchun */
  purchase: { id: number; number: string }
}

export async function login(request: APIRequestContext, username = 'admin'): Promise<Session> {
  const response = await request.post(`${API}/api/auth/login/`, {
    data: { username, password: PASSWORD },
  })

  expect(response.ok(), `Backend ${API} da «${username}» kira olmadi — seed_demo ishga tushirilganmi?`)
    .toBeTruthy()

  const body = await response.json()

  return { access: body.access, refresh: body.refresh }
}

/** Chop etish agentining manzili — brauzerdan shu yerga murojaat qilinadi */
const AGENT = 'http://127.0.0.1:7777/**'

/**
 * Tokenlarni brauzerga qo'yib, sahifani ochadi.
 *
 * Standart holda chop etish agenti «yo'q» deb javob beradi: testlarning
 * ko'pi chop etishga aloqador emas. Agent bilan ishlaydigan test
 * `agent: 'fake'` beradi va marshrutni o'zi belgilaydi.
 */
export async function openApp(
  page: Page,
  session: Session,
  path: string,
  { agent = 'off' }: { agent?: 'off' | 'fake' } = {},
) {
  await page.addInitScript(
    ([access, refresh]) => {
      localStorage.setItem('access_token', access as string)
      localStorage.setItem('refresh_token', refresh as string)
    },
    [session.access, session.refresh],
  )

  if (agent === 'off') {
    await page.route(AGENT, (route) => route.abort('connectionrefused'))
  }

  await page.goto(path)
}

/**
 * Ishlayotgan chop etish agentini taqlid qiladi.
 *
 * `openApp` dan OLDIN chaqiriladi va unga `agent: 'fake'` beriladi.
 * Qaytgan ro'yxatga agent qabul qilgan yo'llar tushadi: `/health`,
 * `/receipt`, `/labels`.
 */
export async function fakeAgent(page: Page, { upFrom = 0 } = {}): Promise<string[]> {
  const calls: string[] = []

  await page.route(AGENT, async (route) => {
    // `upFrom` — agent shuncha so'rovdan keyin ko'tariladi. Kun boshida
    // brauzer agentdan oldin ochilgan holatni shunday sinaymiz.
    if (calls.length < upFrom) {
      calls.push('yiqilgan')
      return route.abort('connectionrefused')
    }

    calls.push(new URL(route.request().url()).pathname)

    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ version: 'sinov', codePage: 'cp1252', printers: [] }),
    })
  })

  return calls
}

function headers(access: string) {
  return { Authorization: `Bearer ${access}` }
}

/** `count` ta faol variant; qoldig'i yo'qlari bittadan to'ldiriladi. */
export async function stockedVariants(
  request: APIRequestContext,
  api: string,
  access: string,
  count: number,
): Promise<TestVariant[]> {
  const found: TestVariant[] = []

  let url: string | null = `${api}/api/variants/?active=true`

  while (url && found.length < count) {
    const page: { results: TestVariant[]; next: string | null } = await (
      await request.get(url, { headers: headers(access) })
    ).json()

    found.push(...page.results)
    url = page.next
  }

  const chosen = found.slice(0, count)

  expect(chosen.length, `kamida ${count} ta faol tovar kerak — seed_demo`).toBe(count)

  // Kirim omborga tushadi — kassa uchun zalda bo'lishi kerak
  const empty = chosen.filter((variant) => shopQuantity(variant) < 1)

  if (empty.length) {
    await receive(request, access, empty.map((variant) => ({ variant: variant.id, quantity: 1 })))
  }

  return chosen
}

/**
 * Sinov uchun kichik PNG.
 *
 * Tovarga rasm majburiy, shuning uchun interfeys orqali tovar
 * yaratadigan testlar shu faylni biriktiradi. Mazmuni muhim emas.
 */
export function testPhoto() {
  return {
    name: 'rasm.png',
    mimeType: 'image/png',
    buffer: Buffer.from(
      'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==',
      'base64',
    ),
  }
}

/** Joylar ro'yxati: ombor va savdo zali. */
export async function locations(
  request: APIRequestContext,
  access: string,
): Promise<{ id: number; kind: 'warehouse' | 'shop' }[]> {
  return (await request.get(`${API}/api/locations/`, { headers: headers(access) })).json()
}

/** Ombordan zalga chiqaradi — javonni to'ldirish. */
export async function moveToShop(
  request: APIRequestContext,
  access: string,
  lines: { variant: number; quantity: number }[],
): Promise<{ id: number; number: string }> {
  const places = await locations(request, access)

  const response = await request.post(`${API}/api/transfers/`, {
    headers: headers(access),
    data: {
      source: places.find((place) => place.kind === 'warehouse')!.id,
      target: places.find((place) => place.kind === 'shop')!.id,
      lines,
    },
  })

  expect(response.ok(), `zalga chiqarilmadi: ${await response.text()}`).toBeTruthy()

  return response.json()
}

/**
 * Tasdiqlangan kirim.
 *
 * Tovar avval omborga tushadi. Testlarning ko'pi sotuvni tekshiradi,
 * shuning uchun standart holda darhol zalga ham chiqariladi.
 */
async function receive(
  request: APIRequestContext,
  access: string,
  lines: { variant: number; quantity: number }[],
  { toShop = true } = {},
): Promise<{ id: number; number: string }> {
  const purchase = await (
    await request.post(`${API}/api/purchases/`, {
      headers: headers(access),
      data: {
        date: new Date().toISOString().slice(0, 10),
        supplier: null,
        note: 'Test uchun qoldiq',
        lines: lines.map((line) => ({ ...line, unit_cost: '100000' })),
      },
    })
  ).json()

  const confirmed = await request.post(`${API}/api/purchases/${purchase.id}/confirm/`, {
    headers: headers(access),
  })

  expect(confirmed.ok(), 'test uchun kirim tasdiqlanishi kerak').toBeTruthy()

  if (toShop) await moveToShop(request, access, lines)

  return { id: purchase.id, number: purchase.number }
}

/**
 * Uch o'lcham × ikki rangli mahsulot. Qoldiq:
 *   1-rang: 1-o'lcham 2, 3-o'lcham 5
 *   2-rang: 1-o'lcham 1
 * Ya'ni o'lchamlar bo'yicha jami: 3 · 0 · 5, hammasi 8 dona.
 */
export async function createTestProduct(
  request: APIRequestContext,
  session: Session,
): Promise<TestProduct> {
  const get = async (path: string) =>
    (await request.get(`${API}${path}`, { headers: headers(session.access) })).json()

  const categories = await get('/api/categories/')
  const sizes: Named[] = (await get('/api/sizes/')).slice(0, 3)
  const colors: Named[] = (await get('/api/colors/')).slice(0, 2)

  expect(sizes.length, 'kamida 3 ta o‘lcham kerak — seed_demo').toBe(3)
  expect(colors.length, 'kamida 2 ta rang kerak — seed_demo').toBe(2)

  const name = `Sinov mahsuloti ${Date.now()}`

  const created = await (
    await request.post(`${API}/api/products/`, {
      headers: headers(session.access),
      data: {
        category: categories[0].id,
        name,
        sale_price: '250000',
        material: '95% paxta, 5% elastan',
        size_ids: sizes.map((size) => size.id),
        color_ids: colors.map((color) => color.id),
      },
    })
  ).json()

  const variant = (size: number, color: number): number =>
    created.variants.find(
      (item: { size: number; color: number }) =>
        item.size === sizes[size]!.id && item.color === colors[color]!.id,
    ).id

  const purchase = await receive(request, session.access, [
    { variant: variant(0, 0), quantity: 2 },
    { variant: variant(2, 0), quantity: 5 },
    { variant: variant(0, 1), quantity: 1 },
  ])

  return { id: created.id, name, sizes, colors, purchase }
}

/** Tovarning zaldagi hamma qoldig'ini omborga qaytaradi. */
export async function moveToWarehouse(
  request: APIRequestContext,
  session: Session,
  product: TestProduct,
): Promise<void> {
  const full = await (
    await request.get(`${API}/api/products/${product.id}/`, {
      headers: headers(session.access),
    })
  ).json()

  const lines = full.variants
    .map((variant: TestVariant) => ({
      variant: variant.id,
      quantity: shopQuantity(variant),
    }))
    .filter((line: { quantity: number }) => line.quantity > 0)

  if (!lines.length) return

  const places = await locations(request, session.access)

  const response = await request.post(`${API}/api/transfers/`, {
    headers: headers(session.access),
    data: {
      source: places.find((place) => place.kind === 'shop')!.id,
      target: places.find((place) => place.kind === 'warehouse')!.id,
      lines,
    },
  })

  expect(response.ok(), `omborga qaytarilmadi: ${await response.text()}`).toBeTruthy()
}

/**
 * Faqat omborda turgan variant: zalda nol, omborda `quantity` dona.
 *
 * Kassadagi «Ombordan olib chiqish» va «Zalga chiqarish» ekranlari shu
 * holatni tekshiradi.
 */
export async function stockInWarehouseOnly(
  request: APIRequestContext,
  session: Session,
  product: TestProduct,
  quantity = 3,
): Promise<{ id: number; barcode: string; size: string; color: string }> {
  const full = await (
    await request.get(`${API}/api/products/${product.id}/`, {
      headers: headers(session.access),
    })
  ).json()

  const variant = full.variants.find(
    (item: TestVariant) => item.stock_quantity === 0,
  )

  expect(variant, 'qoldiqsiz variant topilmadi').toBeTruthy()

  await receive(request, session.access, [{ variant: variant.id, quantity }], { toShop: false })

  return {
    id: variant.id,
    barcode: variant.barcode,
    size: variant.size_name,
    color: variant.color_name,
  }
}

/**
 * O'lchamsiz va rangsiz tovar — taqinchoq, ro'mol va shunga o'xshash.
 *
 * Bitta variant, bitta shtrix-kod. Qoldiq savdo zalida.
 */
export async function createSimpleProduct(
  request: APIRequestContext,
  session: Session,
): Promise<{ id: number; name: string; variant: number; barcode: string }> {
  const categories = await (
    await request.get(`${API}/api/categories/`, { headers: headers(session.access) })
  ).json()

  const name = `Uzuk ${Date.now()}`

  const created = await (
    await request.post(`${API}/api/products/`, {
      headers: headers(session.access),
      data: { category: categories[0].id, name, sale_price: '150000' },
    })
  ).json()

  const variant = created.variants[0]

  await receive(request, session.access, [{ variant: variant.id, quantity: 3 }])

  return { id: created.id, name, variant: variant.id, barcode: variant.barcode }
}

/** Bitta qatorli, naqd to'langan sotuv. Chek raqamini qaytaradi. */
export async function createSale(request: APIRequestContext, session: Session): Promise<string> {
  const [variant] = await stockedVariants(request, API, session.access, 1)

  const response = await request.post(`${API}/api/sales/`, {
    headers: headers(session.access),
    data: {
      lines: [{ variant: variant!.id, quantity: 1 }],
      cash_amount: variant!.price,
      card_amount: '0.00',
      request_key: crypto.randomUUID(),
    },
  })

  expect(response.ok(), `sotuv yaratilmadi: ${await response.text()}`).toBeTruthy()

  return (await response.json()).number
}
