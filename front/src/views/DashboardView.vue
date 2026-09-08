<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'

import { useAuthStore } from '@/stores/auth'
import { useWarehouseStore } from '@/stores/warehouses'

const auth = useAuthStore()
const warehouses = useWarehouseStore()
const router = useRouter()

const today = computed(() =>
  new Intl.DateTimeFormat('uz-UZ', {
    day: 'numeric',
    month: 'long',
    year: 'numeric',
  }).format(new Date()),
)

const firstName = computed(() => auth.user?.first_name || auth.user?.username || '')

onMounted(() => warehouses.loadSummary())
</script>

<template>
  <section class="app-section active">
    <div class="hero-card">
      <div class="hero-orb orb-one"></div>
      <div class="hero-orb orb-two"></div>

      <div class="hero-content">
        <span class="hero-date">{{ today }}</span>

        <h2>Xush kelibsiz, {{ firstName }}</h2>

        <p>Barcha omborlar, kirim va sotuvlarni yagona tizimda boshqaring.</p>
      </div>

      <div class="hero-actions">
        <button class="button button-glass" @click="router.push('/warehouses')">
          <svg><use href="#i-warehouse" /></svg>
          <span>Omborlar</span>
        </button>

        <button class="button button-white" @click="router.push('/units')">
          <svg><use href="#i-settings" /></svg>
          <span>O‘lchov birliklari</span>
        </button>
      </div>
    </div>

    <div class="kpi-grid">
      <article class="kpi-card kpi-purple">
        <div class="kpi-icon"><svg><use href="#i-warehouse" /></svg></div>
        <p>Jami omborlar</p>
        <strong>{{ warehouses.summary?.total ?? 0 }}</strong>
      </article>

      <article class="kpi-card kpi-teal">
        <div class="kpi-icon"><svg><use href="#i-warehouse" /></svg></div>
        <p>Faol omborlar</p>
        <strong>{{ warehouses.summary?.active ?? 0 }}</strong>
      </article>

      <article class="kpi-card kpi-green">
        <div class="kpi-icon"><svg><use href="#i-sale" /></svg></div>
        <p>Sotuvga chiqadigan</p>
        <strong>{{ warehouses.summary?.sellable ?? 0 }}</strong>
        <small>tranzit hisobga olinmaydi</small>
      </article>

      <article class="kpi-card kpi-blue">
        <div class="kpi-icon"><svg><use href="#i-stock" /></svg></div>
        <p>Qoldiqlar</p>
        <strong>—</strong>
        <small>keyingi bosqichda</small>
      </article>
    </div>

    <div class="table-card build-note">
      <h3>Qurilish holati</h3>

      <p>
        Hozircha <strong>omborlar</strong> va <strong>o‘lchov birliklari</strong> modullari
        ishlaydi. Keyingi navbatda mahsulotlar katalogi, kirim, sotuv va qoldiqlar.
      </p>

      <p class="muted">
        Chap menyudagi qolgan bo‘limlar hali ulanmagan — ular bo‘sh sahifa ochadi.
      </p>
    </div>
  </section>
</template>

<style scoped>
.build-note {
  padding: 20px 22px;
}

.build-note h3 {
  margin-bottom: 8px;
  font-size: 11px;
}

.build-note p {
  font-size: 8px;
  line-height: 1.6;
  color: var(--text-secondary);
}

.build-note .muted {
  margin-top: 6px;
  color: var(--text-muted);
}
</style>
