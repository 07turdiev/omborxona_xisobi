<script setup lang="ts">
import { computed } from 'vue'
import { RouterLink, useRoute } from 'vue-router'

import { useAuthStore } from '@/stores/auth'
import logoUrl from '@/assets/logo.png'

defineProps<{ show: boolean }>()
const emit = defineEmits<{ close: [] }>()

const auth = useAuthStore()
const route = useRoute()

/** Kassirga ochiq bo'limlar */
const daily = [
  { to: '/', icon: 'i-sale', label: 'Kassa' },
  { to: '/returns', icon: 'i-import', label: 'Qaytarish' },
  { to: '/receipts', icon: 'i-print', label: 'Cheklar' },
  { to: '/catalog', icon: 'i-catalog', label: 'Katalog' },
  { to: '/products', icon: 'i-company', label: 'Mahsulotlar' },
  { to: '/stock', icon: 'i-stock', label: 'Qoldiq' },
]

/** Faqat administrator uchun */
const management = [
  { to: '/dashboard', icon: 'i-dashboard', label: 'Boshqaruv paneli' },
  { to: '/purchases', icon: 'i-import', label: 'Kirim' },
  { to: '/suppliers', icon: 'i-users', label: 'Ta’minotchilar' },
  { to: '/stock-counts', icon: 'i-warehouse', label: 'Inventarizatsiya' },
  { to: '/write-offs', icon: 'i-trash', label: 'Hisobdan chiqarish' },
  { to: '/expenses', icon: 'i-report', label: 'Xarajatlar' },
  { to: '/reports', icon: 'i-report', label: 'Hisobotlar' },
  { to: '/users', icon: 'i-users', label: 'Xodimlar' },
  { to: '/settings', icon: 'i-settings', label: 'Sozlamalar' },
]

const initials = computed(() => (auth.user?.full_name ?? 'X').slice(0, 1).toUpperCase())
</script>

<template>
  <aside class="sidebar" :class="{ show }">
    <div class="sidebar-brand">
      <!-- Do'kon nomi logotipning o'zida yozilgan — matn takrorlanmaydi -->
      <img class="sidebar-logo" :src="logoUrl" alt="Madlen sen" />

      <button class="sidebar-close" type="button" @click="emit('close')">
        <svg><use href="#i-close" /></svg>
      </button>
    </div>

    <nav class="sidebar-menu">
      <span class="menu-caption">Kundalik ish</span>

      <!-- `/catalog/5` ochiq bo'lsa ham "Katalog" bandi belgilangan qoladi -->
      <RouterLink
        v-for="item in daily"
        :key="item.to"
        v-slot="{ isActive, navigate }"
        :to="item.to"
        custom
      >
        <button
          class="menu-item"
          :class="{ active: isActive || route.path.startsWith(`${item.to}/`) }"
          @click="navigate"
        >
          <span class="menu-icon"><svg><use :href="`#${item.icon}`" /></svg></span>
          <span>{{ item.label }}</span>
        </button>
      </RouterLink>

      <template v-if="auth.isAdmin">
        <span class="menu-caption second">Boshqaruv</span>

        <RouterLink
          v-for="item in management"
          :key="item.to"
          v-slot="{ isActive, navigate }"
          :to="item.to"
          custom
        >
          <button class="menu-item" :class="{ active: isActive }" @click="navigate">
            <span class="menu-icon"><svg><use :href="`#${item.icon}`" /></svg></span>
            <span>{{ item.label }}</span>
          </button>
        </RouterLink>
      </template>
    </nav>

    <div class="sidebar-footer">
      <div class="sidebar-avatar">{{ initials }}</div>

      <div class="sidebar-user-copy">
        <strong>{{ auth.user?.full_name }}</strong>
        <span>{{ auth.user?.role_display }}</span>
      </div>
    </div>
  </aside>
</template>

<style scoped>
/* Logotip keng yozuv (nisbat ~2.25), shuning uchun brend qatori
   app.css dagi 56px o'rniga balandroq — aks holda nom o'qilmaydi. */
.sidebar .sidebar-brand {
  height: auto;
  padding: 14px 16px;
}

.sidebar-logo {
  width: 100%;
  max-width: 184px;
  height: auto;
  object-fit: contain;
}
</style>
