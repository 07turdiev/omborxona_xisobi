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
