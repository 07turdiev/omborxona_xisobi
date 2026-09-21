<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'

import { catalogApi } from '@/api/catalog'
import { errorMessage } from '@/api/client'
import { useAuthStore } from '@/stores/auth'
import { formatMoney, normalizeMoneyInput, suggestPrice } from '@/utils/money'
import type { Category, Color, Product, Size } from '@/types'

/**
 * Kirim ekranidagi "Yangi mahsulot" oynasi.
 *
 * Tovar do'konga birinchi marta kelganda uni shu yerda yaratish kerak:
 * ilgari administrator Mahsulotlar sahifasiga o'tib, modelni yaratib,
 * keyin kirimga qaytardi.
 *
 * Chap tomonda rasmlar, o'ng tomonda ma'lumot. Rasm **majburiy emas**:
 * qutini ochib, tovarni tezda kiritish kerak bo'ladi, suratni keyin
 * mahsulot sahifasida qo'shish mumkin.
 *
 * `barcode` berilgan bo'lsa (noma'lum kod skanerlangan), mahsulot bitta
 * variantli bo'ladi va o'sha kod shu variantga yoziladi.
 */

const props = defineProps<{ barcode?: string }>()

const emit = defineEmits<{
  created: [product: Product, prices: { cost: string; markup: string }]
  close: []
}>()

const auth = useAuthStore()

const categories = ref<Category[]>([])
const sizes = ref<Size[]>([])
const colors = ref<Color[]>([])

const saving = ref(false)
const uploading = ref(false)
const error = ref('')

/** Ro'yxatlar kelmaguncha saqlash yopiq: kategoriyasiz mahsulot bo'lmaydi */
const ready = ref(false)

const nameInput = ref<HTMLInputElement | null>(null)
const picker = ref<HTMLInputElement | null>(null)
const camera = ref<HTMLInputElement | null>(null)

/** Tanlangan rasmlar — mahsulot yaratilgandan keyin yuklanadi */
const photos = ref<{ file: File; url: string }[]>([])
const dragging = ref(false)

const MAX_PHOTOS = 5

const form = ref({
  category: 0,
  name: '',
  brand: '',
  cost: '',
  markup: '',
  sale_price: '',
  size_ids: [] as number[],
  color_ids: [] as number[],
})

const step = computed(() => auth.shop?.price_rounding_step ?? 1000)

// Tannarx va ustama sotuv narxini taklif qiladi — kirimdagi katakcha
// bilan bir xil qoida
watch(
  () => [form.value.cost, form.value.markup],
  () => {
    if (!form.value.cost.trim() || !form.value.markup.trim()) return

    form.value.sale_price = formatMoney(
      suggestPrice(form.value.cost, form.value.markup, step.value),
    )
  },
)

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

onBeforeUnmount(() => {
  for (const photo of photos.value) URL.revokeObjectURL(photo.url)
})

function toggle(list: number[], id: number) {
  const index = list.indexOf(id)

  if (index === -1) list.push(id)
  else list.splice(index, 1)
}

function addPhotos(list: FileList | null) {
  for (const file of Array.from(list ?? [])) {
    if (photos.value.length >= MAX_PHOTOS) break
    if (!file.type.startsWith('image/')) continue

    photos.value.push({ file, url: URL.createObjectURL(file) })
  }
}

function onPick(event: Event) {
  const input = event.target as HTMLInputElement

  addPhotos(input.files)
  input.value = ''
}

function onDrop(event: DragEvent) {
  dragging.value = false
  addPhotos(event.dataTransfer?.files ?? null)
}

