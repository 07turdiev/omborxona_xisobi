/** Inventarizatsiya: skanerlangan kodni sanoq ro'yxatidan topish. */

export interface CountLine {
  variant: number
  barcode: string
  product_name: string
  variant_label: string
  expected_quantity: number
  counted_quantity: number
}

export type ScanResult = { ok: true; index: number } | { ok: false; message: string }

/**
 * Skanerlangan shtrix-kod qaysi qatorga tegishli.
 *
 * Topilmasa — sabab aytiladi: kod noma'lum bo'lishi yoki tovar tanlangan
 * kategoriyaga kirmasligi mumkin. Ikkalasi ham xato: sanoqchi buni
 * darhol ko'rishi kerak.
 */
export function findScanned(lines: CountLine[], code: string): ScanResult {
  const cleaned = code.trim()

  if (!cleaned) {
    return { ok: false, message: 'Kod bo‘sh.' }
  }

  const index = lines.findIndex((line) => line.barcode === cleaned)

  if (index === -1) {
    return {
      ok: false,
      message: `«${cleaned}» — bu ro‘yxatda yo‘q: noma’lum shtrix-kod yoki boshqa kategoriya tovari.`,
    }
  }

  return { ok: true, index }
}

/** Hali umuman sanalmagan (0 turgan) qatorlar soni. */
export function uncountedLines(lines: CountLine[]): number {
  return lines.filter((line) => line.counted_quantity === 0).length
}

/** Tizimdagi qoldiqdan farq qiladigan qatorlar soni. */
export function differingLines(lines: CountLine[]): number {
  return lines.filter((line) => line.counted_quantity !== line.expected_quantity).length
}
