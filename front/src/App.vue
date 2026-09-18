<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { RouterView, useRoute } from 'vue-router'

import AppIcons from '@/components/AppIcons.vue'
import AppSidebar from '@/components/AppSidebar.vue'
import AppToast from '@/components/AppToast.vue'
import AppTopbar from '@/components/AppTopbar.vue'
import PageTabs from '@/components/PageTabs.vue'
import { useAgentStore } from '@/stores/agent'
import { useAuthStore } from '@/stores/auth'

const route = useRoute()
const auth = useAuthStore()
const agent = useAgentStore()

const sidebarOpen = ref(false)

/** Kirish va 404 sahifalari qobiqsiz ko'rsatiladi. */
const showShell = computed(() => route.meta.public !== true)
const title = computed(() => route.meta.title ?? '')
const description = computed(() => route.meta.description ?? '')

onMounted(async () => {
  if (auth.isAuthenticated && !auth.user) {
    try {
      await auth.loadProfile()
    } catch {
      // Token eskirgan — API mijozi kirish sahifasiga yuboradi
    }
  }

  // Chop etish agenti bormi. Javob bo'lmasa 300 ms dan keyin to'xtaydi
  // va ilova brauzer orqali chop etishda qoladi.
  void agent.probe()
})

watch(() => route.fullPath, () => (sidebarOpen.value = false))
</script>

<template>
  <AppIcons />

  <div v-if="showShell" class="app-shell">
    <AppSidebar :show="sidebarOpen" @close="sidebarOpen = false" />

    <div class="sidebar-overlay" :class="{ show: sidebarOpen }" @click="sidebarOpen = false"></div>

    <main class="main-area">
      <AppTopbar
        :title="title"
        :description="description"
        @toggle-sidebar="sidebarOpen = !sidebarOpen"
      />

      <div class="content">
        <PageTabs />

        <!-- Mahsulotlar ro'yxati saqlanib turadi: mahsulotni ochib orqaga
             qaytganda yuklangan ro'yxat va filtrlar yo'qolmasin -->
        <RouterView v-slot="{ Component }">
          <KeepAlive include="ProductListView">
            <component :is="Component" />
          </KeepAlive>
        </RouterView>
      </div>
    </main>

    <AppToast />
  </div>

  <RouterView v-else />
</template>
