<script setup lang="ts">
import { computed } from 'vue'
import { RouterLink } from 'vue-router'

import { useAuthStore } from '@/stores/auth'

defineProps<{ show: boolean; warehouseCount: number }>()
const emit = defineEmits<{ close: [] }>()

const auth = useAuthStore()

const tenantName = computed(
  () => auth.user?.current_tenant?.tenant_name ?? 'Tashkilot tanlanmagan',
)
const roleName = computed(() => auth.user?.current_tenant?.role_display ?? '')
const initials = computed(() => {
  const name = auth.user?.full_name ?? ''
  return name.slice(0, 1).toUpperCase() || 'F'
})

/**
 * Menyu tarkibi dizayndagi tartibda (store/index.html).
 *
 * `perm` — bo'limni ko'rsatish uchun kerakli ruxsat. Ruxsatsiz bo'lim
 * menyuda umuman ko'rinmaydi; unga manzil orqali kirilsa, router
 * boshqaruv paneliga qaytaradi, server esa 403 beradi.
 */
const operations = [
  { to: '/', icon: 'i-dashboard', label: 'Boshqaruv paneli', perm: 'dashboard' },
  { to: '/warehouses', icon: 'i-warehouse', label: 'Omborlar', perm: 'warehouses', badge: true },
  { to: '/stock', icon: 'i-stock', label: 'Qoldiqlar', perm: 'stock' },
  { to: '/imports', icon: 'i-import', label: 'Kirim', perm: 'imports' },
  { to: '/sales', icon: 'i-sale', label: 'Sotuv', perm: 'sales' },
  { to: '/transfers', icon: 'i-warehouse', label: 'Ko‘chirish', perm: 'transfers' },
  { to: '/products', icon: 'i-company', label: 'Mahsulotlar', perm: 'products' },
  { to: '/counterparties', icon: 'i-users', label: 'Kontragentlar', perm: 'counterparties' },
]

const analytics = [
  { to: '/reports', icon: 'i-report', label: 'Hisobotlar', perm: 'reports' },
  { to: '/users', icon: 'i-users', label: 'Foydalanuvchilar', perm: 'users' },
  { to: '/settings', icon: 'i-settings', label: 'Sozlamalar', perm: 'settings' },
]

const visibleOperations = computed(() => operations.filter((item) => auth.can(item.perm)))
const visibleAnalytics = computed(() => analytics.filter((item) => auth.can(item.perm)))
</script>

<template>
  <aside class="sidebar" :class="{ show }">
    <div class="sidebar-brand">
      <div class="brand-symbol">O</div>

      <div class="brand-copy">
        <strong>Omborxona</strong>
        <span>Hisob tizimi</span>
      </div>

      <button class="sidebar-close" type="button" @click="emit('close')">
        <svg><use href="#i-close" /></svg>
      </button>
    </div>

    <div class="workspace-card">
      <span>Ish maydoni</span>
      <strong>{{ tenantName }}</strong>

      <div class="workspace-status">
        <i></i>
        <small>Tizim faol</small>
      </div>
    </div>

    <nav class="sidebar-menu">
      <span class="menu-caption">Operatsiyalar</span>

      <RouterLink
        v-for="item in visibleOperations"
        :key="item.to"
        v-slot="{ isActive, navigate }"
        :to="item.to"
        custom
      >
        <button class="menu-item" :class="{ active: isActive }" @click="navigate">
          <span class="menu-icon">
            <svg><use :href="`#${item.icon}`" /></svg>
          </span>

          <span>{{ item.label }}</span>

          <b v-if="item.badge" class="menu-badge">{{ warehouseCount }}</b>
        </button>
      </RouterLink>

      <span v-if="visibleAnalytics.length" class="menu-caption second">Tahlil</span>

      <RouterLink
        v-for="item in visibleAnalytics"
        :key="item.to"
        v-slot="{ isActive, navigate }"
        :to="item.to"
        custom
      >
        <button class="menu-item" :class="{ active: isActive }" @click="navigate">
          <span class="menu-icon">
            <svg><use :href="`#${item.icon}`" /></svg>
          </span>

          <span>{{ item.label }}</span>
        </button>
      </RouterLink>
    </nav>

    <div class="sidebar-footer">
      <div class="sidebar-avatar">{{ initials }}</div>

      <div class="sidebar-user-copy">
        <strong>{{ auth.user?.full_name }}</strong>
        <span>{{ roleName }}</span>
      </div>
    </div>
  </aside>
</template>