function removePhoto(index: number) {
  const [photo] = photos.value.splice(index, 1)

  if (photo) URL.revokeObjectURL(photo.url)
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

    // Rasmlar mahsulot yaratilgandan keyin yuklanadi. Bittasi
    // yuklanmasa ham mahsulot qoladi — suratni keyin qo'shish mumkin.
    if (photos.value.length) {
      uploading.value = true

      let failed = 0

      for (const photo of photos.value) {
        try {
          await catalogApi.uploadImage(product.id, photo.file, null)
        } catch {
          failed += 1
        }
      }

      uploading.value = false

      if (failed) error.value = `${failed} ta rasm yuklanmadi — keyin qo‘shsangiz bo‘ladi.`
    }

    emit('created', product, { cost: form.value.cost, markup: form.value.markup })
  } catch (err) {
    error.value = errorMessage(err, 'Mahsulotni saqlab bo‘lmadi.')
  } finally {
    saving.value = false
    uploading.value = false
  }
}
</script>

<template>
  <div class="overlay" @click.self="emit('close')">
    <div
      class="dialog"
      role="dialog"
      aria-modal="true"
      aria-label="Yangi mahsulot"
      data-testid="quick-product"
    >
      <header class="dialog-head">
        <h2>Yangi mahsulot</h2>

        <button class="icon-button" type="button" aria-label="Yopish" @click="emit('close')">
          <svg><use href="#i-close" /></svg>
        </button>
      </header>

      <div class="dialog-body">
        <!-- Rasmlar: majburiy emas -->
        <aside class="photo-panel">
          <span class="eyebrow">MAHSULOT RASMLARI</span>

          <div
            class="drop-zone"
            :class="{ dragging }"
            @dragover.prevent="dragging = true"
            @dragleave="dragging = false"
            @drop.prevent="onDrop"
          >
            <div v-if="!photos.length" class="drop-empty">
              <svg aria-hidden="true"><use href="#i-image" /></svg>
              <strong>Asosiy rasm</strong>
              <span>Faylni shu yerga tashlang yoki tanlang</span>
            </div>

            <ul v-else class="photo-grid">
              <li v-for="(photo, index) in photos" :key="photo.url">
                <img :src="photo.url" alt="" />

                <button
                  type="button"
                  class="photo-remove"
                  :aria-label="`${index + 1}-rasmni olib tashlash`"
                  @click="removePhoto(index)"
                >
                  ×
                </button>

                <small v-if="index === 0">Asosiy</small>
              </li>
            </ul>
          </div>

          <div class="photo-buttons">
            <button
              class="button button-outline"
              type="button"
              :disabled="photos.length >= MAX_PHOTOS"
              @click="picker?.click()"
            >
              <svg><use href="#i-image" /></svg>
              <span>Rasm tanlash</span>
            </button>

            <button
              class="button button-outline"
              type="button"
              :disabled="photos.length >= MAX_PHOTOS"
              @click="camera?.click()"
            >
              <svg><use href="#i-camera" /></svg>
              <span>Kamera</span>
            </button>
          </div>

          <input
            ref="picker"
            type="file"
            accept="image/*"
            multiple
            hidden
            data-testid="file-input"
            @change="onPick"
          />

          <input
            ref="camera"
            type="file"
            accept="image/*"
            capture="environment"
            hidden
            data-testid="camera-input"
            @change="onPick"
          />

          <small class="field-hint">
            Rasmsiz ham saqlanadi — suratni keyin mahsulot sahifasida qo‘shasiz.
            Ko‘pi bilan {{ MAX_PHOTOS }} ta, birinchisi asosiy bo‘ladi.
          </small>
        </aside>

        <!-- Ma'lumot -->
        <section class="detail-panel">
          <span class="eyebrow">MAHSULOT MA’LUMOTLARI</span>

          <p v-if="error" class="load-error">{{ error }}</p>

          <p v-if="barcode" class="field-hint barcode-note">
            Skanerlangan kod <strong>{{ barcode }}</strong> shu mahsulotning yagona
            variantiga yoziladi. O‘lcham va ranglarni keyin qo‘shasiz.
          </p>

          <div class="field-grid">
            <label class="field wide">
              <span>Nomi *</span>
              <input ref="nameInput" v-model="form.name" type="text" aria-label="Mahsulot nomi" />
            </label>

            <label class="field">
              <span>Brend</span>
              <input
                v-model="form.brand"
                type="text"
                aria-label="Brend"
                placeholder="Majburiy emas"
              />
            </label>

            <label class="field">
              <span>Kategoriya</span>
              <select v-model.number="form.category" aria-label="Kategoriya">
                <option v-for="item in categories" :key="item.id" :value="item.id">
                  {{ item.name }}
                </option>
              </select>
            </label>

            <label class="field">
              <span>Tannarx</span>
              <input
                v-model="form.cost"
                type="text"
                inputmode="decimal"
                aria-label="Tannarx"
                placeholder="0"
              />
            </label>

            <label class="field narrow">
              <span>Ustama %</span>
              <input v-model="form.markup" type="text" inputmode="decimal" aria-label="Ustama foizi" />
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
            <p class="field-hint variants-hint">
              O‘lcham va rang — model <strong>qaysi ko‘rinishda kelgani</strong>.
              Faqat kelganlarini belgilang. Keyin jadvalga sonini yozasiz.
              Bittadan belgilansa, jadval bitta katakdan iborat bo‘ladi.
            </p>

            <div class="field">
              <span class="field-label">Qaysi o‘lchamlar keldi?</span>

              <div class="chips" role="group" aria-label="O‘lchamlar">
                <button
                  v-for="item in sizes"
                  :key="item.id"
                  class="size-chip"
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
              <span class="field-label">Qaysi ranglar keldi?</span>

              <div class="swatches" role="group" aria-label="Ranglar">
                <button
                  v-for="item in colors"
                  :key="item.id"
                  class="swatch"
                  :class="{ active: form.color_ids.includes(item.id) }"
                  type="button"
                  :aria-pressed="form.color_ids.includes(item.id)"
                  @click="toggle(form.color_ids, item.id)"
                >
                  <span class="swatch-dot" :style="{ background: item.hex_code }" />
                  <small>{{ item.name }}</small>
                </button>
              </div>

              <small class="field-hint">
                Har o‘lcham × rang juftligi uchun alohida shtrix-kod chiqadi.
                Keyinroq yangi o‘lcham yoki rang kelsa, uni kirim jadvalining
                o‘zida qo‘shasiz — qolgan juftliklar yaratilmaydi.
              </small>
            </div>
          </template>
        </section>
      </div>

      <footer class="dialog-foot">
        <button class="button button-outline" type="button" @click="emit('close')">
          Bekor qilish
        </button>

        <button
          class="button button-gradient"
          type="button"
          :disabled="saving || uploading || !ready"
          @click="onSave"
        >
          {{ uploading ? 'Rasm yuklanmoqda…' : saving ? 'Saqlanmoqda…' : 'Saqlash va qabul qilish' }}
        </button>
      </footer>
    </div>
  </div>
