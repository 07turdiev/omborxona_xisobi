<script setup lang="ts">
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const router = useRouter()
const route = useRoute()

const username = ref('')
const password = ref('')
const error = ref('')

async function onSubmit() {
  error.value = ''
  try {
    await auth.login(username.value, password.value)
    await router.push((route.query.redirect as string) ?? { name: 'home' })
  } catch {
    error.value = 'Login yoki parol noto‘g‘ri.'
  }
}
</script>

<template>
  <div class="flex min-h-screen items-center justify-center bg-slate-100 px-4">
    <form
      class="w-full max-w-sm space-y-4 rounded-xl bg-white p-8 shadow-sm"
      @submit.prevent="onSubmit"
    >
      <h1 class="text-xl font-semibold text-slate-900">Omborxona xisobi</h1>
      <p class="text-sm text-slate-500">Tizimga kirish uchun ma'lumotlaringizni kiriting.</p>

      <label class="block space-y-1">
        <span class="text-sm font-medium text-slate-700">Login</span>
        <input
          v-model="username"
          type="text"
          required
          autocomplete="username"
          class="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-slate-900"
        />
      </label>

      <label class="block space-y-1">
        <span class="text-sm font-medium text-slate-700">Parol</span>
        <input
          v-model="password"
          type="password"
          required
          autocomplete="current-password"
          class="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-slate-900"
        />
      </label>

      <p v-if="error" class="text-sm text-red-600">{{ error }}</p>

      <button
        type="submit"
        :disabled="auth.loading"
        class="w-full rounded-lg bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-800 disabled:opacity-50"
      >
        {{ auth.loading ? 'Kirilmoqda…' : 'Kirish' }}
      </button>
    </form>
  </div>
</template>
