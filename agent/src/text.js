/**
 * Matnni printer tushunadigan ko'rinishga keltiradi.
 *
 * Muammo: o'zbek lotin alifbosida `oʻ`, `gʻ` va `ʼ` uchun maxsus
 * Unicode belgilar ishlatiladi (U+02BB, U+02BC, U+2018...). Chek
 * printeri esa bir baytli kod sahifasida ishlaydi va bu belgilarni
 * bilmaydi — ular o'rniga tasodifiy belgi yoki bo'shliq chiqadi.
 *
 * Shuning uchun avval hammasi oddiy apostrofga keltiriladi, keyin
 * kod sahifasiga o'giriladi; sahifada yo'q belgi tashlab yuboriladi.
 */

/** Maxsus belgilar → oddiy ASCII */
const REPLACEMENTS = new Map([
  // O'zbekcha tutuq belgilari
  ['ʻ', "'"], // ʻ  (o'zbekcha oʻ, gʻ)
  ['ʼ', "'"], // ʼ
  ['ʹ', "'"],
  ['‘', "'"], // '
  ['’', "'"], // '
  ['‛', "'"],
  ['´', "'"],
  ['`', "'"],
  // Qo'shtirnoqlar
  ['“', '"'],
  ['”', '"'],
  ['„', '"'],
  ['«', '"'],
  ['»', '"'],
  // Tire va bo'shliqlar
  ['–', '-'],
  ['—', '-'],
  ['−', '-'],
  [' ', ' '], // uzilmas bo'shliq
  [' ', ' '],
  [' ', ' '],
  // Uch nuqta
  ['…', '...'],
])

/** CP1252 da 0x80-0x9F oralig'idagi belgilar */
const CP1252_HIGH = new Map([
  ['€', 0x80], ['‚', 0x82], ['ƒ', 0x83], ['„', 0x84],
  ['…', 0x85], ['†', 0x86], ['‡', 0x87], ['ˆ', 0x88],
  ['‰', 0x89], ['Š', 0x8a], ['‹', 0x8b], ['Œ', 0x8c],
  ['Ž', 0x8e], ['‘', 0x91], ['’', 0x92], ['“', 0x93],
  ['”', 0x94], ['•', 0x95], ['–', 0x96], ['—', 0x97],
  ['˜', 0x98], ['™', 0x99], ['š', 0x9a], ['›', 0x9b],
  ['œ', 0x9c], ['ž', 0x9e], ['Ÿ', 0x9f],
])

/** Kod sahifasini tanlash buyrug'i uchun raqam (ESC t n) */
export const CODE_PAGES = {
  cp437: 0,
  cp1252: 16,
  ascii: 0,
}

/**
 * Maxsus belgilarni oddiysiga almashtiradi.
 *
 * Bu bosqich kod sahifasidan qat'i nazar bajariladi: `oʻ` har qanday
 * holatda ham `o'` bo'lib chiqishi kerak.
 */
export function normalize(text) {
  if (text === null || text === undefined) return ''

  let result = String(text)

  for (const [from, to] of REPLACEMENTS) {
    result = result.split(from).join(to)
  }

  return result
}

/**
 * Matnni bayt qatoriga o'giradi.
 *
 * Kod sahifasida yo'q belgi tashlab yuboriladi — yarim tanilgan belgi
 * chop etilgandan ko'ra yo'qligi tushunarliroq.
 */
export function encode(text, codePage = 'cp1252') {
  const normalized = normalize(text)
  const bytes = []

  for (const character of normalized) {
    const code = character.codePointAt(0)

    // Boshqaruv belgilari va oddiy ASCII
    if (code <= 0x7f) {
      bytes.push(code)
      continue
    }

    if (codePage === 'ascii') continue

    if (codePage === 'cp1252') {
      const high = CP1252_HIGH.get(character)

      if (high !== undefined) {
        bytes.push(high)
        continue
      }

      // 0xA0-0xFF: CP1252 va Latin-1 bir xil
      if (code >= 0xa0 && code <= 0xff) {
        bytes.push(code)
        continue
      }
    }

    // Sahifada yo'q — tashlab yuboriladi
  }

  return Buffer.from(bytes)
}

/** Matnni ustun kengligiga qarab satrlarga bo'ladi. */
export function wrap(text, columns) {
  const words = normalize(text).split(/\s+/).filter(Boolean)
  const lines = []

  let current = ''

  for (const word of words) {
    if (!current) {
      current = word
    } else if (current.length + 1 + word.length <= columns) {
      current += ` ${word}`
    } else {
      lines.push(current)
      current = word
    }

    // Bitta so'z ustundan uzun bo'lsa, bo'lib tashlaymiz
    while (current.length > columns) {
      lines.push(current.slice(0, columns))
      current = current.slice(columns)
    }
  }

  if (current) lines.push(current)

  return lines.length ? lines : ['']
}

/**
 * Chap va o'ng ustun: nom chapda, summa o'ngda.
 *
 * Ikkalasi sig'masa, nom yuqorida alohida satrda qoladi va summa
 * pastda o'ngga tekislanadi — summa hech qachon kesilmaydi.
 */
export function twoColumns(left, right, columns) {
  const start = normalize(left)
  const end = normalize(right)

  if (start.length + end.length + 1 <= columns) {
    return [start + ' '.repeat(columns - start.length - end.length) + end]
  }

  const lines = wrap(start, columns)

  lines.push(' '.repeat(Math.max(0, columns - end.length)) + end)

  return lines
}

/** Summani "450 000" ko'rinishida yozadi (oddiy bo'shliq bilan). */
export function formatAmount(value) {
  const number = Number(value ?? 0)

  if (!Number.isFinite(number)) return '0'

  const rounded = Math.round(number * 100) / 100
  const [whole, fraction] = rounded.toFixed(2).split('.')
  const grouped = whole.replace(/\B(?=(\d{3})+(?!\d))/g, ' ')

  return fraction === '00' ? grouped : `${grouped},${fraction}`
}
