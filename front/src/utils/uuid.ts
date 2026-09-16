/**
 * Bir martalik kalit (UUID v4).
 *
 * `crypto.randomUUID` faqat xavfsiz kontekstda (HTTPS yoki localhost)
 * mavjud. Do'kon kompyuteri ichki tarmoqda oddiy HTTP orqali ishlashi
 * mumkin, shuning uchun zaxira yo'l ham bor.
 */
export function uuid(): string {
  const source = globalThis.crypto

  if (source && typeof source.randomUUID === 'function') {
    return source.randomUUID()
  }

  if (source && typeof source.getRandomValues === 'function') {
    const bytes = source.getRandomValues(new Uint8Array(16))

    // RFC 4122: versiya 4 va variant belgilaridan tashqari hammasi tasodifiy
    bytes[6] = (bytes[6]! & 0x0f) | 0x40
    bytes[8] = (bytes[8]! & 0x3f) | 0x80

    const hex = [...bytes].map((byte) => byte.toString(16).padStart(2, '0')).join('')

    return `${hex.slice(0, 8)}-${hex.slice(8, 12)}-${hex.slice(12, 16)}-${hex.slice(16, 20)}-${hex.slice(20)}`
  }

  // Oxirgi chora: kriptografik emas, lekin takrorlanish ehtimoli juda kichik
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (char) => {
    const random = (Math.random() * 16) | 0
    const value = char === 'x' ? random : (random & 0x3) | 0x8

    return value.toString(16)
  })
}
