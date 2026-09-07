<script setup lang="ts">
import { computed } from 'vue'
import { RouterLink, RouterView, useRoute, useRouter } from 'vue-router'

import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const route = useRoute()
const router = useRouter()

const showChrome = computed(() => route.meta.public !== true)

function onLogout() {
  auth.logout()
  router.push({ name: 'login' })
}
</script>

<template>
  <div v-if="showChrome" class="min-h-screen bg-slate-50">
    <header class="border-b border-slate-200 bg-white">
      <nav class="mx-auto flex max-w-6xl items-center justify-between px-6 py-3">
        <RouterLink to="/" class="font-semibold text-slate-900">Omborxona xisobi</RouterLink>
        <button
          type="button"
          class="text-sm font-medium text-slate-600 hover:text-slate-900"
          @click="onLogout"
        >
          Chiqish
        </button>
      </nav>
    </header>

    <main class="mx-auto max-w-6xl px-6 py-8">
      <RouterView />
    </main>
  </div>

  <RouterView v-else />
</template>