</template>

<style scoped>
.overlay {
  position: fixed;
  inset: 0;
  /* Yon paneldan ham baland (u 60): oyna keng, chetlari panel ostida
     qolib ketmasin */
  z-index: 70;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 16px;
  background: rgb(35 27 20 / 45%);
}

.dialog {
  display: flex;
  flex-direction: column;
  width: min(1040px, 96vw);
  max-height: 90vh;
  overflow: hidden;
  border-radius: var(--radius-card);
  background: var(--surface);
  box-shadow: var(--shadow-large);
}

.dialog-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 18px 24px;
  border-bottom: 1px solid var(--border);
  background: linear-gradient(120deg, #f7efe2, #fffdf9);
}

.dialog-head h2 {
  font-family: var(--font-display);
  font-size: 26px;
  font-weight: 500;
}

.dialog-body {
  display: grid;
  grid-template-columns: 320px minmax(0, 1fr);
  gap: 22px;
  padding: 20px 24px;
  overflow-y: auto;
}

.eyebrow {
  display: block;
  margin-bottom: 12px;
  color: var(--accent);
  font-size: 10px;
  letter-spacing: 2px;
}

/* --- Rasmlar --- */

.photo-panel {
  align-self: start;
  padding: 16px;
  border-radius: var(--radius-card);
  background: var(--surface-soft);
}

