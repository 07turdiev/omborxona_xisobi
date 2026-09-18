/**
 * Chop etishdan oldin qog'oz o'lchamini belgilaydi.
 *
 * `@page` qoidasi CSS o'zgaruvchilarini ko'rmaydi: ular elementga
 * bog'langan, sahifaga emas. Shuning uchun o'lcham tayyor matn sifatida
 * <style> ichiga yoziladi.
 */
export function printWithPageSize(pageCss: string) {
  let style = document.getElementById('print-page') as HTMLStyleElement | null

  if (!style) {
    style = document.createElement('style')
    style.id = 'print-page'
    document.head.appendChild(style)
  }

  style.textContent = pageCss

  document.body.classList.add('printing')
  window.print()
  document.body.classList.remove('printing')
}

const HEIGHT_KEY = 'last-receipt-height-mm'

/**
 * Oxirgi chekning mazmuni necha millimetr bo'lganini eslab qoladi.
 *
 * Buni administrator Sozlamalar → Qurilmalarni sinash sahifasida
 * ko'radi va qog'oz balandligini shunga qarab tanlaydi: brauzer orqali
 * chop etishda sahifa balandligini har chekka moslab bo'lmaydi, uni
 * printer drayveri hal qiladi.
 */
export function rememberReceiptHeight(mm: number) {
  try {
    localStorage.setItem(HEIGHT_KEY, String(Math.round(mm * 10) / 10))
  } catch {
    // Shaxsiy oynada saqlash yopiq bo'lishi mumkin — muhim emas
  }
}

/** Oxirgi chek mazmunining balandligi, mm. Hali chop etilmagan bo'lsa — null. */
export function lastReceiptHeight(): number | null {
  try {
    const value = localStorage.getItem(HEIGHT_KEY)

    return value ? Number(value) : null
  } catch {
    return null
  }
}
