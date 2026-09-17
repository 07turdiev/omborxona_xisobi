import { fileURLToPath, URL } from 'node:url'

import { defineConfig } from 'vitest/config'
import vue from '@vitejs/plugin-vue'
import vueDevTools from 'vite-plugin-vue-devtools'

// Backend manzili. 8000 port boshqa loyihada band bo'lsa:
//   VITE_API_TARGET=http://127.0.0.1:8001 npm run dev
const apiTarget = process.env.VITE_API_TARGET ?? 'http://127.0.0.1:8000'

// https://vite.dev/config/
export default defineConfig({
  plugins: [vue(), vueDevTools()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  server: {
    port: 5173,
    proxy: {
      // Django backend'ga proxy — CORS'siz ishlash uchun
      '/api': {
        target: apiTarget,
        changeOrigin: true,
      },
      '/media': {
        target: apiTarget,
        changeOrigin: true,
      },
    },
  },
  // Qurilgan ilovani sinash uchun (chop etish testi shu yerda ishlaydi)
  preview: {
    // `localhost` Windows'da IPv6 (::1) ga hal bo'ladi, test esa IPv4
    // manzilni so'raydi — shuning uchun manzil aniq yozilgan
    host: '127.0.0.1',
    port: 4173,
    strictPort: true,
    proxy: {
      '/api': {
        target: apiTarget,
        changeOrigin: true,
      },
      '/media': {
        target: apiTarget,
        changeOrigin: true,
      },
    },
  },
  test: {
    // Pul hisobi sof funksiyalar — brauzer muhiti kerak emas
    environment: 'node',
    include: ['src/**/*.spec.ts'],
  },
})
