<script setup lang="ts"></script>

<template>
  <section class="app-section active">
    <div class="table-card card-padded not-found">
      <strong>404</strong>
      <h3>Bunday sahifa topilmadi</h3>
      <p>Havola eskirgan yoki manzil noto‘g‘ri yozilgan bo‘lishi mumkin.</p>

      <RouterLink to="/" class="button button-gradient">
        Boshqaruv paneliga qaytish
      </RouterLink>
    </div>
  </section>
</template>

<style scoped>
/* Bu sahifa oldin Tailwind sinflaridan foydalanardi. Tailwind
   loyihadan olib tashlangan (assets/main.css), shuning uchun u
   umuman uslubsiz chiqardi. */
.not-found {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 48px 20px;
  text-align: center;
}

.not-found strong {
  color: var(--text-muted);
  font-size: 28px;
  font-weight: 600;
  font-variant-numeric: tabular-nums;
}

.not-found h3 {
  font-size: 16px;
  font-weight: 600;
}

.not-found p {
  margin-bottom: 8px;
  color: var(--text-muted);
  font-size: 13px;
}
</style>
