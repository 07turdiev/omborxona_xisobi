<script setup lang="ts">
import { onMounted, ref } from 'vue'

import { catalogApi } from '@/api/catalog'
import { errorMessage } from '@/api/client'
import type { Category, Color, Size } from '@/types'

const categories = ref<Category[]>([])
const sizes = ref<Size[]>([])
const colors = ref<Color[]>([])

const error = ref('')
const notice = ref('')

const newCategory = ref('')
const newSize = ref('')
const newColor = ref('')
const newColorHex = ref('#808080')

async function load() {
  ;[categories.value, sizes.value, colors.value] = await Promise.all([
    catalogApi.categories(),
    catalogApi.sizes(),
    catalogApi.colors(),
  ])
}

async function run(action: () => Promise<unknown>, fallback: string) {
  error.value = ''
  notice.value = ''

  try {
    await action()
  } catch (err) {
    error.value = errorMessage(err, fallback)
  } finally {
    await load()
  }
}

function addCategory() {
  const name = newCategory.value.trim()

  if (!name) return

  void run(async () => {
    await catalogApi.createCategory(name)
    newCategory.value = ''
  }, 'Kategoriyani qo‘shib bo‘lmadi.')
}

/** Kategoriyaning MXIK kodi — shu kategoriyadagi hamma mahsulotga tarqaladi. */
function saveCategoryCode(item: Category, value: string) {
  void run(async () => {
    await catalogApi.updateCategory(item.id, { mxik_code: value.trim() })
    notice.value = `${item.name}: MXIK kodi saqlandi.`
  }, 'MXIK kodini saqlab bo‘lmadi.')
}

function addSize() {
  const name = newSize.value.trim()

  if (!name) return

  void run(async () => {
    await catalogApi.createSize({ name, position: sizes.value.length + 1 })
    newSize.value = ''
  }, 'O‘lchamni qo‘shib bo‘lmadi.')
}

function addColor() {
  const name = newColor.value.trim()

  if (!name) return

  void run(async () => {
    await catalogApi.createColor({ name, hex_code: newColorHex.value.toUpperCase() })
    newColor.value = ''
    newColorHex.value = '#808080'
  }, 'Rangni qo‘shib bo‘lmadi.')
}

/** Mahsulot sahifasidagi rang doirachasi shu kod bilan chiziladi */
function saveColorHex(item: Color, value: string) {
  void run(
    () => catalogApi.updateColor(item.id, { hex_code: value.toUpperCase() }),
    'Rang kodini saqlab bo‘lmadi.',
  )
}

function remove(kind: 'category' | 'size' | 'color', id: number) {
  if (!window.confirm('O‘chirilsinmi?')) return

  void run(async () => {
    if (kind === 'category') await catalogApi.removeCategory(id)
    if (kind === 'size') await catalogApi.removeSize(id)
    if (kind === 'color') await catalogApi.removeColor(id)
  }, 'O‘chirib bo‘lmadi — bog‘liq tovarlar bor.')
}

onMounted(load)
</script>

<template>
  <section class="app-section active">
    <p v-if="error" class="load-error">{{ error }}</p>
    <p v-if="notice" class="notice">{{ notice }}</p>

    <div class="attributes">
      <div class="table-card card-padded wide">
        <h3>Kategoriyalar</h3>

        <div class="add-row">
          <input v-model="newCategory" type="text" placeholder="Yangi kategoriya" @keydown.enter="addCategory" />
          <button class="button button-outline" type="button" @click="addCategory">Qo‘shish</button>
        </div>

        <p class="field-hint">
          MXIK — 17 xonali soliq kodi, tasnif.soliq.uz dan olinadi.
        </p>

        <table class="data-table">
          <thead>
            <tr>
              <th>Nomi</th>
              <th class="num">Mahsulot</th>
              <th>MXIK kodi</th>
              <th></th>
            </tr>
          </thead>

          <tbody>
            <tr v-for="item in categories" :key="item.id">
              <td>{{ item.name }}</td>
              <td class="num">{{ item.product_count ?? '—' }}</td>
              <td>
                <input
                  class="mxik-input"
                  type="text"
                  inputmode="numeric"
                  maxlength="17"
                  placeholder="17 xonali raqam"
                  :value="item.mxik_code"
                  :class="{ missing: !item.mxik_code }"
                  @change="saveCategoryCode(item, ($event.target as HTMLInputElement).value)"
                />
              </td>
              <td class="num">
                <button class="icon-button delete" type="button" aria-label="O‘chirish" @click="remove('category', item.id)">
                  <svg><use href="#i-trash" /></svg>
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <div class="table-card card-padded">
        <h3>O‘lchamlar</h3>

        <div class="add-row">
          <input v-model="newSize" type="text" placeholder="S, M, L, 42…" @keydown.enter="addSize" />
          <button class="button button-outline" type="button" @click="addSize">Qo‘shish</button>
        </div>

        <ul class="attribute-list">
          <li v-for="item in sizes" :key="item.id">
            <span>{{ item.name }}</span>
            <button class="icon-button delete" type="button" aria-label="O‘chirish" @click="remove('size', item.id)">
              <svg><use href="#i-trash" /></svg>
            </button>
          </li>
        </ul>
      </div>

      <div class="table-card card-padded">
        <h3>Ranglar</h3>

        <div class="add-row">
          <input v-model="newColor" type="text" placeholder="Qora, oq…" @keydown.enter="addColor" />
          <input v-model="newColorHex" class="color-input" type="color" aria-label="Rang kodi" />
          <button class="button button-outline" type="button" @click="addColor">Qo‘shish</button>
        </div>

        <ul class="attribute-list">
          <li v-for="item in colors" :key="item.id">
            <span class="color-row">
              <input
                class="color-input"
                type="color"
                :value="item.hex_code"
                :aria-label="`${item.name} rang kodi`"
                @change="saveColorHex(item, ($event.target as HTMLInputElement).value)"
              />
              <span>{{ item.name }}</span>
              <small>{{ item.hex_code }}</small>
            </span>

            <button class="icon-button delete" type="button" aria-label="O‘chirish" @click="remove('color', item.id)">
              <svg><use href="#i-trash" /></svg>
            </button>
          </li>
        </ul>
      </div>
    </div>
  </section>
</template>

<style scoped>
.attributes {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
  gap: 12px;
}

.attributes .wide {
  grid-column: 1 / -1;
}

.add-row {
  display: flex;
  gap: 6px;
  margin: 10px 0;
}

.mxik-input {
  width: 190px;
  font-variant-numeric: tabular-nums;
}

.mxik-input.missing {
  border-color: var(--orange);
}

.attribute-list {
  margin: 0;
  padding: 0;
  list-style: none;
}

.attribute-list li {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 6px 0;
  border-bottom: 1px solid var(--border);
  font-size: 14px;
}

.color-row {
  display: inline-flex;
  align-items: center;
  gap: 8px;
}

.color-row small {
  color: var(--text-muted);
  font-variant-numeric: tabular-nums;
}

.color-input {
  flex: none;
  width: 34px;
  height: 34px;
  padding: 2px;
  border: 1px solid var(--border-strong);
  border-radius: var(--radius);
  background: var(--surface);
  cursor: pointer;
}
</style>
