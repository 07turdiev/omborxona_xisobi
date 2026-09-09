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

/** Foydalanuvchi bir nechta tashkilotda ishlasa, almashtirish taklif qilinadi. */
const memberships = computed(() => auth.user?.memberships ?? [])
const hasMultiple = computed(() => memberships.value.length > 1)
const currentTenantId = computed(() => auth.user?.current_tenant?.tenant_id ?? '')

function onSwitch(tenantId: string) {
  if (tenantId === currentTenantId.value) {
    menuOpen.value = false
    return
  }

  auth.switchTenant(tenantId)
}

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

          <div v-if="hasMultiple" class="tenant-switch">
            <span class="switch-caption">Tashkilotni almashtirish</span>

            <button
              v-for="item in memberships"
              :key="item.tenant_id"
              class="tenant-option"
              :class="{ active: item.tenant_id === currentTenantId }"
              type="button"
              @click="onSwitch(item.tenant_id)"
            >
              <span>
                <strong>{{ item.tenant_name }}</strong>
                <small>{{ item.role_display }}</small>
              </span>

              <b v-if="item.tenant_id === currentTenantId" class="tick">✓</b>
            </button>
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

<style scoped>
/* Tashkilot almashtirish — dizaynda bunday blok yo'q edi, ranglar
   app.css o'zgaruvchilaridan olingan. */
.tenant-switch {
  padding: 8px 0;
  border-top: 1px solid var(--border);
}

.switch-caption {
  display: block;
  padding: 0 12px 6px;
  color: var(--text-muted);
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.08em;
}

.tenant-option {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  width: 100%;
  padding: 7px 12px;
  border: none;
  background: none;
  color: var(--text);
  text-align: left;
  cursor: pointer;
  transition: var(--transition);
}

.tenant-option:hover {
  background: var(--surface-hover);
}

.tenant-option.active {
  background: var(--accent-soft);
}

.tenant-option strong {
  display: block;
  font-size: 13px;
}

.tenant-option small {
  display: block;
  margin-top: 1px;
  color: var(--text-muted);
  font-size: 11px;
}

.tick {
  color: var(--accent);
  font-size: 14px;
}
</style>
