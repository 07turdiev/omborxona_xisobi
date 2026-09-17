/**
 * PDF ni tekshirish: sahifa soni, o'lchami va chizg'ich uzunligi.
 *
 * Chizg'ich aynan **rasterlangan** tasvirdan o'lchanadi, chunki
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
  return Math.round((pt * MM_PER_INCH) / PT_PER_INCH * 100) / 100
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

/**
 * Birinchi sahifadagi eng uzun **uzluksiz** qora chiziqni mm da qaytaradi.
 *
 * Bu — chizg'ich. Yorliq ramkasi undan kengroq (sahifaning butun eni),
 * shuning uchun sahifa enining 90 % idan uzun chiziqlar hisobga
 * olinmaydi. Shtrix-kod chiziqlari tik, ya'ni gorizontal o'lchovda
 * qisqa bo'lagi tushadi; chekdagi punktir chiziqlar ham uzluksiz emas.
 */
export async function longestRulerMm(data: Buffer, dpi: number = PRINTER_DPI): Promise<number> {
  const doc = await loadPdf(data)
  const page = await doc.getPage(1)

  const scale = dpi / PT_PER_INCH
  const viewport = page.getViewport({ scale })

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

  const { data: pixels } = context.getImageData(0, 0, width, height)

  const limit = width * 0.9
  let longest = 0

  for (let y = 0; y < height; y += 1) {
    let run = 0

    for (let x = 0; x < width; x += 1) {
      const index = (y * width + x) * 4
      const dark = (pixels[index]! + pixels[index + 1]! + pixels[index + 2]!) / 3 < 128

      if (dark) {
        run += 1
      } else {
        if (run <= limit) longest = Math.max(longest, run)
        run = 0
      }
    }

    if (run <= limit) longest = Math.max(longest, run)
  }

  return Math.round((longest / dpi) * MM_PER_INCH * 100) / 100
}
