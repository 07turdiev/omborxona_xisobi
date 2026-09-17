import { defineConfig } from '@playwright/test'

/**
 * Chop etish regressiya testi uchun sozlama.
 *
 * Brauzer sifatida kompyuterdagi **Edge** ishlatiladi (`channel:
 * 'msedge'`): Playwright'ning o'z Chromium'ini yuklab olish shart
 * emas, chek va yorliq baribir Chromium dvigatelida chop etiladi.
 *
 * Sinov qurilgan ilovaga qarshi o'tkaziladi (`vite preview`), chunki
 * chop etish uslublari faqat yakuniy CSS da to'liq ko'rinadi.
 */

const apiTarget = process.env.VITE_API_TARGET ?? 'http://127.0.0.1:8004'

export default defineConfig({
  testDir: './tests',
  timeout: 60_000,
  fullyParallel: false,
  workers: 1,
  reporter: [['list']],

  use: {
    baseURL: 'http://127.0.0.1:4173',
    channel: 'msedge',
    headless: true,
  },

  webServer: {
    command: 'npm run preview',
    url: 'http://127.0.0.1:4173',
    reuseExistingServer: true,
    timeout: 60_000,
    env: { VITE_API_TARGET: apiTarget },
  },
})
