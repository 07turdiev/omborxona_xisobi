<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'

import AmountField from '@/components/AmountField.vue'
import { catalogApi } from '@/api/catalog'
import { errorMessage } from '@/api/client'
import { useAuthStore } from '@/stores/auth'
import { formatMoney, normalizeMoneyInput, suggestPrice } from '@/utils/money'
import type { Category, Color, Product, Size } from '@/types'

/**
 * Qabul qilishning 1-qadami: yangi tovar.
 *
 * Do'konga keladigan tovarda shtrix-kod bo'lmaydi — yorliqni do'konning
 * o'zi chiqaradi. Shuning uchun qabul qilish shu yerdan boshlanadi:
 * tovar tizimga kiritiladi, keyin har o'lcham × rang uchun shtrix-kod
 * avtomatik yaratiladi.
 *
 * Chap tomonda rasmlar, o'ng tomonda ma'lumot. Kamida bitta rasm
 * majburiy: rasmsiz tovarni na javonda, na ro'yxatda tanib bo'ladi.
 *
 * Har rangga o'z rasmini biriktirish mumkin. Qora ko'ylakni
 * qidirayotgan xodim oq ko'ylakning suratini ko'rmasin: kassa savati
 * va tanlagich variantning o'z rangidagi rasmni ko'rsatadi.
 *
 * Nom yozilganda shu nomli tovar bor-yo'qligi tekshiriladi: bir tovar
 * ikki marta yaratilsa, qoldiq ikkiga bo'linib ketardi.
 */

const props = defineProps<{ barcode?: string }>()

const emit = defineEmits<{
  created: [product: Product, prices: { cost: string; markup: string }]
  existing: [product: Product]
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

/** Tanlangan rasmlar — mahsulot yaratilgandan keyin yuklanadi */
const photos = ref<{ file: File; url: string }[]>([])

/** Rang bo'yicha rasm: `{ rang id: fayl }` */
const colorPhotos = ref<Record<number, { file: File; url: string }>>({})

const colorPicker = ref<HTMLInputElement | null>(null)
const pickingColor = ref<number | null>(null)
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

/** Shu nomli tovar allaqachon bor bo'lsa — takror yaratilmasin */
const similar = ref<Product | null>(null)

let nameTimer: ReturnType<typeof setTimeout> | undefined

watch(
  () => form.value.name,
  (name) => {
    clearTimeout(nameTimer)
    similar.value = null

    const text = name.trim()

    if (text.length < 3) return

    nameTimer = setTimeout(async () => {
      try {
        const page = await catalogApi.products({ search: text })

        similar.value =
          page.results.find(
            (product) => product.name.toLowerCase() === text.toLowerCase(),
          ) ??
          page.results[0] ??
          null
      } catch {
        // Tekshiruv — qulaylik; ishlamasa yaratishga xalaqit bermaydi
      }
    }, 400)
  },
)

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
  for (const photo of Object.values(colorPhotos.value)) URL.revokeObjectURL(photo.url)
})

/** Tanlangan ranglar — ular uchun rasm so'raladi. */
const chosenColors = computed(() =>
  colors.value.filter((item) => form.value.color_ids.includes(item.id)),
)

function toggle(list: number[], id: number) {
  const index = list.indexOf(id)

  if (index === -1) list.push(id)
  else list.splice(index, 1)
}

/** Rang bekor qilinsa, unga biriktirilgan rasm ham keraksiz bo'ladi. */
function toggleColor(id: number) {
  toggle(form.value.color_ids, id)

  if (!form.value.color_ids.includes(id)) removeColorPhoto(id)
}

function pickColorPhoto(id: number) {
  pickingColor.value = id
  colorPicker.value?.click()
}

function onColorPick(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  const id = pickingColor.value

  input.value = ''
  pickingColor.value = null

  if (!file?.type.startsWith('image/') || id === null) return

  removeColorPhoto(id)
  colorPhotos.value[id] = { file, url: URL.createObjectURL(file) }
}

