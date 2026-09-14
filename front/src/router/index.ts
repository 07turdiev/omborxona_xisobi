import { createRouter, createWebHistory } from 'vue-router'

import { tokenStorage } from '@/api/client'
import { useAuthStore } from '@/stores/auth'
import DashboardView from '@/views/DashboardView.vue'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      name: 'dashboard',
      component: DashboardView,
      meta: {
        requiresAuth: true,
        permission: 'dashboard',
        title: 'Boshqaruv paneli',
        subtitle: 'Ombor tizimining asosiy ko‘rsatkichlari',
      },
    },
    {
      path: '/warehouses',
      name: 'warehouses',
      component: () => import('@/views/WarehousesView.vue'),
      meta: {
        requiresAuth: true,
        permission: 'warehouses',
        title: 'Omborlar',
        subtitle: 'Omborlarni qo‘shish, tahrirlash va boshqarish',
      },
    },
    {
      path: '/stock',
      name: 'stock',
      component: () => import('@/views/StockView.vue'),
      meta: {
        requiresAuth: true,
        permission: 'stock',
        title: 'Qoldiqlar',
        subtitle: 'Ombor, partiya va yaroqlilik muddati kesimida',
      },
    },
    {
      path: '/imports',
      name: 'imports',
      component: () => import('@/views/DocumentsView.vue'),
      meta: {
        requiresAuth: true,
        permission: 'imports',
        title: 'Kirim',
        subtitle: 'Yetkazib beruvchidan kelgan tovar hujjatlari',
        documentKind: 'purchase',
      },
    },
    {
      path: '/sales',
      name: 'sales',
      component: () => import('@/views/DocumentsView.vue'),
      meta: {
        requiresAuth: true,
        permission: 'sales',
        title: 'Sotuv',
        subtitle: 'Sotuv hujjatlari, tannarx va foyda',
        documentKind: 'sale',
      },
    },
    {
      path: '/categories',
      name: 'categories',
      component: () => import('@/views/CategoriesView.vue'),
      meta: {
        requiresAuth: true,
        permission: 'categories',
        title: 'Kategoriyalar',
        subtitle: 'Kategoriya daraxti va atribut ta’riflari',
      },
    },
    {
      path: '/products',
      name: 'products',
      component: () => import('@/views/ProductsView.vue'),
      meta: {
        requiresAuth: true,
        permission: 'products',
        title: 'Mahsulotlar',
        subtitle: 'Katalog, atributlar va o‘ram birliklari',
      },
    },
    {
      path: '/transfers',
      name: 'transfers',
      component: () => import('@/views/TransfersView.vue'),
      meta: {
        requiresAuth: true,
        permission: 'transfers',
        title: 'Ko‘chirish',
        subtitle: 'Omborlar orasida: jo‘natildi → qabul qilindi',
      },
    },
    {
      path: '/counterparties',
      name: 'counterparties',
      component: () => import('@/views/PartnersView.vue'),
      meta: {
        requiresAuth: true,
        permission: 'counterparties',
        title: 'Kontragentlar',
        subtitle: 'Yetkazib beruvchilar va mijozlar',
      },
    },
    {
      path: '/reports',
      name: 'reports',
      component: () => import('@/views/ReportsView.vue'),
      meta: {
        requiresAuth: true,
        permission: 'reports',
        title: 'Hisobotlar',
        subtitle: 'Aylanma, tannarx, foyda va yo‘qotishlar',
      },
    },
    {
      path: '/users',
      name: 'users',
      component: () => import('@/views/UsersView.vue'),
      meta: {
        requiresAuth: true,
        permission: 'users',
        title: 'Foydalanuvchilar',
        subtitle: 'Xodimlar, rollar va ombor huquqlari',
      },
    },
    {
      path: '/settings',
      name: 'settings',
      component: () => import('@/views/SettingsView.vue'),
      meta: {
        requiresAuth: true,
        permission: 'settings',
        title: 'Sozlamalar',
        subtitle: 'Tashkilot rekvizitlari, hujjat raqamlari va kurslar',
      },
    },
    {
      path: '/units',
      name: 'units',
      component: () => import('@/views/UnitsView.vue'),
      meta: {
        requiresAuth: true,
        permission: 'settings',
        title: 'O‘lchov birliklari',
        subtitle: 'Tashkilotning o‘z birliklari va konversiya',
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
  ],
})

/**
 * Ruxsatsiz bo'limga manzil orqali kirilganda qayerga yo'naltiriladi.
 * Tartib — kundalik ishda eng ko'p kerak bo'ladiganidan boshlab.
 */
const FALLBACK_ORDER = [
  'dashboard', 'sales', 'stock', 'imports', 'products', 'warehouses',
  'counterparties', 'transfers', 'reports', 'settings', 'users',
]

router.beforeEach(async (to) => {
  const authenticated = Boolean(tokenStorage.access)

  if (to.meta.requiresAuth && !authenticated) {
    return { name: 'login', query: { redirect: to.fullPath } }
  }

  if (to.name === 'login' && authenticated) {
    return { name: 'dashboard' }
  }

  const permission = to.meta.permission as string | undefined

  if (!permission || !authenticated) return

  // Bu faqat qulaylik: ruxsatsiz bo'lim bo'sh sahifa va 403 xatolar bilan
  // ochilmasin. Himoyaning o'zi serverda.
  const auth = useAuthStore()

  if (!auth.user) {
    try {
      await auth.fetchMe()
    } catch {
      // Token eskirgan — API mijozi login sahifasiga o'zi yuboradi
      return
    }
  }

  if (auth.can(permission)) return

  const fallback = FALLBACK_ORDER.find((name) => {
    const target = router.resolve({ name })
    return target.name !== to.name && auth.can(target.meta.permission as string)
  })

  // Birorta ham bo'lim ochiq bo'lmasa, sahifa o'zi "ruxsat yo'q" deb ko'rsatadi
  if (fallback) return { name: fallback }
})

export default router
