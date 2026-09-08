<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { RouterView, useRoute } from 'vue-router'

import AppIcons from '@/components/AppIcons.vue'
import AppSidebar from '@/components/AppSidebar.vue'
import AppTopbar from '@/components/AppTopbar.vue'
import { useAuthStore } from '@/stores/auth'
import { useThemeStore } from '@/stores/theme'
import { useWarehouseStore } from '@/stores/warehouses'

const route = useRoute()
const auth = useAuthStore()
const theme = useThemeStore()
const warehouses = useWarehouseStore()

const sidebarOpen = ref(false)

/** Login va 404 sahifalari qobiqsiz ko'rsatiladi. */
const showShell = computed(() => route.meta.public !== true)

const title = computed(() => (route.meta.title as string) ?? '')
const subtitle = computed(() => (route.meta.subtitle as string) ?? '')

onMounted(async () => {
  theme.init()

  if (auth.isAuthenticated && !auth.user) {
    await auth.fetchMe()
  }
})

// Sahifa almashganda mobil menyu yopiladi
watch(() => route.fullPath, () => (sidebarOpen.value = false))

// Sidebar'dagi ombor soni har doim dolzarb bo'lsin
watch(
  () => auth.isAuthenticated,
  (value) => {
    if (value) warehouses.loadSummary()
  },
  { immediate: true },
)
</script>

<template>
  <AppIcons />

  <div v-if="showShell" class="app-shell">
    <AppSidebar
      :show="sidebarOpen"
      :warehouse-count="warehouses.summary?.total ?? 0"
      @close="sidebarOpen = false"
    />

    <div
      class="sidebar-overlay"
      :class="{ show: sidebarOpen }"
      @click="sidebarOpen = false"
    ></div>

    <main class="main-area">
      <AppTopbar
        :title="title"
        :subtitle="subtitle"
        @toggle-sidebar="sidebarOpen = !sidebarOpen"
      />

      <div class="content">
        <RouterView />
      </div>
    </main>
  </div>

  <RouterView v-else />
</template>
