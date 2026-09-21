<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'

import { catalogApi } from '@/api/catalog'
import { errorMessage } from '@/api/client'
import type { Color, ProductImage } from '@/types'

/**
 * Mahsulot rasmlarini boshqarish (administrator).
 *
 * Har amal darhol serverga ketadi. Yuklash navbat bilan, bittadan boradi
 * (telefon internetida bir vaqtda o'nta fayl hammasini sekinlashtiradi) va
 * sahifani to'sib qo'ymaydi: yuklanayotganda boshqa amallar ishlayveradi.
 */

const props = defineProps<{ productId: number; colors: Color[] }>()

/** Har o'zgarishdan keyin — sahifadagi galereya yangilansin */
const emit = defineEmits<{ changed: [] }>()

const MAX_IMAGES = 10
const MAX_BYTES = 15 * 1024 * 1024

interface Upload {
  key: number
  file: File
  preview: string
  color: number | null
  progress: number
  status: 'waiting' | 'uploading' | 'failed'
  error: string
}

const images = ref<ProductImage[]>([])
const uploads = ref<Upload[]>([])

/** Yangi rasmlar qaysi rangga biriktiriladi (`null` — umumiy) */
const uploadColor = ref<number | null>(null)

const error = ref('')
const busy = ref(false)
const dragging = ref(false)

const picker = ref<HTMLInputElement | null>(null)
const camera = ref<HTMLInputElement | null>(null)

let nextKey = 1
let running = false

const slotsLeft = computed(
  () =>
    MAX_IMAGES -
    images.value.length -
    uploads.value.filter((upload) => upload.status !== 'failed').length,
)

async function load() {
  try {
    images.value = await catalogApi.productImages(props.productId)
  } catch (err) {
    error.value = errorMessage(err, 'Rasmlarni yuklab bo‘lmadi.')
  }
}

watch(() => props.productId, load, { immediate: true })

/** Fayllarni navbatga qo'yadi. Hajm va tur serverda ham tekshiriladi —
 *  bu yerda faqat keraksiz trafik ketmasligi uchun. */
function enqueue(files: FileList | null | undefined) {
  error.value = ''

  for (const file of Array.from(files ?? [])) {
    if (slotsLeft.value <= 0) {
      error.value = `Bitta mahsulotga ${MAX_IMAGES} tadan ortiq rasm qo‘shib bo‘lmaydi.`
      break
    }

    // `reactive`: foiz yangilanganda ekran ham yangilansin
    const upload = reactive<Upload>({
      key: nextKey++,
      file,
      preview: '',
      color: uploadColor.value,
      progress: 0,
      status: 'waiting',
      error: '',
    })

    if (!file.type.startsWith('image/')) {
      upload.status = 'failed'
      upload.error = `«${file.name}» rasm emas.`
    } else if (file.size > MAX_BYTES) {
      upload.status = 'failed'
      upload.error = `«${file.name}» 15 MB dan katta.`
    } else {
      upload.preview = URL.createObjectURL(file)
    }

    uploads.value.push(upload)
  }

  void pump()
}

async function pump() {
  if (running) return

  running = true

  try {
    for (;;) {
      const upload = uploads.value.find((item) => item.status === 'waiting')

      if (!upload) break

      upload.status = 'uploading'

      try {
        const image = await catalogApi.uploadImage(
          props.productId,
          upload.file,
          upload.color,
          (share) => {
            upload.progress = share
          },
        )

        images.value.push(image)
        dismiss(upload)
        emit('changed')
      } catch (err) {
        upload.status = 'failed'
        upload.error = errorMessage(err, `«${upload.file.name}» yuklanmadi.`)
      }
    }
  } finally {
    running = false
  }
}

function dismiss(upload: Upload) {
  if (upload.preview) URL.revokeObjectURL(upload.preview)

  uploads.value = uploads.value.filter((item) => item !== upload)
}

function onPick(event: Event) {
  const input = event.target as HTMLInputElement

  enqueue(input.files)

  // Xuddi shu faylni qayta tanlash ham ishlasin
  input.value = ''
}

function onDrop(event: DragEvent) {
  dragging.value = false
  enqueue(event.dataTransfer?.files)
}

async function run(action: () => Promise<void>, fallback: string) {
  if (busy.value) return

  busy.value = true
  error.value = ''

  try {
    await action()
    emit('changed')
  } catch (err) {
    error.value = errorMessage(err, fallback)
  } finally {
    busy.value = false
  }
}

function setColor(image: ProductImage, value: string) {
  void run(async () => {
    const updated = await catalogApi.updateImage(image.id, {
      color: value === '' ? null : Number(value),
    })

    images.value = images.value.map((item) => (item.id === updated.id ? updated : item))
  }, 'Rangni saqlab bo‘lmadi.')
}

