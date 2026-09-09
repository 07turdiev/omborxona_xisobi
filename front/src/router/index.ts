import { createRouter, createWebHistory } from 'vue-router'

import { tokenStorage } from '@/api/client'
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

router.beforeEach((to) => {
  const authenticated = Boolean(tokenStorage.access)

  if (to.meta.requiresAuth && !authenticated) {
    return { name: 'login', query: { redirect: to.fullPath } }
  }

  if (to.name === 'login' && authenticated) {
    return { name: 'dashboard' }
  }
})

export default router
