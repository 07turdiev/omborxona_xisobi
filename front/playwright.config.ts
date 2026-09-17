import { defineConfig } from '@playwright/test'

/**
 * Chop etish regressiya testi uchun sozlama.
 *
 * Brauzer — Playwright bilan keladigan Chromium. Boshqa brauzerda
 * sinash kerak bo'lsa:
 *
 *   PLAYWRIGHT_CHANNEL=msedge npm run test:print
 *
 * Sinov qurilgan ilovaga qarshi o'tkaziladi (`vite preview`), chunki
 * chop etish uslublari faqat yakuniy CSS da to'liq ko'rinadi.
 *
 * Backend manzili `VITE_API_TARGET` dan olinadi — test ham, preview
 * proxysi ham bir xil manzilga qaraydi.
 */

const apiTarget = process.env.VITE_API_TARGET ?? 'http://127.0.0.1:8000'
const channel = process.env.PLAYWRIGHT_CHANNEL

export default defineConfig({
  testDir: './tests',
  timeout: 60_000,
  fullyParallel: false,
  workers: 1,
  reporter: [['list']],

  use: {
    baseURL: 'http://127.0.0.1:4173',
    headless: true,
    ...(channel ? { channel } : {}),
  },

  webServer: {
    command: 'npm run preview',
    url: 'http://127.0.0.1:4173',
    reuseExistingServer: true,
    timeout: 60_000,
    env: { VITE_API_TARGET: apiTarget },
  },
})
