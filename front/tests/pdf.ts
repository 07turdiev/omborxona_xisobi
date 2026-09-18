/**
 * PDF ni tekshirish: sahifa soni, o'lchami, chizg'ich uzunligi va
 * mazmunning sahifadagi o'rni.
 *
 * O'lchovlar aynan **rasterlangan** tasvirdan olinadi, chunki
 * brauzerdagi o'lchov yolg'on xotirjamlik beradi: sahifa qog'ozga
 * sig'masa, Chromium butun chizmani kichraytiradi va buni faqat
 * chiqqan PDF da ko'rish mumkin.
 */

import { createCanvas } from '@napi-rs/canvas'

/** Chek va yorliq printerlarining zichligi */
export const PRINTER_DPI = 203

const PT_PER_INCH = 72
const MM_PER_INCH = 25.4

export interface PageSize {
  widthMm: number
  heightMm: number
}

export interface PdfInfo {
  pages: number
  size: PageSize
}

function ptToMm(pt: number): number {
  return Math.round(((pt * MM_PER_INCH) / PT_PER_INCH) * 100) / 100
}

function pxToMm(px: number, dpi: number): number {
  return Math.round((px / dpi) * MM_PER_INCH * 100) / 100
}

async function loadPdf(data: Buffer) {
  // `legacy` qurilishi Node uchun mo'ljallangan
  const pdfjs = await import('pdfjs-dist/legacy/build/pdf.mjs')

  return pdfjs.getDocument({
    data: new Uint8Array(data),
    isEvalSupported: false,
    disableFontFace: true,
  }).promise
}

/** Sahifalar soni va birinchi sahifaning o'lchami (mm). */
export async function readPdf(data: Buffer): Promise<PdfInfo> {
  const doc = await loadPdf(data)
  const page = await doc.getPage(1)
  const viewport = page.getViewport({ scale: 1 })

  return {
    pages: doc.numPages,
    size: { widthMm: ptToMm(viewport.width), heightMm: ptToMm(viewport.height) },
  }
}

interface Raster {
  width: number
  height: number
  pixels: Uint8ClampedArray
}

/** Sahifani berilgan zichlikda rasterlaydi. */
async function rasterize(data: Buffer, pageNumber: number, dpi: number): Promise<Raster> {
  const doc = await loadPdf(data)
  const page = await doc.getPage(pageNumber)

  const viewport = page.getViewport({ scale: dpi / PT_PER_INCH })
  const width = Math.ceil(viewport.width)
  const height = Math.ceil(viewport.height)

  const canvas = createCanvas(width, height)
  const context = canvas.getContext('2d')

  // Oq fon: shaffof joylar qora deb hisoblanmasin
  context.fillStyle = '#ffffff'
  context.fillRect(0, 0, width, height)

  await page.render({
    canvas: canvas as unknown as HTMLCanvasElement,
    canvasContext: context as unknown as CanvasRenderingContext2D,
    viewport,
  }).promise

  return { width, height, pixels: context.getImageData(0, 0, width, height).data }
}

function isDark(raster: Raster, x: number, y: number): boolean {
  const index = (y * raster.width + x) * 4

  return (raster.pixels[index]! + raster.pixels[index + 1]! + raster.pixels[index + 2]!) / 3 < 128
}

/**
 * Birinchi sahifadagi eng uzun **uzluksiz** qora chiziqni mm da qaytaradi.
 *
 * Bu — chizg'ich. Yorliq ramkasi undan kengroq (sahifaning butun eni),
 * shuning uchun sahifa enining 90 % idan uzun chiziqlar hisobga
 * olinmaydi. Shtrix-kod chiziqlari tik, ya'ni gorizontal o'lchovda
 * qisqa bo'lagi tushadi; chekdagi punktir chiziqlar ham uzluksiz emas.
 */
export async function longestRulerMm(data: Buffer, dpi: number = PRINTER_DPI): Promise<number> {
  const raster = await rasterize(data, 1, dpi)
  const limit = raster.width * 0.9

  let longest = 0

  for (let y = 0; y < raster.height; y += 1) {
    let run = 0

    for (let x = 0; x < raster.width; x += 1) {
      if (isDark(raster, x, y)) {
        run += 1
      } else {
        if (run <= limit) longest = Math.max(longest, run)
        run = 0
      }
    }

    if (run <= limit) longest = Math.max(longest, run)
  }

  return pxToMm(longest, dpi)
}

/**
 * Sahifaning tepasidan birinchi qora piksel qayerda (mm).
 *
 * Mazmun tepadan boshlanishi kerak: brauzer uni sahifa o'rtasiga
 * tushirsa, chek boshida ortiqcha bo'sh lenta chiqadi.
 */
export async function firstInkRowMm(
  data: Buffer,
  pageNumber = 1,
  dpi: number = PRINTER_DPI,
): Promise<number> {
  const raster = await rasterize(data, pageNumber, dpi)

  for (let y = 0; y < raster.height; y += 1) {
    for (let x = 0; x < raster.width; x += 1) {
      if (isDark(raster, x, y)) return pxToMm(y, dpi)
    }
  }

  return Number.POSITIVE_INFINITY
}

/** Sahifada umuman chop etiladigan narsa bormi (bo'sh sahifa emasmi). */
export async function pageHasInk(
  data: Buffer,
  pageNumber: number,
  dpi: number = PRINTER_DPI,
): Promise<boolean> {
  const raster = await rasterize(data, pageNumber, dpi)

  for (let y = 0; y < raster.height; y += 1) {
    for (let x = 0; x < raster.width; x += 1) {
      if (isDark(raster, x, y)) return true
    }
  }

  return false
}