function makePrimary(image: ProductImage) {
  void run(async () => {
    await catalogApi.updateImage(image.id, { is_primary: true })

    // Ro'yxat qayta so'ralmaydi: shu payt yuklanib tugagan rasm
    // javobda bo'lmay, ekrandan yo'qolib qolishi mumkin edi
    images.value = images.value.map((item) => ({ ...item, is_primary: item.id === image.id }))
  }, 'Asosiy rasmni o‘zgartirib bo‘lmadi.')
}

function move(image: ProductImage, step: number) {
  void run(async () => {
    const ids = images.value.map((item) => item.id)
    const from = ids.indexOf(image.id)
    const to = from + step

    ;[ids[from], ids[to]] = [ids[to]!, ids[from]!]

    images.value = await catalogApi.reorderImages(props.productId, ids)
  }, 'Tartibni saqlab bo‘lmadi.')
}

function remove(image: ProductImage) {
  if (!window.confirm('Rasm o‘chirilsinmi?')) return

  void run(async () => {
    await catalogApi.removeImage(image.id)

    const rest = images.value.filter((item) => item.id !== image.id)

    // Server ham shunday qiladi: asosiy o'chsa keyingisi asosiy bo'ladi
    if (image.is_primary && rest[0]) rest[0] = { ...rest[0], is_primary: true }

    images.value = rest
  }, 'O‘chirib bo‘lmadi.')
}

function colorLabel(id: number | null) {
  return props.colors.find((color) => color.id === id)?.name ?? 'Umumiy'
}
</script>

<template>
  <div class="product-images">
    <div class="images-head">
      <span class="images-title">Rasmlar <small>{{ images.length }} / {{ MAX_IMAGES }}</small></span>

      <select v-if="colors.length" v-model="uploadColor" aria-label="Yangi rasmlar rangi">
        <option :value="null">Yangi rasm: umumiy</option>
        <option v-for="color in colors" :key="color.id" :value="color.id">
          Yangi rasm: {{ color.name }}
        </option>
      </select>
    </div>

    <div
      class="drop-zone"
      :class="{ dragging }"
      @dragover.prevent="dragging = true"
      @dragleave.prevent="dragging = false"
      @drop.prevent="onDrop"
    >
      <!-- Bitta bosish: telefonda kamera darhol ochiladi -->
      <button
        class="button button-gradient"
        type="button"
        :disabled="slotsLeft <= 0"
        @click="camera?.click()"
      >
        <svg><use href="#i-camera" /></svg>
        <span>Suratga olish</span>
      </button>

      <button
        class="button button-outline"
        type="button"
        :disabled="slotsLeft <= 0"
        @click="picker?.click()"
      >
        <svg><use href="#i-plus" /></svg>
        <span>Fayldan tanlash</span>
      </button>

      <span class="drop-hint">yoki rasmni shu yerga tashlang</span>

      <input
        ref="camera"
        type="file"
        accept="image/*"
        capture="environment"
        hidden
        data-testid="camera-input"
        @change="onPick"
      />
      <input
        ref="picker"
        type="file"
        accept="image/*"
        multiple
        hidden
        data-testid="file-input"
        @change="onPick"
      />
    </div>

    <p v-if="error" class="images-error" role="alert">{{ error }}</p>

    <ul v-if="images.length || uploads.length" class="image-grid">
      <li
        v-for="(image, position) in images"
        :key="image.id"
        class="image-item"
        :class="{ primary: image.is_primary }"
      >
        <div class="image-frame">
          <img :src="image.thumb" alt="" loading="lazy" width="200" height="250" />
          <span v-if="image.is_primary" class="primary-badge">Asosiy</span>
        </div>

        <select
          :value="image.color ?? ''"
          :disabled="busy"
          :aria-label="`Rasm rangi: ${colorLabel(image.color)}`"
          @change="setColor(image, ($event.target as HTMLSelectElement).value)"
        >
          <option value="">Umumiy</option>
          <option v-for="color in colors" :key="color.id" :value="color.id">
            {{ color.name }}
          </option>
        </select>

        <div class="image-actions">
          <button
            type="button"
            aria-label="Chapga surish"
            :disabled="busy || position === 0"
            @click="move(image, -1)"
          >
            ‹
          </button>

          <button
            type="button"
            title="Asosiy rasm qilish"
            aria-label="Asosiy rasm qilish"
            :disabled="busy || image.is_primary"
            @click="makePrimary(image)"
          >
            ★
          </button>

          <button
            type="button"
            aria-label="O‘ngga surish"
            :disabled="busy || position === images.length - 1"
            @click="move(image, 1)"
          >
            ›
          </button>

          <button
            class="delete"
            type="button"
            aria-label="O‘chirish"
            :disabled="busy"
            @click="remove(image)"
          >
            <svg><use href="#i-trash" /></svg>
          </button>
        </div>
      </li>

      <li
        v-for="upload in uploads"
        :key="`upload-${upload.key}`"
        class="image-item uploading"
        :class="{ failed: upload.status === 'failed' }"
      >
        <div class="image-frame">
          <img v-if="upload.preview" :src="upload.preview" alt="" />

          <div class="upload-state">
            <template v-if="upload.status === 'failed'">
              <span class="upload-error">{{ upload.error }}</span>
              <button class="link-button" type="button" @click="dismiss(upload)">Yopish</button>
            </template>

            <template v-else>
              <progress :value="upload.progress" max="1" />
              <span>
                {{
                  upload.status === 'waiting'
                    ? 'Navbatda'
                    : upload.progress >= 1
                      ? 'Ishlanmoqda…'
                      : `${Math.round(upload.progress * 100)}%`
                }}
              </span>
            </template>
          </div>
        </div>

        <span class="upload-color">{{ colorLabel(upload.color) }}</span>
      </li>
    </ul>

    <p class="field-hint">
      Rasmni rangga biriktirsangiz, katalogda o‘sha rang tanlanganda chiqadi.
    </p>
  </div>
