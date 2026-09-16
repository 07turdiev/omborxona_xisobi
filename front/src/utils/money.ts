/**
 * Pul bilan ishlash — faqat satrlar orqali.
 *
 * `Number` yoki `parseFloat` ishlatilmaydi: 0.1 + 0.2 = 0.30000000000000004
 * bo'ladigan suzuvchi nuqta pulga yaramaydi. Hisob tiyinlarda (`bigint`)
 * bajariladi, natija yana satr bo'lib qaytadi — serverga ham shu ketadi.
 */

const ZERO = 0n

/** Guruh ajratuvchisi: uzilmaydigan probel, son qatorga bo'linmasin. */
const GROUP_SEPARATOR = ' '

/** Satrni tiyinga o'giradi: "450000.5" → 45000050n */
export function toCents(value: string | number | null | undefined): bigint {
  if (value === null || value === undefined || value === '') return ZERO

  const text = String(value).trim().replace(/\s| /g, '').replace(',', '.')
  const negative = text.startsWith('-')
  const digits = negative ? text.slice(1) : text

  if (!/^\d*(\.\d*)?$/.test(digits)) {
    throw new Error(`Noto'g'ri pul qiymati: ${value}`)
  }

  const [whole = '0', fraction = ''] = digits.split('.')
  const cents = BigInt(whole || '0') * 100n + BigInt((fraction + '00').slice(0, 2) || '0')

  return negative ? -cents : cents
}

/** Tiyinni satrga qaytaradi: 45000050n → "450000.50" */
export function fromCents(cents: bigint): string {
  const negative = cents < ZERO
  const absolute = negative ? -cents : cents

  const whole = absolute / 100n
  const fraction = absolute % 100n

  return `${negative ? '-' : ''}${whole}.${fraction.toString().padStart(2, '0')}`
}

export function addMoney(a: string, b: string): string {
  return fromCents(toCents(a) + toCents(b))
}

export function subtractMoney(a: string, b: string): string {
  return fromCents(toCents(a) - toCents(b))
}

/** Narxni butun songa ko'paytiradi (miqdor doim dona). */
export function multiplyMoney(value: string, quantity: number): string {
  return fromCents(toCents(value) * BigInt(Math.trunc(quantity)))
}

/**
 * Foizni hisoblaydi va tiyinga yaxlitlaydi (yarmi yuqoriga).
 * Serverdagi `ROUND_HALF_UP` bilan bir xil natija beradi.
 */
export function percentOf(value: string, percent: string): string {
  const scaled = toCents(value) * toCents(percent) // tiyin × (foiz × 100)
  const divisor = 10000n

  const negative = scaled < ZERO
  const absolute = negative ? -scaled : scaled

  const rounded = (absolute + divisor / 2n) / divisor

  return fromCents(negative ? -rounded : rounded)
}

export function compareMoney(a: string, b: string): number {
  const left = toCents(a)
  const right = toCents(b)

  if (left === right) return 0

  return left < right ? -1 : 1
}

export function isZero(value: string): boolean {
  return toCents(value) === ZERO
}

/**
 * Ekranga chiqarish: "450000.00" → "450 000".
 * Tiyin faqat nolga teng bo'lmaganda ko'rsatiladi.
 */
export function formatMoney(value: string | number | null | undefined): string {
  if (value === null || value === undefined || value === '') return '—'

  const cents = toCents(value)
  const negative = cents < ZERO
  const absolute = negative ? -cents : cents

  const whole = (absolute / 100n).toString()
  const fraction = absolute % 100n

  const grouped = whole.replace(/\B(?=(\d{3})+(?!\d))/g, GROUP_SEPARATOR)
  const tail = fraction === ZERO ? '' : `,${fraction.toString().padStart(2, '0')}`

  return `${negative ? '−' : ''}${grouped}${tail}`
}

/** Summa va valyuta: "450 000 so'm". */
export function formatSum(value: string | number | null | undefined): string {
  const formatted = formatMoney(value)

  return formatted === '—' ? formatted : `${formatted} so'm`
}

/**
 * Foydalanuvchi kiritgan matnni serverga yuboriladigan qiymatga aylantiradi:
 * "450 000,50" → "450000.50". Bo'sh qiymat "0" bo'ladi.
 */
export function normalizeMoneyInput(value: string): string {
  if (!value || !value.trim()) return '0'

  return fromCents(toCents(value))
}