.drop-zone {
  display: grid;
  place-items: center;
  min-height: 220px;
  padding: 12px;
  border: 1px dashed var(--border-strong);
  border-radius: var(--radius);
  background: var(--surface);
}

.drop-zone.dragging {
  border-color: var(--accent);
  background: var(--accent-soft);
}

.drop-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  color: var(--text-muted);
  text-align: center;
}

.drop-empty svg {
  width: 30px;
  height: 30px;
  fill: none;
  stroke: var(--gray-4);
  stroke-width: 1.2;
}

.drop-empty strong {
  color: var(--text-secondary);
  font-size: 13px;
}

.drop-empty span {
  font-size: 12px;
}

.photo-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
  width: 100%;
  list-style: none;
}

.photo-grid li {
  position: relative;
}

.photo-grid img {
  display: block;
  width: 100%;
  aspect-ratio: 4 / 5;
  object-fit: cover;
  border-radius: var(--radius-small);
}

.photo-grid small {
  display: block;
  margin-top: 2px;
  color: var(--text-muted);
  font-size: 10px;
  text-align: center;
}

.photo-remove {
  position: absolute;
  top: -6px;
  right: -6px;
  width: 22px;
  height: 22px;
  border: 1px solid var(--border);
  border-radius: 50%;
  background: var(--surface);
  color: var(--red);
  font-size: 14px;
  line-height: 1;
  cursor: pointer;
}

.photo-buttons {
  display: flex;
  gap: 8px;
  margin-top: 10px;
}

.photo-buttons .button {
  flex: 1;
}

/* --- Ma'lumot --- */

.field-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
  margin-bottom: 14px;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 4px;
  margin-bottom: 12px;
}

.field-grid .field {
  margin-bottom: 0;
}

.field-grid .field.wide {
  grid-column: span 2;
}

.field > span,
.field-label {
  color: var(--text-secondary);
  font-size: 12px;
}

.barcode-note {
  margin-bottom: 12px;
}

.variants-hint {
  margin-bottom: 10px;
  line-height: 1.6;
}

.chips,
.swatches {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.size-chip {
  min-width: 48px;
  min-height: 38px;
  padding: 0 14px;
  border: 1px solid var(--border-strong);
  border-radius: var(--radius);
  background: var(--surface);
  color: var(--text-secondary);
  font-size: 14px;
  cursor: pointer;
}

.size-chip.active {
  border-color: var(--gray-9);
  background: var(--gray-9);
  color: #fff;
}

.swatch {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 5px;
  width: 64px;
  padding: 4px 2px;
  border: 0;
  background: none;
  cursor: pointer;
}

.swatch-dot {
  width: 30px;
  height: 30px;
  border: 1px solid var(--border-strong);
  border-radius: 50%;
  box-shadow: 0 0 0 2px transparent;
  transition: box-shadow 0.12s;
}

.swatch.active .swatch-dot {
  box-shadow:
    0 0 0 2px var(--surface),
    0 0 0 4px var(--accent);
}

.swatch small {
  color: var(--text-muted);
  font-size: 11px;
  text-align: center;
}

.swatch.active small {
  color: var(--text);
  font-weight: 600;
}

/* --- Pastki qator --- */

.dialog-foot {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  padding: 14px 24px;
  border-top: 1px solid var(--border);
  background: var(--surface-soft);
}

@media (max-width: 900px) {
  .dialog-body {
    grid-template-columns: minmax(0, 1fr);
  }

  .field-grid {
    grid-template-columns: minmax(0, 1fr);
  }

  .field-grid .field.wide {
    grid-column: auto;
  }
}
</style>
