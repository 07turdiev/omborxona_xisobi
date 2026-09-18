<script setup lang="ts">
import { computed } from 'vue'
import { RouterLink, useRoute } from 'vue-router'

import { ADMIN_MENU, CASHIER_MENU } from '@/navigation'
import { useAuthStore } from '@/stores/auth'
import logoUrl from '@/assets/logo.png'

defineProps<{ show: boolean }>()
const emit = defineEmits<{ close: [] }>()

const auth = useAuthStore()
const route = useRoute()

/** Tuzilma: `navigation.ts`. Kassir uchta bandni ko'radi. */
const menu = computed(() => (auth.isAdmin ? ADMIN_MENU : CASHIER_MENU))

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

    <nav class="sidebar-menu" aria-label="Asosiy menyu">
      <!-- Band o'z bo'limidagi har sahifada belgilangan qoladi:
           masalan Ta'minotchilar ochiq bo'lsa ham "Kirim" -->
      <RouterLink
        v-for="item in menu"
        :key="item.to"
        v-slot="{ navigate }"
        :to="item.to"
        custom
      >
        <button
          class="menu-item"
          :class="{ active: item.sections.includes(route.meta.section ?? '') }"
          :aria-current="item.sections.includes(route.meta.section ?? '') ? 'page' : undefined"
          @click="navigate"
        >
          <span class="menu-icon"><svg><use :href="`#${item.icon}`" /></svg></span>
          <span>{{ item.label }}</span>
        </button>
      </RouterLink>
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

.sidebar-menu {
  padding-top: 12px;
}
</style>