function removeColorPhoto(id: number) {
  const photo = colorPhotos.value[id]

  if (!photo) return

  URL.revokeObjectURL(photo.url)
  delete colorPhotos.value[id]
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

    // Rasmlar mahsulot yaratilgandan keyin yuklanadi: yuklashga
    // mahsulot `id` si kerak. Bittasi yuklanmasa ham mahsulot qoladi —
    // suratni tovar sahifasidan qo'shish mumkin.
    const uploads: { file: File; color: number | null }[] = [
      ...photos.value.map((photo) => ({ file: photo.file, color: null })),
      ...Object.entries(colorPhotos.value).map(([id, photo]) => ({
        file: photo.file,
        color: Number(id),
      })),
    ]

    if (uploads.length) {
      uploading.value = true

      let failed = 0

      for (const upload of uploads) {
        try {
          await catalogApi.uploadImage(product.id, upload.file, upload.color)
        } catch {
          failed += 1
        }
      }

      uploading.value = false

      if (failed) error.value = `${failed} ta rasm yuklanmadi — tovar sahifasidan qo‘shing.`
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
  <div class="new-product" data-testid="quick-product">
    <!-- Shu nomli tovar bor: qoldiq ikkiga bo'linib ketmasin -->
    <p v-if="similar" class="notice same-product">
      <span>«{{ similar.name }}» do‘konda bor.</span>

      <button class="button button-outline" type="button" @click="emit('existing', similar)">
        Shu tovar yana keldi
      </button>
    </p>

    <div class="panel-body">
        <!-- Kamida bitta rasm majburiy -->
        <aside class="photo-panel">
          <span class="eyebrow">MAHSULOT RASMI</span>

          <div
            class="drop-zone"
            :class="{ dragging }"
            @dragover.prevent="dragging = true"
            @dragleave="dragging = false"
            @drop.prevent="onDrop"
          >
            <div v-if="!photos.length" class="drop-empty">
              <svg aria-hidden="true"><use href="#i-image" /></svg>
              <strong>Asosiy rasm — majburiy</strong>
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

        </aside>

        <!-- Ma'lumot -->
        <section class="detail-panel">
          <span class="eyebrow">MAHSULOT MA’LUMOTLARI</span>

          <p v-if="error" class="load-error">{{ error }}</p>

          <p v-if="barcode" class="field-hint barcode-note">
            Shtrix-kod: <strong>{{ barcode }}</strong>
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
              <AmountField v-model="form.cost" aria-label="Tannarx" placeholder="0" />
            </label>

            <label class="field narrow">
              <span>Ustama</span>
              <AmountField
                v-model="form.markup"
                suffix="%"
                :grouped="false"
                aria-label="Ustama foizi"
              />
            </label>

            <label class="field">
              <span>Sotuv narxi</span>
              <AmountField v-model="form.sale_price" aria-label="Sotuv narxi" placeholder="0" />
            </label>
          </div>

          <template v-if="!barcode">
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
                  @click="toggleColor(item.id)"
                >
                  <span class="swatch-dot" :style="{ background: item.hex_code }" />
                  <small>{{ item.name }}</small>
                </button>
              </div>
            </div>

            <!-- Har rangning o'z surati: kassada aynan o'sha ko'rinadi -->
            <div v-if="chosenColors.length" class="field">
              <span class="field-label">Rang bo‘yicha rasm (ixtiyoriy)</span>

              <ul class="color-photos">
                <li v-for="item in chosenColors" :key="item.id">
                  <button
                    type="button"
                    :aria-label="`${item.name}: rasm tanlash`"
                    @click="pickColorPhoto(item.id)"
                  >
                    <img v-if="colorPhotos[item.id]" :src="colorPhotos[item.id]!.url" alt="" />
                    <span v-else class="color-photo-empty">
                      <svg aria-hidden="true"><use href="#i-image" /></svg>
                    </span>

                    <span class="color-photo-name">
                      <span class="swatch-dot" :style="{ background: item.hex_code }" />
                      {{ item.name }}
                    </span>
                  </button>

                  <button
                    v-if="colorPhotos[item.id]"
                    class="icon-button delete"
                    type="button"
                    :aria-label="`${item.name}: rasmni olib tashlash`"
                    @click="removeColorPhoto(item.id)"
                  >
                    <svg><use href="#i-trash" /></svg>
                  </button>
                </li>
              </ul>

              <input
                ref="colorPicker"
                type="file"
                accept="image/*"
                hidden
                data-testid="color-file-input"
                @change="onColorPick"
              />
            </div>
          </template>
        </section>
      </div>

    <footer class="panel-foot">
      <button
        class="button button-gradient next"
        type="button"
        :disabled="saving || uploading || !ready || !form.name.trim() || !photos.length"
        @click="onSave"
      >
        {{ uploading ? 'Rasm yuklanmoqda…' : saving ? 'Saqlanmoqda…' : 'Davom etish' }}
      </button>
    </footer>
  </div>
</template>

<style scoped>
.same-product {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 14px;
}

.panel-body {
  display: grid;
  grid-template-columns: 300px minmax(0, 1fr);
  gap: 22px;
}

.eyebrow {
  display: block;
  margin-bottom: 12px;
  color: var(--accent);
  font-size: 11px;
  letter-spacing: 2px;
}

/* Rang bo'yicha rasm: har rang uchun bitta katakcha */
.color-photos {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin: 0;
  padding: 0;
  list-style: none;
}

.color-photos li {
  position: relative;
}

.color-photos li > button:first-child {
  display: flex;
  width: 96px;
  flex-direction: column;
  gap: 4px;
  padding: 6px;
  border: 1px solid var(--border);
  border-radius: var(--radius-card);
  background: var(--surface);
  cursor: pointer;
}

.color-photos li > button:first-child:hover {
  border-color: var(--accent);
}

.color-photos img,
.color-photo-empty {
  width: 100%;
  height: 96px;
  border-radius: var(--radius);
  object-fit: cover;
}

.color-photo-empty {
  display: grid;
  place-items: center;
  background: var(--surface-soft);
}

.color-photo-empty svg {
  width: 22px;
  height: 22px;
  fill: none;
  stroke: var(--text-muted);
  stroke-width: 1.6;
}

.color-photo-name {
  display: flex;
  align-items: center;
  gap: 5px;
  font-size: 13px;
}

.color-photos .icon-button {
  position: absolute;
  top: 10px;
  right: 10px;
  background: var(--surface);
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
  font-size: 14px;
}

.drop-empty span {
  font-size: 13px;
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
  font-size: 11px;
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
  font-size: 15px;
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
  font-size: 13px;
}

.barcode-note {
  margin-bottom: 12px;
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
  font-size: 15px;
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
  font-size: 12px;
  text-align: center;
}

.swatch.active small {
  color: var(--text);
  font-weight: 600;
}

/* --- Pastki qator --- */

.panel-foot {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px solid var(--border);
}

.next {
  min-height: 48px;
  padding: 0 28px;
  font-size: 16px;
}

@media (max-width: 900px) {
  .panel-body {
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
