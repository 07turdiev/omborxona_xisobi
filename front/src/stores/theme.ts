import { ref } from 'vue'
import { defineStore } from 'pinia'

const STORAGE_KEY = 'theme'

/**
 * Tungi rejim. Dizayn `body.dark-mode` sinfiga tayanadi
 * (store/app.css), shuning uchun shu yerda ham xuddi shunday.
 */
export const useThemeStore = defineStore('theme', () => {
  const isDark = ref(false)

  function apply() {
    document.body.classList.toggle('dark-mode', isDark.value)
  }

  function init() {
    try {
      const saved = localStorage.getItem(STORAGE_KEY)
      isDark.value = saved
        ? saved === 'dark'
        : window.matchMedia('(prefers-color-scheme: dark)').matches
    } catch {
      isDark.value = false
    }
    apply()
  }

  function toggle() {
    isDark.value = !isDark.value
    apply()
    try {
      localStorage.setItem(STORAGE_KEY, isDark.value ? 'dark' : 'light')
    } catch {
      // Shaxsiy oynada localStorage yopiq bo'lishi mumkin — muhim emas
    }
  }

  return { isDark, init, toggle }
})
