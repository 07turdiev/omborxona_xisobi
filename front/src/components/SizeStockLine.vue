<script setup lang="ts">
import type { SizeStock } from '@/types'

/** "S 2 · M 0 · L 5" — qaysi o'lcham qolgani bir qarashda. */
defineProps<{ entries: SizeStock[] }>()
</script>

<template>
  <span class="size-line">
    <span
      v-for="entry in entries"
      :key="entry.size_id"
      class="size-entry"
      :class="{ zero: !entry.quantity }"
    >
      {{ entry.size_name }}&nbsp;{{ entry.quantity }}
    </span>
  </span>
</template>

<style scoped>
.size-line {
  color: var(--text-secondary);
  font-size: 12px;
  font-variant-numeric: tabular-nums;
}

.size-entry {
  white-space: nowrap;
}

.size-entry + .size-entry::before {
  content: '·';
  margin: 0 5px;
  color: var(--text-muted);
}

/* Tugagan o'lcham ham ko'rinadi — "M tugagan" ham javob */
.size-entry.zero {
  color: var(--gray-5);
}
</style>
