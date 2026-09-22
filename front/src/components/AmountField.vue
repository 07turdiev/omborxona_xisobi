<script setup lang="ts">
/**
 * Pul va foiz maydoni.
 *
 * Ikki narsa qiladi: yozayotganda raqamlarni uchtadan ajratadi
 * («100 000») va o'ng chetda birlikni ko'rsatadi («so'm», «%»).
 *
 * Nega kerak: do'kon summalari olti xonali bo'ladi, ajratuvchisiz
 * kassir nollarni sanab o'tirishga majbur. Birlik esa maydon nima
 * so'rayotganini aytadi — foiz bilan summani chalkashtirmaslik uchun.
 *
 * Qiymat satr bo'lib chiqadi, ichida probel bilan. `utils/money.ts`
 * dagi hisob probelni tashlab yuboradi, shuning uchun uni qayta
 * tozalash shart emas.
 */

import { computed, ref } from 'vue'

const props = withDefaults(
  defineProps<{
    modelValue: string
    /** O'ng chetdagi birlik */
    suffix?: string
    /** Uchtadan ajratish. Foizda kerak emas — u ikki xonali. */
    grouped?: boolean
    placeholder?: string
    disabled?: boolean
  }>(),
  { suffix: 'so‘m', grouped: true, placeholder: '', disabled: false },
)

const emit = defineEmits<{ 'update:modelValue': [value: string] }>()

// `aria-label`, `id` va boshqalar ichkaridagi `input` ga tushsin
defineOptions({ inheritAttrs: false })

const input = ref<HTMLInputElement | null>(null)

const display = computed(() => format(props.modelValue))

/** «100000,5» → «100 000,5». Faqat raqam va bitta kasr belgisi qoladi. */
function format(value: string): string {
  const cleaned = String(value ?? '').replace(/[^\d.,]/g, '')
  const [whole = '', ...rest] = cleaned.split(/[.,]/)

  if (!props.grouped) return rest.length ? `${whole},${rest.join('')}` : whole

  // Uzilmaydigan probel: son qatorga bo'linib ketmasin
  const groups = whole.replace(/\B(?=(\d{3})+(?!\d))/g, ' ')

  return rest.length ? `${groups},${rest.join('').slice(0, 2)}` : groups
}

function onInput(event: Event) {
  const element = event.target as HTMLInputElement

  // Karet joyi raqamlar soni bilan o'lchanadi: probel qo'shilganda
  // kursor o'z-o'zidan oxiriga sakrab ketmasin
  const before = element.value.slice(0, element.selectionStart ?? 0)
  const digits = (before.match(/\d/g) ?? []).length

  const formatted = format(element.value)

  element.value = formatted
  emit('update:modelValue', formatted)

  let position = 0
  let seen = 0

  while (position < formatted.length && seen < digits) {
    if (/\d/.test(formatted[position]!)) seen += 1
    position += 1
  }

  element.setSelectionRange(position, position)
}

defineExpose({
  focus: () => input.value?.focus(),
  select: () => input.value?.select(),
})
</script>

<template>
  <span class="amount-field" :class="{ disabled }">
    <input
      ref="input"
      v-bind="$attrs"
      type="text"
      inputmode="decimal"
      autocomplete="off"
      :value="display"
      :placeholder="placeholder"
      :disabled="disabled"
      @input="onInput"
    />

    <small v-if="suffix">{{ suffix }}</small>
  </span>
</template>

<style scoped>
.amount-field {
  display: flex;
  align-items: center;
  gap: 6px;
  width: 100%;
  min-height: var(--control-height);
  padding: 0 12px;
  border: 1px solid var(--border-strong);
  border-radius: var(--radius);
  background: var(--surface);
}

/* Fokus belgisi o'ramda — ichkaridagi maydonda emas. Aks holda global
   `:focus-visible` konturi maydon ichida ikkinchi ramka bo'lib chiqadi. */
.amount-field:focus-within {
  border-color: var(--accent);
  box-shadow: 0 0 0 3px var(--accent-soft);
}

.amount-field.disabled {
  background: var(--surface-soft);
}

.amount-field input {
  width: 100%;
  min-width: 0;
  min-height: 0;
  padding: 0;
  border: 0;
  border-radius: 0;
  background: none;
  box-shadow: none;
  font-variant-numeric: tabular-nums;
}

.amount-field input:focus,
.amount-field input:focus-visible {
  border: 0;
  outline: none;
  box-shadow: none;
}

.amount-field small {
  flex: none;
  color: var(--text-muted);
  font-size: 13px;
  white-space: nowrap;
}
</style>
