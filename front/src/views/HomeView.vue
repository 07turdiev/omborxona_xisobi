<script setup lang="ts">
import { onMounted } from 'vue'

import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()

onMounted(() => {
  if (!auth.user) auth.fetchMe()
})
</script>

<template>
  <section class="space-y-4">
    <h1 class="text-2xl font-semibold text-slate-900">Bosh sahifa</h1>
    <p class="text-slate-600">
      Xush kelibsiz<span v-if="auth.user">, {{ auth.user.first_name || auth.user.username }}</span>!
    </p>

    <div class="rounded-xl border border-slate-200 bg-white p-6">
      <p class="text-sm text-slate-500">
        Omborxona modullari shu yerda joylashadi — mahsulotlar, kirim/chiqim, qoldiqlar, hisobotlar.
      </p>
    </div>
  </section>
</template>
