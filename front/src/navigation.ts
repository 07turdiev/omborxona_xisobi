/**
 * Ilova tuzilmasi bitta joyda: yon menyu va sahifa ichidagi tablar.
 *
 * Har marshrutda `meta.section` bor (`router/index.ts`) — sahifa qaysi
 * menyu bandiga va qaysi tablar guruhiga tegishli ekanini shu aytadi.
 * Sahifalarning o'zi tab chizmaydi: tablarni `PageTabs` shu ro'yxatdan
 * oladi. Yangi sahifa qo'shilsa — marshrutga `section` beriladi va kerak
 * bo'lsa shu yerga tab qo'shiladi.
 */

export interface MenuItem {
  to: string
  icon: string
  label: string
  /** Shu bo'limlardagi sahifa ochiq bo'lsa band belgilanadi */
  sections: string[]
}

export interface Tab {
  to: string
  label: string
  /** Faqat administratorga ko'rinadi */
  admin?: boolean
}

export const ADMIN_MENU: MenuItem[] = [
  { to: '/dashboard', icon: 'i-dashboard', label: 'Bosh sahifa', sections: ['dashboard'] },
  // Qaytarish alohida band emas — kassadan va cheklardan ochiladi
  { to: '/', icon: 'i-sale', label: 'Sotish', sections: ['pos', 'returns'] },
  { to: '/products', icon: 'i-catalog', label: 'Tovarlar', sections: ['products'] },
  { to: '/purchases', icon: 'i-import', label: 'Tovar qabul qilish', sections: ['purchases'] },
  { to: '/stock-counts', icon: 'i-warehouse', label: 'Sanoq', sections: ['counts'] },
  { to: '/reports', icon: 'i-report', label: 'Hisobot', sections: ['reports'] },
  { to: '/settings', icon: 'i-settings', label: 'Sozlamalar', sections: ['settings'] },
]

export const CASHIER_MENU: MenuItem[] = [
  { to: '/', icon: 'i-sale', label: 'Sotish', sections: ['pos'] },
  { to: '/returns', icon: 'i-import', label: 'Qaytarish', sections: ['returns'] },
  { to: '/products', icon: 'i-catalog', label: 'Tovarlar', sections: ['products'] },
]

export const SECTION_TABS: Record<string, Tab[]> = {
  products: [
    { to: '/products', label: 'Tovarlar' },
    { to: '/products/attributes', label: 'Kategoriya, o‘lcham, rang', admin: true },
  ],
  purchases: [
    { to: '/purchases', label: 'Qabul qilish' },
    { to: '/suppliers', label: 'Ta’minotchilar' },
  ],
  counts: [
    { to: '/stock-counts', label: 'Sanoq' },
    { to: '/write-offs', label: 'Hisobdan chiqarish' },
  ],
  reports: [
    { to: '/reports', label: 'Savdo', admin: true },
    { to: '/reports/stock', label: 'Qoldiq qiymati', admin: true },
    { to: '/expenses', label: 'Xarajatlar', admin: true },
    { to: '/receipts', label: 'Cheklar' },
  ],
  settings: [
    { to: '/settings', label: 'Do‘kon' },
    { to: '/users', label: 'Xodimlar' },
    { to: '/settings/devices', label: 'Qurilmalar' },
  ],
}
