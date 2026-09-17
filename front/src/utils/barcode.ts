/**
 * Shtrix-kod o'lchamlari — printerning nuqtalariga moslab.
 *
 * Termal printer rasmni nuqtalardan yig'adi: 203 dpi da bitta nuqta
 * 25.4 / 203 = 0.125 mm. Agar chiziq kengligi nuqtaga butun bo'linmasa,
 * printer uni yaxlitlaydi — ba'zi chiziqlar bir nuqtaga keng, ba'zilari
 * tor chiqadi va skaner kodni o'qiy olmay qoladi.
 *
 * Shuning uchun modul (eng tor chiziq) kengligi 0.25 mm qilib olingan:
 * bu roppa-rosa 2 nuqta.
 */

/** Yorliq va chek printerlarining zichligi */
export const PRINTER_DPI = 203

/** Bitta nuqta necha mm */
export const DOT_MM = 25.4 / PRINTER_DPI

/** Eng tor chiziq kengligi, mm (= 2 nuqta) */
export const MODULE_MM = 0.25

export type BarcodeFormat = 'EAN13' | 'CODE128'

/**
 * EAN-13 belgisi doim 95 modul:
 * 3 (chekka qo'riqchi) + 6×7 + 5 (o'rta qo'riqchi) + 6×7 + 3.
 */
export const EAN13_SYMBOL_MODULES = 95

/**
 * Tinch zona — kod atrofidagi bo'sh joy. Usiz skaner kodning qayerda
 * boshlanishini bilmaydi. Standart: EAN-13 da chapda 11, o'ngda 7 modul.
 */
export const QUIET_ZONES: Record<BarcodeFormat, { left: number; right: number }> = {
  EAN13: { left: 11, right: 7 },
  CODE128: { left: 10, right: 10 },
}

/** Tinch zonalar bilan birga umumiy modullar soni. */
export function totalModules(format: BarcodeFormat, symbolModules: number): number {
  const quiet = QUIET_ZONES[format]

  return quiet.left + symbolModules + quiet.right
}

/** Umumiy kenglik, mm. */
export function widthMm(modules: number, moduleMm: number = MODULE_MM): number {
  return Math.round(modules * moduleMm * 100) / 100
}

/** Bitta modul necha nuqtaga tushadi. */
export function dotsPerModule(moduleMm: number = MODULE_MM, dpi: number = PRINTER_DPI): number {
  return moduleMm / (25.4 / dpi)
}

/**
 * Modul kengligi nuqtalarga butun bo'linadimi.
 *
 * Yaxlitlash xatosi uchun kichik bag'rikenglik: 203 dpi da 0.25 mm
 * aslida 1.998 nuqta, bu amalda 2 nuqta demakdir.
 */
export function fitsPrinterDots(moduleMm: number = MODULE_MM, dpi: number = PRINTER_DPI): boolean {
  const dots = dotsPerModule(moduleMm, dpi)

  return Math.abs(dots - Math.round(dots)) < 0.02
}

/** Kod yorliqqa sig'adimi (chap va o'ng hoshiya bilan). */
export function fitsLabel(
  modules: number,
  labelWidthMm: number,
  moduleMm: number = MODULE_MM,
): boolean {
  return widthMm(modules, moduleMm) <= labelWidthMm
}
