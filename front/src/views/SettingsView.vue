<script setup lang="ts">
import { onMounted, ref } from 'vue'

import { settingsApi } from '@/api/accounts'
import AmountField from '@/components/AmountField.vue'
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
  price_rounding_step: 1000,
  receipt_logo: null,
})

const loading = ref(true)
const saving = ref(false)
const logoBusy = ref(false)
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
    // Logotip alohida yuklanadi — shakl bilan yuborish shart emas
    const fields: Partial<ShopSettings> = { ...form.value }

    delete fields.receipt_logo

    const saved = await settingsApi.save(fields)

    form.value = saved
    auth.shop = saved
    notice.value = 'Saqlandi.'
  } catch (err) {
    error.value = errorMessage(err, 'Saqlab bo‘lmadi.')
  } finally {
    saving.value = false
  }
}

/**
 * Logotipni yuklaydi yoki olib tashlaydi.
 *
 * Shaklning boshqa maydonlariga tegilmaydi: ularda saqlanmagan
 * o'zgarish bo'lishi mumkin.
 */
async function changeLogo(action: () => Promise<ShopSettings>, done: string) {
  logoBusy.value = true
  error.value = ''
  notice.value = ''

  try {
    const saved = await action()

    form.value.receipt_logo = saved.receipt_logo
    auth.shop = saved
    notice.value = done
  } catch (err) {
    error.value = errorMessage(err, 'Logotipni saqlab bo‘lmadi.')
  } finally {
    logoBusy.value = false
  }
}

function onLogoChosen(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]

  // Xuddi o'sha faylni qayta tanlash ham ishlasin
  input.value = ''

  if (file) void changeLogo(() => settingsApi.uploadLogo(file), 'Logotip saqlandi.')
}

function removeLogo() {
  void changeLogo(() => settingsApi.removeLogo(), 'Logotip olib tashlandi.')
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
        <small class="field-hint">Chekda va tovar yorlig‘ida chiqadi.</small>
      </div>

      <div class="field">
        <label>Chek logotipi</label>

        <!-- Qog'ozdagidek: oq-qora va printerdagi o'lchamda (8 nuqta = 1 mm) -->
        <div v-if="form.receipt_logo" class="logo-paper">
          <img
            :src="form.receipt_logo.png"
            alt="Chek logotipi"
            :style="{ width: `${form.receipt_logo.width / 8}mm` }"
          />
        </div>

        <small class="field-hint">
          Chekda do‘kon nomi o‘rnida chiqadi. Rasm oq-qora qilinadi va chekka moslanadi — bu yerda
          ko‘ringani qog‘ozda chiqadi. Oq fonda to‘q rangli logotip yaxshi chiqadi.
        </small>

        <div class="logo-actions">
          <label class="button button-outline" :class="{ disabled: logoBusy }">
            <input
              type="file"
              accept="image/png,image/jpeg,image/webp"
              hidden
              :disabled="logoBusy"
              aria-label="Chek logotipi"
              @change="onLogoChosen"
            />
            {{ form.receipt_logo ? 'Almashtirish' : 'Logotip yuklash' }}
          </label>

          <button
            v-if="form.receipt_logo"
            class="button button-outline"
            type="button"
            :disabled="logoBusy"
            @click="removeLogo"
          >
            Olib tashlash
          </button>
        </div>
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
          Printer drayveridagi maxsus qog‘oz bilan bir xil bo‘lishi kerak —
          docs/hardware.md.
        </small>
      </div>

      <div class="field">
        <label>Narxni yaxlitlash qadami (so‘m)</label>
        <input v-model.number="form.price_rounding_step" type="number" min="1" step="100" />
      </div>

      <div class="field">
        <label>Kassir bera oladigan eng katta chegirma</label>
        <AmountField v-model="form.max_discount_percent" suffix="%" :grouped="false" />
      </div>

      <button class="button button-gradient" type="button" :disabled="saving" @click="onSave">
        {{ saving ? 'Saqlanmoqda…' : 'Saqlash' }}
      </button>
    </div>

  </section>
</template>

<style scoped>
.settings-card {
  max-width: 420px;
}

/* Logotip chek qog'ozidagidek: oq fon, printerdagi o'lcham */
.logo-paper {
  display: flex;
  justify-content: center;
  padding: 12px;
  border: 1px dashed var(--border);
  border-radius: var(--radius);
  background: #fff;
}

.logo-paper img {
  display: block;
  max-width: 100%;
  height: auto;
}

.logo-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 8px;
}

.logo-actions .disabled {
  opacity: 0.6;
  pointer-events: none;
}
</style>
