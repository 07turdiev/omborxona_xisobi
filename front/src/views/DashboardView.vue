<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'

import { errorMessage } from '@/api/client'
import { reportsApi } from '@/api/reports'
import { formatMoney } from '@/utils/money'
import type { Dashboard } from '@/types'

const data = ref<Dashboard | null>(null)
const loading = ref(true)
const error = ref('')

onMounted(async () => {
  try {
    data.value = await reportsApi.dashboard()
  } catch (err) {
    error.value = errorMessage(err, 'Ma’lumotlarni yuklab bo‘lmadi.')
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <section class="app-section active">
    <p v-if="error" class="load-error">{{ error }}</p>
    <p v-else-if="loading" class="empty-state">Yuklanmoqda…</p>

    <template v-else-if="data">
      <!-- Ingichka bezak lenta: raqamlar baribir birinchi ekranda qoladi -->
      <header class="shop-banner">
        <p class="banner-name">Madlen sen</p>
        <p class="banner-sub">Ayollar kiyimlari do‘koni</p>
      </header>

      <!-- Xodim ishni shu yerdan boshlaydi: nima qilmoqchi bo'lsa, shu -->
      <nav class="actions" aria-label="Asosiy amallar">
        <RouterLink class="action" to="/">
          <span class="action-icon"><svg><use href="#i-sale" /></svg></span>
          <strong>Tovar sotish</strong>
          <small>Kassa: sotib, chek chiqarasiz</small>
        </RouterLink>

        <RouterLink class="action" to="/purchases">
          <span class="action-icon"><svg><use href="#i-import" /></svg></span>
          <strong>Tovar qabul qilish</strong>
          <small>Yangi kelgan tovarni kiritib, yorlig‘ini chiqarasiz</small>
        </RouterLink>

        <RouterLink class="action" to="/products">
          <span class="action-icon"><svg><use href="#i-catalog" /></svg></span>
          <strong>Tovarlar va yorliqlar</strong>
          <small>Qidirish, narxini ko‘rish, yorliqni qayta chop etish</small>
        </RouterLink>

        <RouterLink class="action" to="/stock-counts">
          <span class="action-icon"><svg><use href="#i-warehouse" /></svg></span>
          <strong>Sanoq</strong>
          <small>Javondagi tovarni sanab, tizim bilan solishtirasiz</small>
        </RouterLink>
      </nav>

      <h3 class="block-title">Bugun</h3>

      <div class="kpi-row">
        <div class="kpi-card">
          <span>Tushum</span>
          <strong>{{ formatMoney(data.today.revenue) }}</strong>
        </div>

        <div class="kpi-card">
          <span>Cheklar</span>
          <strong>{{ data.today.receipts }}</strong>
        </div>

        <div class="kpi-card">
          <span>O‘rtacha chek</span>
          <strong>{{ formatMoney(data.today.average_receipt) }}</strong>
        </div>

        <div class="kpi-card">
          <span>Yalpi foyda</span>
          <strong>{{ formatMoney(data.today.gross_profit) }}</strong>
        </div>
      </div>

      <h3 class="block-title">Shu oy</h3>

      <div class="kpi-row">
        <div class="kpi-card">
          <span>Tushum</span>
          <strong>{{ formatMoney(data.month.revenue) }}</strong>
        </div>

        <div class="kpi-card">
          <span>Cheklar</span>
          <strong>{{ data.month.receipts }}</strong>
        </div>

        <div class="kpi-card">
          <span>O‘rtacha chek</span>
          <strong>{{ formatMoney(data.month.average_receipt) }}</strong>
        </div>

        <div class="kpi-card">
          <span>Yalpi foyda</span>
          <strong>{{ formatMoney(data.month.gross_profit) }}</strong>
        </div>
      </div>

      <div class="table-card card-padded low-stock">
        <div>
          <strong>Qoldig‘i kam tovarlar: {{ data.low_stock_count }} ta</strong>
          <small class="cell-sub">Eng kam qoldiq chegarasidan pastga tushganlari</small>
        </div>

        <RouterLink class="button button-outline" to="/products?low_stock=true">Tugayotganlarni ko‘rish</RouterLink>
      </div>
    </template>
  </section>
</template>

<style scoped>
/* Do'kon lentasi — balandligi 72px: 1366x768 ekranda ikkala
   raqamlar qatori ham birinchi ekranda qoladi */
.shop-banner {
  display: flex;
  flex-direction: column;
  justify-content: center;
  height: 72px;
  margin-bottom: 14px;
  padding: 0 22px;
  overflow: hidden;
  border-radius: var(--radius-card);
  background:
    linear-gradient(90deg, rgb(28 22 18 / 88%) 25%, rgb(28 22 18 / 45%)),
    url("../assets/boutique.webp") center 38% / cover no-repeat,
    #2b221b;
  color: #f7ecd8;
}

.banner-name {
  font-family: var(--font-display);
  font-size: 28px;
  line-height: 1.1;
}

.banner-sub {
  margin-top: 3px;
  color: #d8c6a6;
  font-size: 11px;
  letter-spacing: 2.4px;
  text-transform: uppercase;
}

.actions {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: 12px;
  margin-bottom: 18px;
}

.action {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 16px 18px;
  border: 1px solid var(--border);
  border-radius: var(--radius-card);
  background: var(--surface);
  box-shadow: var(--shadow);
  color: inherit;
  text-decoration: none;
  transition:
    transform 0.15s,
    box-shadow 0.15s;
}

.action:hover {
  transform: translateY(-2px);
  border-color: var(--gold-line, var(--accent));
  box-shadow: var(--shadow-large);
}

.action-icon {
  display: grid;
  place-items: center;
  width: 44px;
  height: 44px;
  margin-bottom: 8px;
  border-radius: var(--radius);
  background: var(--accent-soft);
  color: var(--accent);
}

.action-icon svg {
  width: 22px;
  height: 22px;
  fill: none;
  stroke: currentColor;
  stroke-width: 1.7;
  stroke-linecap: round;
  stroke-linejoin: round;
}

.action strong {
  font-size: 17px;
  font-weight: 600;
}

.action small {
  color: var(--text-muted);
  font-size: 13px;
  line-height: 1.5;
}

.block-title {
  margin: 0 0 8px;
  font-size: 15px;
}

.kpi-row {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 12px;
  margin-bottom: 20px;
}

.kpi-card {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 16px 18px;
  border: 1px solid var(--border);
  border-radius: var(--radius-card);
  background: var(--surface);
  box-shadow: var(--shadow);
}

.kpi-card span {
  color: var(--text-muted);
  font-size: 13px;
}

.kpi-card strong {
  font-size: 22px;
  font-variant-numeric: tabular-nums;
}

.low-stock {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}
</style>
