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

/** Menyu tarkibi dizayndagi tartibda (store/index.html). */
const operations = [
  { to: '/', icon: 'i-dashboard', tone: 'purple', label: 'Boshqaruv paneli' },
  { to: '/warehouses', icon: 'i-warehouse', tone: 'teal', label: 'Omborlar', badge: true },
  { to: '/stock', icon: 'i-stock', tone: 'blue', label: 'Qoldiqlar' },
  { to: '/imports', icon: 'i-import', tone: 'green', label: 'Kirim' },
  { to: '/sales', icon: 'i-sale', tone: 'orange', label: 'Sotuv' },
  { to: '/transfers', icon: 'i-warehouse', tone: 'blue', label: 'Ko‘chirish' },
  { to: '/products', icon: 'i-company', tone: 'purple', label: 'Mahsulotlar' },
  { to: '/counterparties', icon: 'i-users', tone: 'teal', label: 'Kontragentlar' },
]

const analytics = [
  { to: '/reports', icon: 'i-report', tone: 'orange', label: 'Hisobotlar' },
  { to: '/users', icon: 'i-users', tone: 'blue', label: 'Foydalanuvchilar' },
  { to: '/settings', icon: 'i-settings', tone: 'purple', label: 'Sozlamalar' },
]
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
        v-for="item in operations"
        :key="item.to"
        v-slot="{ isActive, navigate }"
        :to="item.to"
        custom
      >
        <button class="menu-item" :class="{ active: isActive }" @click="navigate">
          <span class="menu-icon" :class="`${item.tone}-menu-icon`">
            <svg><use :href="`#${item.icon}`" /></svg>
          </span>

          <span>{{ item.label }}</span>

          <b v-if="item.badge" class="menu-badge">{{ warehouseCount }}</b>
        </button>
      </RouterLink>

      <span class="menu-caption second">Tahlil</span>

      <RouterLink
        v-for="item in analytics"
        :key="item.to"
        v-slot="{ isActive, navigate }"
        :to="item.to"
        custom
      >
        <button class="menu-item" :class="{ active: isActive }" @click="navigate">
          <span class="menu-icon" :class="`${item.tone}-menu-icon`">
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
