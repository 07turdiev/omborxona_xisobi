<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'

import AmountField from '@/components/AmountField.vue'
import { catalogApi, type ProductInput } from '@/api/catalog'
import { errorMessage } from '@/api/client'
import { normalizeMoneyInput } from '@/utils/money'
import type { Category, Color, Product, Size } from '@/types'

/**
 * Mahsulotni yaratish va tahrirlash oynasi.
 *
 * Yangi mahsulotga bitta rasm majburiy — rasmsiz tovarni ro'yxatdan
 * tanib bo'lmaydi. Qolgan rasmlar mahsulot sahifasida qo'shiladi.
 */

const props = defineProps<{ product: Product | null }>()

const emit = defineEmits<{ saved: [product: Product]; close: [] }>()

const categories = ref<Category[]>([])
const sizes = ref<Size[]>([])
const colors = ref<Color[]>([])

const saving = ref(false)
const error = ref('')

const picker = ref<HTMLInputElement | null>(null)
const photo = ref<{ file: File; url: string } | null>(null)

const form = ref({
  category: 0,
  name: '',
  slug: '',
  brand: '',
  description: '',
  material: '',
  care: '',
  sale_price: '',
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
    size_ids: [
      ...new Set(product.variants.map((item) => item.size).filter((id): id is number => id !== null)),
    ],
    color_ids: [
      ...new Set(product.variants.map((item) => item.color).filter((id): id is number => id !== null)),
    ],
  }
})

function onPickPhoto(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]

  input.value = ''

  if (!file?.type.startsWith('image/')) return

  if (photo.value) URL.revokeObjectURL(photo.value.url)

  photo.value = { file, url: URL.createObjectURL(file) }
}

onBeforeUnmount(() => {
  if (photo.value) URL.revokeObjectURL(photo.value.url)
})

function toggle(list: number[], id: number) {
  const index = list.indexOf(id)

  if (index === -1) list.push(id)
  else list.splice(index, 1)
}

async function onSave() {
  if (!form.value.name.trim() || saving.value) return
  if (isNew.value && !photo.value) return

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

    // Rasm yuklashga mahsulot `id` si kerak, shuning uchun saqlagandan keyin
    if (photo.value) await catalogApi.uploadImage(saved.id, photo.value.file, null)

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

      <div v-if="isNew" class="field">
        <label>Rasm — majburiy</label>

        <div class="photo-field">
          <img v-if="photo" :src="photo.url" alt="" class="photo-preview" />

          <button class="button button-outline" type="button" @click="picker?.click()">
            <svg><use href="#i-image" /></svg>
            <span>{{ photo ? 'Boshqasini tanlash' : 'Rasm tanlash' }}</span>
          </button>
        </div>

        <input
          ref="picker"
          type="file"
          accept="image/*"
          hidden
          data-testid="product-photo"
          @change="onPickPhoto"
        />
      </div>

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
        <AmountField v-model="form.sale_price" />
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
        <label>Manzil qismi (slug)</label>
        <input v-model="form.slug" type="text" placeholder="Nomdan avtomatik yasaladi" />
        <small class="field-hint">Do‘kon ochilgach o‘zgartirmang.</small>
      </div>

      <div class="form-actions">
        <button class="button button-outline" type="button" @click="emit('close')">
          Bekor qilish
        </button>

        <button
          class="button button-gradient"
          type="button"
          :disabled="saving || (isNew && !photo)"
          @click="onSave"
        >
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
  background: rgb(35 27 20 / 45%);
}

.overlay-card {
  width: 100%;
  max-width: 520px;
  max-height: 90vh;
  overflow-y: auto;
  padding: 20px;
  border-radius: var(--radius-card);
  background: var(--surface);
}

.overlay-card > .field {
  margin-bottom: 12px;
}

.photo-field {
  display: flex;
  align-items: center;
  gap: 10px;
}

.photo-preview {
  width: 56px;
  height: 72px;
  border-radius: var(--radius);
  object-fit: cover;
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
  font-size: 13px;
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
