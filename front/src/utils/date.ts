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


/** Oyning qisqa nomi — jadval va yorliqlar uchun */
const SHORT_MONTHS = [
  'yan', 'fev', 'mar', 'apr', 'may', 'iyn',
  'iyl', 'avg', 'sen', 'okt', 'noy', 'dek',
]

/**
 * Kun va oy: 2026-09-21 → «21-sen».
 *
 * Kirim ro'yxatida to'liq sana joy egallaydi va o'qishga og'ir:
 * hujjatlar odatda shu haftaniki bo'ladi.
 */
export function formatDayMonth(value: string | null): string {
  if (!value) return '—'

  const [, month, day] = value.slice(0, 10).split('-')
  const name = SHORT_MONTHS[Number(month) - 1]

  return name ? `${Number(day)}-${name}` : formatDate(value)
}

/** ISO vaqt → «17:40» */
export function formatTime(value: string | null): string {
  if (!value) return ''

  const date = new Date(value)

  return `${String(date.getHours()).padStart(2, '0')}:${String(date.getMinutes()).padStart(2, '0')}`
}
