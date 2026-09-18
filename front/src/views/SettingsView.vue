<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'

import { settingsApi } from '@/api/accounts'
import { errorMessage } from '@/api/client'
import { useAuthStore } from '@/stores/auth'
import type { ShopSettings } from '@/types'

const auth = useAuthStore()

const form = ref<ShopSettings>({
  shop_name: '',
  label_width_mm: 40,
  label_height_mm: 30,
  receipt_width_mm: 80,
  receipt_page_height_mm: 110,
  max_discount_percent: '0',
})

const loading = ref(true)
const saving = ref(false)
const error = ref('')
const notice = ref('')

onMounted(async () => {
  try {
    form.value = await settingsApi.get()
  } catch (err) {
    error.value = errorMessage(err, 'Sozlamalarni yuklab bo‘lmadi.')
  } finally {
    loading.value = false
  }
})

async function onSave() {
  saving.value = true
  error.value = ''
  notice.value = ''

  try {
    const saved = await settingsApi.save(form.value)

    form.value = saved
    auth.shop = saved
    notice.value = 'Saqlandi.'
  } catch (err) {
    error.value = errorMessage(err, 'Saqlab bo‘lmadi.')
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <section class="app-section active">
    <p v-if="error" class="load-error">{{ error }}</p>
    <p v-if="notice" class="notice">{{ notice }}</p>

    <div v-if="!loading" class="table-card card-padded settings-card">
      <div class="field">
        <label>Do‘kon nomi</label>
        <input v-model="form.shop_name" type="text" />
        <small class="field-hint">Chek va yorliqlarda chiqadi.</small>
      </div>

      <div class="field">
        <label>Yorliq eni (mm)</label>
        <input v-model.number="form.label_width_mm" type="number" min="10" max="100" />
      </div>

      <div class="field">
        <label>Yorliq bo‘yi (mm)</label>
        <input v-model.number="form.label_height_mm" type="number" min="10" max="100" />
      </div>

      <div class="field">
        <label>Chek qog‘ozi eni (mm)</label>
        <input v-model.number="form.receipt_width_mm" type="number" min="50" max="120" />
      </div>

      <div class="field">
        <label>Chek sahifasi bo‘yi (mm)</label>
        <input v-model.number="form.receipt_page_height_mm" type="number" min="40" max="300" />
        <small class="field-hint">
          Bu ikki o‘lcham printer drayverida yaratilgan maxsus qog‘oz bilan
          <strong>aynan bir xil</strong> bo‘lishi kerak. Brauzer orqali chop
          etishda sahifa balandligini har chekka moslab bo‘lmaydi — uni
          drayver hal qiladi. Qanday qilish: docs/hardware.md.
        </small>
      </div>

      <div class="field">
        <label>Kassir bera oladigan eng katta chegirma (%)</label>
        <input v-model="form.max_discount_percent" type="text" inputmode="decimal" />
        <small class="field-hint">Administrator uchun cheklov yo‘q.</small>
      </div>

      <button class="button button-gradient" type="button" :disabled="saving" @click="onSave">
        {{ saving ? 'Saqlanmoqda…' : 'Saqlash' }}
      </button>
    </div>

    <div v-if="!loading" class="table-card card-padded settings-card">
      <h3>Qurilmalar</h3>

      <p class="field-hint">
        Printer va skanerni sinab ko‘rish: sinov yorlig‘i, sinov cheki va
        skaner maydoni. Yangi qurilma ulanganda shu yerdan tekshiring.
      </p>

      <RouterLink class="button button-outline" to="/settings/devices">
        Qurilmalarni sinash
      </RouterLink>
    </div>
  </section>
</template>

<style scoped>
.settings-card {
  max-width: 420px;
}
</style>
