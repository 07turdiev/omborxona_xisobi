<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { useAuthStore } from '@/stores/auth'
import logoUrl from '@/assets/logo.png'

import '@/assets/login.css'

const auth = useAuthStore()
const router = useRouter()
const route = useRoute()

const username = ref('')
const password = ref('')
const showPassword = ref(false)
const error = ref('')

// Login sahifasi o'z fonini oladi — dizayndagi `body.login-page`.
onMounted(() => document.body.classList.add('login-page'))
onBeforeUnmount(() => document.body.classList.remove('login-page'))

async function onSubmit() {
  error.value = ''

  try {
    await auth.login(username.value, password.value)
    // Kassir boshqaruv paneliga kira olmaydi — hamma kassadan boshlaydi
    await router.push((route.query.redirect as string) ?? { name: 'pos' })
  } catch {
    error.value = 'Login yoki parol noto‘g‘ri.'
  }
}
</script>

<template>
  <main class="login-layout">
    <!-- Chap taraf: faqat logotip. Nomi logotipning o'zida yozilgan,
         shuning uchun yonida matn takrorlanmaydi. -->
    <section class="login-showcase">
      <div class="showcase-content">
        <img class="brand-mark" :src="logoUrl" alt="Madlen sen" />
      </div>
    </section>

    <section class="login-panel">
      <div class="login-box">
        <!-- Telefonda chap panel yashirin — logotip shu yerda ko'rinadi -->
        <div class="mobile-brand">
          <img class="brand-mark small" :src="logoUrl" alt="Madlen sen" />
        </div>

        <div class="login-heading">
          <h2>Tizimga kirish</h2>
        </div>

        <div v-if="error" class="login-message show" role="alert">
          <div class="message-icon">
            <svg viewBox="0 0 24 24">
              <circle cx="12" cy="12" r="9" />
              <path d="M12 8V12" />
              <path d="M12 16H12.01" />
            </svg>
          </div>

          <span>{{ error }}</span>

          <button type="button" aria-label="Yopish" @click="error = ''">×</button>
        </div>

        <form class="login-form" autocomplete="off" @submit.prevent="onSubmit">
          <div class="form-group">
            <label for="username">Login</label>

            <div class="input-wrapper">
              <div class="input-icon">
                <svg viewBox="0 0 24 24">
                  <circle cx="12" cy="8" r="4" />
                  <path d="M4 21C4 16.58 7.58 13 12 13C16.42 13 20 16.58 20 21" />
                </svg>
              </div>

              <input
                id="username"
                v-model="username"
                type="text"
                required
                autocomplete="username"
                placeholder="admin"
              />
            </div>
          </div>

          <div class="form-group">
            <label for="password">Parol</label>

            <div class="input-wrapper">
              <div class="input-icon">
                <svg viewBox="0 0 24 24">
                  <rect x="4" y="10" width="16" height="11" rx="2" />
                  <path d="M8 10V7A4 4 0 0 1 16 7V10" />
                </svg>
              </div>

              <input
                id="password"
                v-model="password"
                :type="showPassword ? 'text' : 'password'"
                required
                autocomplete="current-password"
                placeholder="••••••••"
              />

              <button
                class="password-toggle"
                type="button"
                :aria-label="showPassword ? 'Parolni yashirish' : 'Parolni ko‘rsatish'"
                @click="showPassword = !showPassword"
              >
                <svg v-if="!showPassword" class="eye-open" viewBox="0 0 24 24">
                  <path
                    d="M2 12C4.5 7.5 7.8 5.5 12 5.5C16.2 5.5 19.5 7.5 22 12C19.5 16.5 16.2 18.5 12 18.5C7.8 18.5 4.5 16.5 2 12Z"
                  />
                  <circle cx="12" cy="12" r="3" />
                </svg>

                <svg v-else class="eye-closed" viewBox="0 0 24 24">
                  <path d="M3 3L21 21" />
                  <path
                    d="M10.5 5.7C11 5.57 11.5 5.5 12 5.5C16.2 5.5 19.5 7.5 22 12C21.2 13.44 20.3 14.63 19.28 15.58"
                  />
                  <path
                    d="M16.5 17.3C15.12 18.1 13.62 18.5 12 18.5C7.8 18.5 4.5 16.5 2 12C3.05 10.11 4.25 8.65 5.61 7.59"
                  />
                  <path
                    d="M9.88 9.88C9.34 10.42 9 11.17 9 12C9 13.66 10.34 15 12 15C12.83 15 13.58 14.66 14.12 14.12"
                  />
                </svg>
              </button>
            </div>
          </div>

          <button class="login-button" type="submit" :disabled="auth.loading">
            <span v-if="!auth.loading" class="button-content">
              <span>Tizimga kirish</span>

              <svg viewBox="0 0 24 24">
                <path d="M5 12H19" />
                <path d="M14 7L19 12L14 17" />
              </svg>
            </span>

            <span v-else class="button-loading">
              <span class="spinner"></span>
              Tekshirilmoqda...
            </span>
          </button>
        </form>
      </div>
    </section>
  </main>
</template>

<style scoped>
/* Logotip chap panelning o'rtasida turadi */
.showcase-content {
  align-items: center;
  justify-content: center;
}

.brand-mark {
  width: min(460px, 78%);
  height: auto;
  /* Oltin rang to'q fonda o'zi yorqin — qo'shimcha soya kerak emas */
}

.brand-mark.small {
  width: 220px;
}
</style>
