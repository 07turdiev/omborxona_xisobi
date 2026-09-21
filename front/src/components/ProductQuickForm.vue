<script setup lang="ts">
import { nextTick, onMounted, ref } from 'vue'

import { catalogApi } from '@/api/catalog'
import { errorMessage } from '@/api/client'
import { normalizeMoneyInput } from '@/utils/money'
import type { Category, Color, Product, Size } from '@/types'

/**
 * Kirim ekranidagi ixcham "Yangi mahsulot" formasi.
 *
 * Tovar do'konga birinchi marta kelganda uni shu yerda yaratish kerak:
 * ilgari administrator Mahsulotlar sahifasiga o'tib, modelni yaratib,
 * keyin kirimga qaytardi va har variantning 13 xonali kodini qo'lda
 * terardi.
 *
 * Bu yerda faqat qabul qilish uchun kerak bo'lgan maydonlar bor.
 * Tavsif, tarkib, MXIK va rasm — mahsulot sahifasida, keyinroq.
 *
 * `barcode` berilgan bo'lsa (noma'lum kod skanerlangan), mahsulot
 * bitta variantli bo'ladi va o'sha kod shu variantga yoziladi.
 */

const props = defineProps<{ barcode?: string }>()

const emit = defineEmits<{ created: [product: Product]; close: [] }>()

const categories = ref<Category[]>([])
const sizes = ref<Size[]>([])
const colors = ref<Color[]>([])

const saving = ref(false)
const error = ref('')

/** Ro'yxatlar kelmaguncha saqlash yopiq: kategoriyasiz mahsulot bo'lmaydi */
const ready = ref(false)

const nameInput = ref<HTMLInputElement | null>(null)

const form = ref({
  category: 0,
  name: '',
  brand: '',
  sale_price: '',
  size_ids: [] as number[],
  color_ids: [] as number[],
})

onMounted(async () => {
  try {
    ;[categories.value, sizes.value, colors.value] = await Promise.all([
      catalogApi.categories(),
      catalogApi.sizes(),
      catalogApi.colors(),
    ])

    form.value.category = categories.value[0]?.id ?? 0
    ready.value = Boolean(form.value.category)
  } catch (err) {
    error.value = errorMessage(err, 'Ro‘yxatlarni yuklab bo‘lmadi.')
  }

  await nextTick()
  nameInput.value?.focus()
})

function toggle(list: number[], id: number) {
  const index = list.indexOf(id)

  if (index === -1) list.push(id)
  else list.splice(index, 1)
}

async function onSave() {
  if (!form.value.name.trim() || saving.value) return

  saving.value = true
  error.value = ''

  try {
    const product = await catalogApi.createProduct({
      category: form.value.category,
      name: form.value.name.trim(),
      brand: form.value.brand.trim(),
      sale_price: normalizeMoneyInput(form.value.sale_price || '0'),
      size_ids: props.barcode ? [] : form.value.size_ids,
      color_ids: props.barcode ? [] : form.value.color_ids,
    })

    // Skanerlangan kod yangi variantga yoziladi — keyingi safar shu
    // tovar skanerlanganda topiladi
    if (props.barcode && product.variants.length === 1) {
      const variant = await catalogApi.updateVariant(product.variants[0]!.id, {
        barcode: props.barcode,
      })

      product.variants = [variant]
    }

    emit('created', product)
  } catch (err) {
    error.value = errorMessage(err, 'Mahsulotni saqlab bo‘lmadi.')
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <div class="quick-form" data-testid="quick-product">
    <div class="quick-head">
      <strong>Yangi mahsulot</strong>

      <button class="icon-button" type="button" aria-label="Yopish" @click="emit('close')">
        <svg><use href="#i-close" /></svg>
      </button>
    </div>

    <p v-if="error" class="load-error">{{ error }}</p>

    <p v-if="barcode" class="field-hint barcode-note">
      Skanerlangan kod <strong>{{ barcode }}</strong> shu mahsulotning yagona
      variantiga yoziladi. O‘lcham va ranglarni keyin mahsulot sahifasida
      qo‘shasiz.
    </p>

    <div class="quick-row">
      <label class="field">
        <span>Kategoriya</span>
        <select v-model.number="form.category" aria-label="Kategoriya">
          <option v-for="item in categories" :key="item.id" :value="item.id">{{ item.name }}</option>
        </select>
      </label>

      <label class="field wide">
        <span>Nomi</span>
        <input ref="nameInput" v-model="form.name" type="text" aria-label="Mahsulot nomi" />
      </label>

      <label class="field">
        <span>Brend</span>
        <input v-model="form.brand" type="text" aria-label="Brend" placeholder="Majburiy emas" />
      </label>

      <label class="field">
        <span>Sotuv narxi</span>
        <input
          v-model="form.sale_price"
          type="text"
          inputmode="decimal"
          aria-label="Sotuv narxi"
          placeholder="0"
        />
      </label>
    </div>

    <template v-if="!barcode">
      <div class="field">
        <span class="field-label">O‘lchamlar</span>

        <div class="chips" role="group" aria-label="O‘lchamlar">
          <button
            v-for="item in sizes"
            :key="item.id"
            class="chip"
            :class="{ active: form.size_ids.includes(item.id) }"
            type="button"
            :aria-pressed="form.size_ids.includes(item.id)"
            @click="toggle(form.size_ids, item.id)"
          >
            {{ item.name }}
          </button>
        </div>
      </div>

      <div class="field">
        <span class="field-label">Ranglar</span>

        <div class="chips" role="group" aria-label="Ranglar">
          <button
            v-for="item in colors"
            :key="item.id"
            class="chip"
            :class="{ active: form.color_ids.includes(item.id) }"
            type="button"
            :aria-pressed="form.color_ids.includes(item.id)"
            @click="toggle(form.color_ids, item.id)"
          >
            <span class="chip-dot" :style="{ background: item.hex_code }" />
            {{ item.name }}
          </button>
        </div>

        <small class="field-hint">
          Har o‘lcham × rang juftligi uchun variant va shtrix-kod yaratiladi —
          keyin katakchaga dona yozasiz.
        </small>
      </div>
    </template>

    <div class="quick-actions">
      <button class="button button-outline" type="button" @click="emit('close')">
        Bekor qilish
      </button>

      <button
        class="button button-gradient"
        type="button"
        :disabled="saving || !ready"
        @click="onSave"
      >
        {{ saving ? 'Saqlanmoqda…' : 'Saqlash va qabul qilish' }}
      </button>
    </div>
  </div>
</template>

<style scoped>
.quick-form {
  margin: 10px 0;
  padding: 14px;
  border: 1px solid var(--border-strong);
  border-radius: var(--radius-card);
  background: var(--surface);
}

.quick-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 10px;
}

.barcode-note {
  margin-bottom: 10px;
}

.quick-row {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
  gap: 10px;
  margin-bottom: 10px;
}

.quick-row .field.wide {
  grid-column: span 2;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 4px;
  margin-bottom: 10px;
}

.field > span,
.field-label {
  color: var(--text-secondary);
  font-size: 12px;
}

.chips {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  min-height: 30px;
  padding: 0 12px;
  border: 1px solid var(--border-strong);
  border-radius: 999px;
  background: var(--surface);
  color: var(--text-secondary);
  font-size: 13px;
  cursor: pointer;
}

.chip.active {
  border-color: var(--accent);
  background: var(--accent);
  color: var(--accent-text);
}

.chip-dot {
  width: 12px;
  height: 12px;
  border: 1px solid var(--border-strong);
  border-radius: 50%;
}

.quick-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 4px;
}
</style>
