<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { RouterView, useRoute } from 'vue-router'

import AppIcons from '@/components/AppIcons.vue'
import AppSidebar from '@/components/AppSidebar.vue'
import AppTopbar from '@/components/AppTopbar.vue'
import { useAuthStore } from '@/stores/auth'

const route = useRoute()
const auth = useAuthStore()

const sidebarOpen = ref(false)

/** Kirish va 404 sahifalari qobiqsiz ko'rsatiladi. */
const showShell = computed(() => route.meta.public !== true)
const title = computed(() => (route.meta.title as string) ?? '')

onMounted(async () => {
  if (auth.isAuthenticated && !auth.user) {
    try {
      await auth.loadProfile()
    } catch {
      // Token eskirgan — API mijozi kirish sahifasiga yuboradi
    }
  }
})

watch(() => route.fullPath, () => (sidebarOpen.value = false))
</script>

<template>
  <AppIcons />

  <div v-if="showShell" class="app-shell">
    <AppSidebar :show="sidebarOpen" @close="sidebarOpen = false" />

    <div class="sidebar-overlay" :class="{ show: sidebarOpen }" @click="sidebarOpen = false"></div>

    <main class="main-area">
      <AppTopbar :title="title" @toggle-sidebar="sidebarOpen = !sidebarOpen" />

      <div class="content">
        <RouterView />
      </div>
    </main>
  </div>

  <RouterView v-else />
</template>
