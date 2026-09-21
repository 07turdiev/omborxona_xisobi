<script setup lang="ts">
import { nextTick, onMounted, ref } from 'vue'

/**
 * Shtrix-kod maydoni.
 *
 * USB skaner klaviatura kabi ishlaydi: kodni yozadi va Enter bosadi.
 * Shuning uchun Enter formani yubormaydi, balki `scan` hodisasini
 * chiqaradi va maydon darhol tozalanadi — keyingi skan uchun tayyor.
 */
withDefaults(
  defineProps<{ placeholder?: string; disabled?: boolean; label?: string }>(),
  { placeholder: 'Shtrix-kodni skanerlang', disabled: false, label: '' },
)

const emit = defineEmits<{ scan: [code: string] }>()

const code = ref('')
const input = ref<HTMLInputElement | null>(null)

function onEnter() {
  const value = code.value.trim()

  code.value = ''

  if (value) emit('scan', value)
}

/** Har amaldan keyin fokus shu yerga qaytadi. */
async function focus() {
  await nextTick()
  input.value?.focus()
  input.value?.select()
}

onMounted(focus)

defineExpose({ focus })
</script>

<template>
  <div class="scan-field">
    <svg><use href="#i-search" /></svg>

    <input
      ref="input"
      v-model="code"
      type="text"
      autocomplete="off"
      :placeholder="placeholder"
      :disabled="disabled"
      :aria-label="label || placeholder"
      @keydown.enter.prevent="onEnter"
    />
  </div>
</template>

<style scoped>
.scan-field {
  display: flex;
  align-items: center;
  gap: 8px;
  height: 44px;
  padding: 0 12px;
  border: 2px solid var(--accent);
  border-radius: var(--radius);
  background: var(--surface);
}

.scan-field svg {
  width: 18px;
  height: 18px;
  flex-shrink: 0;
  fill: none;
  stroke: var(--accent);
  stroke-width: 2;
}

.scan-field input {
  width: 100%;
  min-height: 0;
  border: 0;
  background: none;
  box-shadow: none;
  font-size: 17px;
}
</style>
