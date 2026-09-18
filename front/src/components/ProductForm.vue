<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'

import { catalogApi, type ProductInput } from '@/api/catalog'
import { errorMessage } from '@/api/client'
import { normalizeMoneyInput } from '@/utils/money'
import type { Category, Color, Product, Size } from '@/types'

/**
 * Mahsulotni yaratish va tahrirlash oynasi.
 *
 * Rasmlar bu yerda emas — mahsulot sahifasida: rasm yuklash formani
 * to'smasin va rasm faqat saqlangan mahsulotga qo'shiladi.
 */

const props = defineProps<{ product: Product | null }>()

const emit = defineEmits<{ saved: [product: Product]; close: [] }>()

const categories = ref<Category[]>([])
const sizes = ref<Size[]>([])
const colors = ref<Color[]>([])

const saving = ref(false)
const error = ref('')

const form = ref({
  category: 0,
  name: '',
  slug: '',
  brand: '',
  description: '',
  material: '',
  care: '',
  sale_price: '',
  mxik_code: '',
  package_code: '',
  size_ids: [] as number[],
  color_ids: [] as number[],
})

const isNew = computed(() => props.product === null)

onMounted(async () => {
  try {
    ;[categories.value, sizes.value, colors.value] = await Promise.all([
      catalogApi.categories(),
      catalogApi.sizes(),
      catalogApi.colors(),
    ])
  } catch (err) {
    error.value = errorMessage(err, 'Ro‘yxatlarni yuklab bo‘lmadi.')
  }

  const product = props.product

  if (!product) {
    form.value.category = categories.value[0]?.id ?? 0
    return
  }

  // Mavjud variantlardan o'lcham va ranglar tiklanadi
  form.value = {
    category: product.category,
    name: product.name,
    slug: product.slug,
    brand: product.brand,
    description: product.description,
    material: product.material,
    care: product.care,
    sale_price: product.sale_price,
    mxik_code: product.mxik_code,
    package_code: product.package_code,
    size_ids: [
      ...new Set(product.variants.map((item) => item.size).filter((id): id is number => id !== null)),
    ],
    color_ids: [
      ...new Set(product.variants.map((item) => item.color).filter((id): id is number => id !== null)),
    ],
  }
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

  const payload: ProductInput = {
    category: form.value.category,
    name: form.value.name,
    brand: form.value.brand,
    description: form.value.description,
    material: form.value.material.trim(),
    care: form.value.care.trim(),
    sale_price: normalizeMoneyInput(form.value.sale_price || '0'),
    mxik_code: form.value.mxik_code.trim(),
    package_code: form.value.package_code.trim(),
    size_ids: form.value.size_ids,
    color_ids: form.value.color_ids,
  }

  // Bo'sh bo'lsa yuborilmaydi: yangi mahsulotda nomdan yasaladi,
  // mavjudida esa o'zgarmaydi (tashqi havolalar uzilmasin)
  if (form.value.slug.trim()) payload.slug = form.value.slug.trim()

  try {
    const saved = props.product
      ? await catalogApi.updateProduct(props.product.id, payload)
      : await catalogApi.createProduct(payload)

    emit('saved', saved)
  } catch (err) {
    error.value = errorMessage(err, 'Saqlab bo‘lmadi.')
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <div class="overlay" @click.self="emit('close')" @keydown.esc="emit('close')">
    <div class="overlay-card" role="dialog" aria-modal="true" :aria-label="isNew ? 'Yangi mahsulot' : 'Mahsulotni tahrirlash'">
      <h3>{{ isNew ? 'Yangi mahsulot' : 'Mahsulotni tahrirlash' }}</h3>

      <p v-if="error" class="load-error">{{ error }}</p>

      <div class="field">
        <label>Kategoriya</label>
        <select v-model.number="form.category">
          <option v-for="item in categories" :key="item.id" :value="item.id">{{ item.name }}</option>
        </select>
      </div>

      <div class="field">
        <label>Nomi</label>
        <input v-model="form.name" type="text" />
      </div>

      <div class="field">
        <label>Brend</label>
        <input v-model="form.brand" type="text" />
      </div>

      <div class="field">
        <label>Sotuv narxi</label>
        <input v-model="form.sale_price" type="text" inputmode="decimal" />
      </div>

      <div class="field">
        <label>O‘lchamlar</label>

        <div class="chips">
          <button
            v-for="item in sizes"
            :key="item.id"
            class="chip"
            :class="{ active: form.size_ids.includes(item.id) }"
            type="button"
            @click="toggle(form.size_ids, item.id)"
          >
            {{ item.name }}
          </button>
        </div>
      </div>

      <div class="field">
        <label>Ranglar</label>

        <div class="chips">
          <button
            v-for="item in colors"
            :key="item.id"
            class="chip"
            :class="{ active: form.color_ids.includes(item.id) }"
            type="button"
            @click="toggle(form.color_ids, item.id)"
          >
            <span class="chip-dot" :style="{ background: item.hex_code }" />
            {{ item.name }}
          </button>
        </div>

        <small class="field-hint">
          Har o‘lcham va rang juftligi uchun alohida variant va shtrix-kod yaratiladi.
          Mavjud variantlar o‘chirilmaydi.
        </small>
      </div>

      <div class="field">
        <label>Tarkibi</label>
        <input v-model="form.material" type="text" placeholder="60% paxta, 40% polyester" />
      </div>

      <div class="field">
        <label>Parvarish</label>
        <input v-model="form.care" type="text" placeholder="30° da yuvish, past haroratda dazmollash" />
      </div>

      <div class="field">
        <label>Tavsif</label>
        <textarea v-model="form.description" rows="3" />
      </div>

      <div class="field">
        <label>MXIK kodi</label>
        <input
          v-model="form.mxik_code"
          type="text"
          inputmode="numeric"
          maxlength="17"
          placeholder="Bo‘sh qoldirilsa kategoriyaniki"
        />
        <small class="field-hint">
          Faqat shu mahsulotning kodi kategoriyanikidan farq qilsa to‘ldiring.
        </small>
      </div>

      <div class="field">
        <label>Manzil qismi (slug)</label>
        <input v-model="form.slug" type="text" placeholder="Nomdan avtomatik yasaladi" />
        <small class="field-hint">
          Kelajakdagi onlayn do‘kon manzili. Do‘kon ochilgach o‘zgartirmang —
          tashqi havolalar uziladi.
        </small>
      </div>

      <p v-if="isNew" class="field-hint">
        Rasmlarni saqlagandan keyin mahsulot sahifasida qo‘shasiz.
      </p>

      <div class="form-actions">
        <button class="button button-outline" type="button" @click="emit('close')">
          Bekor qilish
        </button>

        <button class="button button-gradient" type="button" :disabled="saving" @click="onSave">
          {{ saving ? 'Saqlanmoqda…' : 'Saqlash' }}
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.overlay {
  position: fixed;
  inset: 0;
  z-index: 50;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 16px;
  background: rgb(15 23 42 / 45%);
}

.overlay-card {
  width: 100%;
  max-width: 520px;
  max-height: 90vh;
  overflow-y: auto;
  padding: 20px;
  border-radius: var(--radius);
  background: var(--surface);
}

.overlay-card > .field {
  margin-bottom: 12px;
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
  padding: 5px 10px;
  border: 1px solid var(--border);
  border-radius: 999px;
  background: var(--surface);
  color: var(--text);
  font-size: 12px;
  cursor: pointer;
}

.chip.active {
  border-color: var(--accent);
  background: var(--accent-soft);
  font-weight: 600;
}

.chip-dot {
  width: 12px;
  height: 12px;
  border: 1px solid rgb(0 0 0 / 18%);
  border-radius: 50%;
}

.form-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 16px;
}
</style>
