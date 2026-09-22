import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'

import { tokenStorage } from '@/api/client'
import { useAuthStore } from '@/stores/auth'
import PosView from '@/views/PosView.vue'

declare module 'vue-router' {
  interface RouteMeta {
    /** Topbar sarlavhasi — bo'lim nomi */
    title?: string
    /** Sarlavha ostidagi bir qatorli izoh: sahifa nima uchun */
    description?: string
    /** Menyu bandi va tablar guruhi (`navigation.ts`) */
    section?: string
    /** Faqat administrator uchun */
    admin?: boolean
    /** Sahifada tablar ko'rsatilmaydi (masalan mahsulot sahifasi) */
    hideTabs?: boolean
    /** Kirishsiz ochiladi */
    public?: boolean
  }
}

/**
 * Marshrutlar. Tuzilma: `navigation.ts`.
 *
 * Kassir ko'radigani: kassa, qaytarish, mahsulotlar (va havola orqali
 * cheklar). Qolgani — `admin: true`.
 */
const routes: RouteRecordRaw[] = [
  {
    path: '/',
    name: 'pos',
    component: PosView,
    meta: {
      title: 'Sotish',
      section: 'pos',
      description: 'Tovarni sotasiz va chek chiqarasiz',
    },
  },
  {
    path: '/returns',
    name: 'returns',
    component: () => import('@/views/ReturnsView.vue'),
    meta: {
      title: 'Qaytarish',
      section: 'returns',
      description: 'Chek bo‘yicha tovarni qaytarib olish yoki boshqasiga almashtirish',
    },
  },

  // --- Mahsulotlar ------------------------------------------------------
  {
    path: '/products',
    name: 'products',
    component: () => import('@/views/ProductListView.vue'),
    meta: {
      title: 'Tovarlar',
      section: 'products',
      description: 'Do‘kondagi hamma tovar: narxi, qoldig‘i va yorlig‘i',
    },
  },
  {
    path: '/products/attributes',
    name: 'product-attributes',
    component: () => import('@/views/ProductAttributesView.vue'),
    meta: {
      title: 'Tovarlar',
      section: 'products',
      admin: true,
      description: 'Mahsulotlarni tartiblash uchun ro‘yxatlar: kategoriya, o‘lcham, rang',
    },
  },
  {
    path: '/products/:id(\\d+)',
    name: 'product',
    component: () => import('@/views/ProductPageView.vue'),
    meta: {
      title: 'Tovarlar',
      section: 'products',
      hideTabs: true,
      description: 'Tovarning rasmlari, har rang va o‘lchamdagi qoldig‘i va shtrix-kodi',
    },
  },
  // Eski manzillar: katalog va qoldiq sahifalari mahsulotlar bilan birlashdi
  { path: '/catalog', redirect: '/products' },
  { path: '/catalog/:id', redirect: (to) => `/products/${to.params.id}` },
  { path: '/stock', redirect: '/products' },

  {
    path: '/dashboard',
    name: 'dashboard',
    component: () => import('@/views/DashboardView.vue'),
    meta: {
      title: 'Bosh sahifa',
      section: 'dashboard',
      admin: true,
      description: 'Nima qilmoqchisiz? Bugungi savdo ham shu yerda',
    },
  },

  // --- Kirim ------------------------------------------------------------
  {
    path: '/purchases',
    name: 'purchases',
    component: () => import('@/views/PurchasesView.vue'),
    meta: {
      title: 'Tovar qabul qilish',
      section: 'purchases',
      admin: true,
      description: 'Yangi kelgan tovarni kiritasiz va yorlig‘ini chop etasiz',
    },
  },
  {
    path: '/suppliers',
    name: 'suppliers',
    component: () => import('@/views/SuppliersView.vue'),
    meta: {
      title: 'Tovar qabul qilish',
      section: 'purchases',
      admin: true,
      description: 'Tovar keltiruvchilar va ular bilan hisob-kitob',
    },
  },

  // --- Zalga chiqarish --------------------------------------------------
  {
    // Kassir ham ocha oladi: javonni sotuvchining o'zi to'ldiradi
    path: '/transfers',
    name: 'transfers',
    component: () => import('@/views/TransferView.vue'),
    meta: {
      title: 'Zalga chiqarish',
      section: 'transfers',
      description: 'Ombordagi tovarni savdo zaliga chiqarasiz',
    },
  },

  // --- Inventarizatsiya -------------------------------------------------
  {
    path: '/stock-counts',
    name: 'stock-counts',
    component: () => import('@/views/StockCountView.vue'),
    meta: {
      title: 'Sanoq',
      section: 'counts',
      admin: true,
      description: 'Zal yoki omborni sanab, tizimdagi son bilan solishtirasiz',
    },
  },
  {
    path: '/write-offs',
    name: 'write-offs',
    component: () => import('@/views/WriteOffsView.vue'),
    meta: {
      title: 'Sanoq',
      section: 'counts',
      admin: true,
      description: 'Buzilgan, yo‘qolgan yoki yaroqsiz tovarni qoldiqdan chiqarish',
    },
  },

  // --- Hisobotlar -------------------------------------------------------
  {
    path: '/reports',
    name: 'reports',
    component: () => import('@/views/ReportsView.vue'),
    meta: {
      title: 'Hisobot',
      section: 'reports',
      admin: true,
      description: 'Tanlangan davr uchun tushum, tannarx va foyda',
    },
  },
  {
    path: '/reports/stock',
    name: 'stock-value',
    component: () => import('@/views/StockValueView.vue'),
    meta: {
      title: 'Hisobot',
      section: 'reports',
      admin: true,
      description: 'Butun qoldiq tannarxda va sotuv narxida qancha turadi',
    },
  },
  {
    path: '/expenses',
    name: 'expenses',
    component: () => import('@/views/ExpensesView.vue'),
    meta: {
      title: 'Hisobot',
      section: 'reports',
      admin: true,
      description: 'Ijara, ish haqi va boshqa xarajatlar — sof foydani hisoblash uchun',
    },
  },
  {
    // Kassir ham ocha oladi (o'zining bugungi cheklari) — menyuda yo'q
    path: '/receipts',
    name: 'receipts',
    component: () => import('@/views/ReceiptsView.vue'),
    meta: {
      title: 'Hisobot',
      section: 'reports',
      description: 'Sotilgan cheklar: topish, qayta chop etish, qaytarishga o‘tish',
    },
  },

  // --- Sozlamalar -------------------------------------------------------
  {
    path: '/settings',
    name: 'settings',
    component: () => import('@/views/SettingsView.vue'),
    meta: {
      title: 'Sozlamalar',
      section: 'settings',
      admin: true,
      description: 'Do‘kon nomi, yorliq va chek o‘lchami, chegirma chegarasi',
    },
  },
  {
    path: '/users',
    name: 'users',
    component: () => import('@/views/UsersView.vue'),
    meta: {
      title: 'Sozlamalar',
      section: 'settings',
      admin: true,
      description: 'Kassir va administratorlar: qo‘shish, parolni almashtirish, bloklash',
    },
  },
  {
    path: '/settings/devices',
    name: 'devices',
    component: () => import('@/views/DeviceTestView.vue'),
    meta: {
      title: 'Sozlamalar',
      section: 'settings',
      admin: true,
      description: 'Printer, skaner va chop etish agentini sinab ko‘rish',
    },
  },

  {
    path: '/login',
    name: 'login',
    component: () => import('@/views/LoginView.vue'),
    meta: { public: true },
  },
  {
    path: '/:pathMatch(.*)*',
    name: 'not-found',
    component: () => import('@/views/NotFoundView.vue'),
    meta: { public: true },
  },
]

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes,
  // Orqaga qaytganda sahifa avvalgi joyiga qaytadi: mahsulotni ochib
  // qaytgan sotuvchi ro'yxatni boshidan varaqlamasin
  scrollBehavior: (_to, _from, saved) => saved ?? { top: 0 },
})

router.beforeEach(async (to) => {
  const authenticated = Boolean(tokenStorage.access)

  if (!to.meta.public && !authenticated) {
    return { name: 'login', query: { redirect: to.fullPath } }
  }

  if (to.name === 'login' && authenticated) {
    return { name: 'pos' }
  }

  if (!authenticated) return

  const auth = useAuthStore()

  if (!auth.user) {
    try {
      await auth.loadProfile()
    } catch {
      return
    }
  }

  // Himoya serverda: bu faqat kassirni yopiq sahifadan qaytaradi
  if (to.meta.admin && !auth.isAdmin) {
    return { name: 'pos' }
  }
})

export default router
