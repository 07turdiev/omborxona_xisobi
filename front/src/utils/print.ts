/**
 * Chop etishdan oldin qog'oz o'lchamini belgilaydi.
 *
 * `@page` qoidasi CSS o'zgaruvchilarini ko'rmaydi: ular elementga
 * bog'langan, sahifaga emas. Shuning uchun o'lcham tayyor matn sifatida
 * <style> ichiga yoziladi — aks holda brauzer o'zining sukut bo'yicha
 * qog'ozini (A4) oladi va chek 80 mm lentaga sig'may qoladi.
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
