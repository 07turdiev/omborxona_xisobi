/**
 * Sozlamani standart qiymatlar bilan birlashtirish.
 *
 * Nega alohida modul kerak bo'ldi: `{ ...DEFAULTS, ...options }` yozuvida
 * sozlamada **yo'q** kalit ham `undefined` qiymat bilan ko'chib o'tadi va
 * standartni bosib ketadi. Natijada to'liq bo'lmagan `config.json` da
 * chek shtrix-kodsiz (`GS h 0`) va kesilmasdan (`ESC d 0`) chiqardi,
 * yorliqqa esa `DENSITY undefined` yozilardi.
 */

/** `undefined` va `null` qiymatlarni tashlaydi; `0` va `false` qoladi. */
export function defined(options = {}) {
  const result = {}

  for (const [key, value] of Object.entries(options)) {
    if (value !== undefined && value !== null) result[key] = value
  }

  return result
}

function show(value) {
  return typeof value === 'string' ? `"${value}"` : String(value)
}

/**
 * Standart qiymatlar ustiga sozlamani qo'yadi va sonlarni tekshiradi.
 *
 * Noto'g'ri qiymat jimgina o'tib ketmaydi: standart qiymat olinadi va
 * qaysi printerda qaysi sozlama buzilgani konsolga yoziladi.
 *
 * @param {object} defaults - standart qiymatlar
 * @param {object} options - sozlamadagi qiymatlar
 * @param {object} rules - `{ positive: [...], nonNegative: [...] }`
 * @param {string} where - ogohlantirishda ko'rsatiladigan printer nomi
 */
export function merge(defaults, options, rules = {}, where = 'printer') {
  const settings = { ...defaults, ...defined(options) }

  const check = (key, ok, expected) => {
    const value = Number(settings[key])

    if (Number.isFinite(value) && ok(value)) {
      // Matn ko'rinishidagi son ham qabul qilinadi: "48" → 48
      settings[key] = value
      return
    }

    console.warn(
      `${where}: "${key}" ${expected} bo'lishi kerak, ` +
        `${show(settings[key])} berilgan — standart qiymat olindi (${defaults[key]})`,
    )

    settings[key] = defaults[key]
  }

  for (const key of rules.positive ?? []) {
    check(key, (value) => value > 0, 'musbat son')
  }

  for (const key of rules.nonNegative ?? []) {
    check(key, (value) => value >= 0, "manfiy bo'lmagan son")
  }

  return settings
}