</template>

<style scoped>
.product-images {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.images-head {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.images-title {
  color: var(--text-secondary);
  font-size: 13px;
  font-weight: 600;
}

.images-title small {
  margin-left: 4px;
  color: var(--text-muted);
  font-weight: 400;
}

.images-head select {
  height: 34px;
  padding: 0 8px;
  border: 1px solid var(--border-strong);
  border-radius: var(--radius);
  background: var(--surface);
  font-size: 14px;
}

.drop-zone {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  padding: 12px;
  border: 1px dashed var(--border-strong);
  border-radius: var(--radius);
  background: var(--surface-soft);
}

.drop-zone.dragging {
  border-color: var(--accent);
  background: var(--accent-soft);
}

.drop-hint {
  color: var(--text-muted);
  font-size: 13px;
}

.images-error {
  margin: 0;
  color: var(--red);
  font-size: 14px;
}

.image-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(110px, 1fr));
  gap: 8px;
  margin: 0;
  padding: 0;
  list-style: none;
}

.image-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
}

.image-frame {
  position: relative;
  overflow: hidden;
  aspect-ratio: 4 / 5;
  border: 2px solid var(--border);
  border-radius: var(--radius);
  background: var(--surface-soft);
}

.image-item.primary .image-frame {
  border-color: var(--accent);
}

.image-frame img {
  display: block;
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.primary-badge {
  position: absolute;
  top: 4px;
  left: 4px;
  padding: 1px 6px;
  border-radius: 999px;
  background: var(--accent);
  color: #fff;
  font-size: 12px;
  font-weight: 600;
}

.image-item select {
  width: 100%;
  height: 30px;
  border: 1px solid var(--border-strong);
  border-radius: var(--radius);
  background: var(--surface);
  font-size: 13px;
}

.image-actions {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 2px;
}

.image-actions button {
  height: 30px;
  padding: 0;
  border: 1px solid var(--border);
  border-radius: var(--radius-small);
  background: var(--surface);
  color: var(--text-secondary);
  font-size: 17px;
  line-height: 1;
  cursor: pointer;
}

.image-actions button:disabled {
  opacity: 0.35;
  cursor: default;
}

.image-actions .delete:hover:not(:disabled) {
  border-color: var(--red);
  color: var(--red);
}

.image-actions svg {
  width: 14px;
  height: 14px;
  fill: none;
  stroke: currentColor;
  stroke-width: 1.8;
}

.upload-state {
  position: absolute;
  inset: auto 0 0;
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 6px;
  background: rgb(255 255 255 / 92%);
  font-size: 13px;
}

.upload-state progress {
  width: 100%;
  height: 6px;
  accent-color: var(--accent);
}

.image-item.failed .image-frame {
  border-color: var(--red);
}

.upload-error {
  color: var(--red);
}

.upload-color {
  color: var(--text-muted);
  font-size: 13px;
}

.link-button {
  align-self: flex-start;
  padding: 0;
  border: 0;
  background: none;
  color: var(--accent);
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
}

/* Barmoq uchun kattaroq nishonlar */
@media (pointer: coarse) {
  .drop-zone .button {
    min-height: 48px;
    flex: 1 1 140px;
  }

  .drop-hint {
    display: none;
  }

  .image-item select,
  .image-actions button {
    height: 40px;
  }
}
</style>
