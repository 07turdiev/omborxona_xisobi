import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'

import { tokenStorage } from '@/api/client'
import { useAuthStore } from '@/stores/auth'
import PosView from '@/views/PosView.vue'

/**
 * Marshrutlar. `meta.admin: true` — faqat administrator uchun.
 * Kassir uchun ochiq bo'limlar: kassa, qaytarish, mahsulotlar, qoldiq.
 */
const routes: RouteRecordRaw[] = [
  {
    path: '/',
    name: 'pos',
    component: PosView,
    meta: { title: 'Kassa' },
  },
  {
    path: '/returns',
    name: 'returns',
    component: () => import('@/views/ReturnsView.vue'),
    meta: { title: 'Qaytarish va almashtirish' },
  },
  {
    path: '/receipts',
    name: 'receipts',
    component: () => import('@/views/ReceiptsView.vue'),
    meta: { title: 'Cheklar' },
  },
  {
    path: '/products',
    name: 'products',
    component: () => import('@/views/ProductsView.vue'),
    meta: { title: 'Mahsulotlar' },
  },
  {
    path: '/stock',
    name: 'stock',
    component: () => import('@/views/StockView.vue'),
    meta: { title: 'Qoldiq' },
  },
  {
    path: '/dashboard',
    name: 'dashboard',
    component: () => import('@/views/DashboardView.vue'),
    meta: { title: 'Boshqaruv paneli', admin: true },
  },
  {
    path: '/purchases',
    name: 'purchases',
    component: () => import('@/views/PurchasesView.vue'),
    meta: { title: 'Kirim', admin: true },
  },
  {
    path: '/suppliers',
    name: 'suppliers',
    component: () => import('@/views/SuppliersView.vue'),
    meta: { title: 'Ta’minotchilar', admin: true },
  },
  {
    path: '/stock-counts',
    name: 'stock-counts',
    component: () => import('@/views/StockCountView.vue'),
    meta: { title: 'Inventarizatsiya', admin: true },
  },
  {
    path: '/write-offs',
    name: 'write-offs',
    component: () => import('@/views/WriteOffsView.vue'),
    meta: { title: 'Hisobdan chiqarish', admin: true },
  },
  {
    path: '/expenses',
    name: 'expenses',
    component: () => import('@/views/ExpensesView.vue'),
    meta: { title: 'Xarajatlar', admin: true },
  },
  {
    path: '/reports',
    name: 'reports',
    component: () => import('@/views/ReportsView.vue'),
    meta: { title: 'Hisobotlar', admin: true },
  },
  {
    path: '/users',
    name: 'users',
    component: () => import('@/views/UsersView.vue'),
    meta: { title: 'Xodimlar', admin: true },
  },
  {
    path: '/settings',
    name: 'settings',
    component: () => import('@/views/SettingsView.vue'),
    meta: { title: 'Sozlamalar', admin: true },
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
