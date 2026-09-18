<script setup lang="ts">
import { computed } from 'vue'
import { RouterLink, useRoute } from 'vue-router'

import { SECTION_TABS } from '@/navigation'
import { useAuthStore } from '@/stores/auth'

const route = useRoute()
const auth = useAuthStore()

/** Bo'lim ichidagi sahifalar. Bittadan iborat guruh tab qilib ko'rsatilmaydi. */
const tabs = computed(() => {
  if (route.meta.hideTabs) return []

  const visible = (SECTION_TABS[route.meta.section ?? ''] ?? []).filter(
    (tab) => !tab.admin || auth.isAdmin,
  )

  return visible.length > 1 ? visible : []
})
</script>

<template>
  <nav v-if="tabs.length" class="page-tabs" aria-label="Bo‘lim sahifalari">
    <RouterLink
      v-for="tab in tabs"
      :key="tab.to"
      class="page-tab"
      :class="{ active: route.path === tab.to }"
      :aria-current="route.path === tab.to ? 'page' : undefined"
      :to="tab.to"
    >
      {{ tab.label }}
    </RouterLink>
  </nav>
</template>

<style scoped>
.page-tabs {
  display: flex;
  gap: 4px;
  margin: -4px 0 12px;
  overflow-x: auto;
  border-bottom: 1px solid var(--border);
  scrollbar-width: none;
}

.page-tab {
  flex: none;
  padding: 8px 14px;
  border-bottom: 2px solid transparent;
  color: var(--text-muted);
  font-size: 13px;
  font-weight: 600;
  text-decoration: none;
  white-space: nowrap;
}

.page-tab:hover {
  color: var(--text);
}

.page-tab.active {
  border-bottom-color: var(--accent);
  color: var(--text);
}

@media (pointer: coarse) {
  .page-tab {
    padding: 12px 14px;
  }
}
</style>
