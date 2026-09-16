<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'

import { useAuthStore } from '@/stores/auth'

defineProps<{ title: string }>()
const emit = defineEmits<{ toggleSidebar: [] }>()

const auth = useAuthStore()
const router = useRouter()

const menuOpen = ref(false)
const menuRoot = ref<HTMLElement | null>(null)

const initials = computed(() => (auth.user?.full_name ?? 'X').slice(0, 2).toUpperCase())

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
      </div>
    </div>

    <div class="topbar-right">
      <div ref="menuRoot" class="user-menu">
        <button class="user-button" type="button" @click="menuOpen = !menuOpen">
          <div class="user-avatar">{{ initials }}</div>

          <div class="user-copy">
            <strong>{{ auth.user?.full_name }}</strong>
            <span>{{ auth.user?.role_display }}</span>
          </div>

          <svg class="user-chevron"><use href="#i-chevron-down" /></svg>
        </button>

        <div class="user-dropdown" :class="{ show: menuOpen }">
          <div class="dropdown-profile">
            <strong>{{ auth.user?.full_name }}</strong>
            <span>{{ auth.user?.username }}</span>
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
