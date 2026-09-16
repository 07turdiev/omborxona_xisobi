/**
 * Sanalar bilan ishlash. Hamma joyda mahalliy sana (Toshkent vaqti)
 * ishlatiladi: server ham hisobotlarni mahalliy kun bo'yicha yig'adi.
 */

function iso(date: Date): string {
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')

  return `${date.getFullYear()}-${month}-${day}`
}

export function todayIso(): string {
  return iso(new Date())
}

export function daysAgoIso(days: number): string {
  const date = new Date()

  date.setDate(date.getDate() - days)

  return iso(date)
}

export function monthStartIso(): string {
  const date = new Date()

  return iso(new Date(date.getFullYear(), date.getMonth(), 1))
}

/** 2026-09-16 → 16.09.2026 */
export function formatDate(value: string | null): string {
  if (!value) return '—'

  const [year, month, day] = value.slice(0, 10).split('-')

  return `${day}.${month}.${year}`
}

/** ISO vaqt → 16.09.2026 14:35 */
export function formatDateTime(value: string | null): string {
  if (!value) return '—'

  return new Date(value).toLocaleString('uz-UZ', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}
