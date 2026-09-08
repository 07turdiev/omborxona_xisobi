<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'

import { useAuthStore } from '@/stores/auth'
import { useThemeStore } from '@/stores/theme'

defineProps<{ title: string; subtitle: string }>()
const emit = defineEmits<{ toggleSidebar: [] }>()

const auth = useAuthStore()
const theme = useThemeStore()
const router = useRouter()

const menuOpen = ref(false)
const menuRoot = ref<HTMLElement | null>(null)

const initials = computed(() => (auth.user?.full_name ?? 'F').slice(0, 2).toUpperCase())
const roleName = computed(() => auth.user?.current_tenant?.role_display ?? '')

function onDocumentClick(event: MouseEvent) {
  if (menuRoot.value && !menuRoot.value.contains(event.target as Node)) {
    menuOpen.value = false
  }
}

onMounted(() => document.addEventListener('click', onDocumentClick))
onBeforeUnmount(() => document.removeEventListener('click', onDocumentClick))

function onLogout() {
  auth.logout()
  router.push({ name: 'login' })
}
</script>

<template>
  <header class="topbar">
    <div class="topbar-left">
      <button class="mobile-menu" type="button" @click="emit('toggleSidebar')">
        <svg><use href="#i-menu" /></svg>
      </button>

      <div class="page-heading">
        <h1>{{ title }}</h1>
        <p>{{ subtitle }}</p>
      </div>
    </div>

    <div class="topbar-right">
      <button
        class="header-icon-button"
        type="button"
        :title="theme.isDark ? 'Kunduzgi rejim' : 'Tungi rejim'"
        @click="theme.toggle()"
      >
        <svg class="theme-light-icon"><use href="#i-moon" /></svg>
        <svg class="theme-dark-icon"><use href="#i-sun" /></svg>
      </button>

      <div ref="menuRoot" class="user-menu">
        <button class="user-button" type="button" @click="menuOpen = !menuOpen">
          <div class="user-avatar">{{ initials }}</div>

          <div class="user-copy">
            <strong>{{ auth.user?.full_name }}</strong>
            <span>{{ roleName }}</span>
          </div>

          <span>⌄</span>
        </button>

        <div class="user-dropdown" :class="{ show: menuOpen }">
          <div class="dropdown-profile">
            <strong>{{ auth.user?.full_name }}</strong>
            <span>{{ auth.user?.current_tenant?.tenant_name }}</span>
          </div>

          <button class="logout-button" type="button" @click="onLogout">
            <svg><use href="#i-logout" /></svg>
            <span>Chiqish</span>
          </button>
        </div>
      </div>
    </div>
  </header>
</template>
