import { ref } from 'vue'
import { defineStore } from 'pinia'

/**
 * Qisqa xabar — ekran burchagida bir necha soniya turadi.
 *
 * Chop etish agenti orqali chek jimgina chiqadi: hech qanday oyna
 * ochilmaydi, shuning uchun kassirga "ketdi" degan belgi kerak.
 */
export const useToastStore = defineStore('toast', () => {
  const message = ref('')
  const kind = ref<'ok' | 'error'>('ok')

  let timer: ReturnType<typeof setTimeout> | null = null

  function show(text: string, type: 'ok' | 'error' = 'ok', ms = 2500) {
    message.value = text
    kind.value = type

    if (timer) clearTimeout(timer)
    timer = setTimeout(hide, ms)
  }

  function hide() {
    message.value = ''

    if (timer) {
      clearTimeout(timer)
      timer = null
    }
  }

  return { message, kind, show, hide }
})
