/**
 * Testlar uchun ma'lumot: qoldig'i bor variantlar.
 *
 * Namuna ma'lumotdagi qoldiq har yurgizishda sotuv bilan kamayadi va bir
 * necha yurgizishdan keyin tugab qoladi — testlar esa "tovar yo'q" deb
 * yiqiladi (shunday bo'ldi: bazada 4 ta qoldiqli variant qolgan edi).
 * Shuning uchun kerakli qoldiqni test o'zi kirim bilan to'ldiradi.
 */

import { expect, type APIRequestContext } from '@playwright/test'

export interface TestVariant {
  id: number
  barcode: string
  price: string
  stock_quantity: number
}

/** `count` ta faol variant; qoldig'i yo'qlari bittadan to'ldiriladi. */
export async function stockedVariants(
  request: APIRequestContext,
  api: string,
  access: string,
  count: number,
): Promise<TestVariant[]> {
  const headers = { Authorization: `Bearer ${access}` }
  const found: TestVariant[] = []

  let url: string | null = `${api}/api/variants/?active=true`

  while (url && found.length < count) {
    const page: { results: TestVariant[]; next: string | null } = await (
      await request.get(url, { headers })
    ).json()

    found.push(...page.results)
    url = page.next
  }

  const chosen = found.slice(0, count)

  expect(chosen.length, `kamida ${count} ta faol tovar kerak — seed_demo`).toBe(count)

  const empty = chosen.filter((variant) => variant.stock_quantity < 1)

  if (empty.length) {
    const purchase = await (
      await request.post(`${api}/api/purchases/`, {
        headers,
        data: {
          date: new Date().toISOString().slice(0, 10),
          supplier: null,
          note: 'Test uchun qoldiq',
          lines: empty.map((variant) => ({
            variant: variant.id,
            quantity: 1,
            unit_cost: '10000',
          })),
        },
      })
    ).json()

    const confirmed = await request.post(`${api}/api/purchases/${purchase.id}/confirm/`, {
      headers,
    })

    expect(confirmed.ok(), 'test uchun kirim tasdiqlanishi kerak').toBeTruthy()
  }

  return chosen
}
