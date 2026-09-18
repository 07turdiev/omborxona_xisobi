<script setup lang="ts">
import { useToastStore } from '@/stores/toast'

const toast = useToastStore()
</script>

<template>
  <!-- Ilova qobig'i ichida turadi: chop etishda u yashiriladi
       (assets/main.css), ya'ni xabar qog'ozga tushmaydi -->
  <div v-if="toast.message" class="toast" :class="toast.kind" role="status" @click="toast.hide()">
    {{ toast.message }}
  </div>
</template>

<style scoped>
.toast {
  position: fixed;
  right: 16px;
  bottom: 16px;
  z-index: 60;

  max-width: 360px;
  padding: 10px 14px;

  border-radius: var(--radius);
  box-shadow: 0 4px 16px rgb(0 0 0 / 18%);

  background: var(--green);
  color: #fff;
  font-size: 13px;
  font-weight: 600;

  cursor: pointer;
}

.toast.error {
  background: var(--red);
}
</style>
