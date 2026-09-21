/**
 * UI testlari ma'lumot yaratadi — ular faqat alohida test bazasiga
 * qarshi yurgizilishi kerak.
 *
 * `npm run test:ui` shu bazani tayyorlab, `UI_TEST` belgisini qo'yadi.
 * To'g'ridan-to'g'ri `npx playwright test` yurgizilsa, testlar ishlab
 * chiqish bazasiga yozib yuborardi — shuning uchun bu yerda to'xtatiladi.
 */
export default function guard() {
  if (process.env.UI_TEST) return

  throw new Error(
    'UI testlarini `npm run test:ui` orqali yurgizing — u alohida baza yaratadi.\n' +
      'Ishlab chiqish bazasiga yozilmasligi uchun to‘g‘ridan-to‘g‘ri yurgizish to‘xtatildi.\n' +
      'Ataylab boshqa backendga qarshi kerak bo‘lsa: UI_TEST=1 VITE_API_TARGET=… npx playwright test',
  )
}
