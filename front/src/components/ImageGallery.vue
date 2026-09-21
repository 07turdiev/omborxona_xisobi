<script setup lang="ts">
import { nextTick, ref, watch } from 'vue'

import type { ProductImage } from '@/types'

const props = defineProps<{ images: ProductImage[]; alt: string }>()

const track = ref<HTMLElement | null>(null)
const index = ref(0)

/** Rang almashganda galereya birinchi rasmdan boshlanadi */
watch(
  () => props.images.map((image) => image.id).join(','),
  async () => {
    index.value = 0
    await nextTick()
    track.value?.scrollTo({ left: 0 })
  },
)

function onScroll() {
  const element = track.value

  if (element?.clientWidth) {
    index.value = Math.round(element.scrollLeft / element.clientWidth)
  }
}

function go(target: number) {
  const element = track.value

  if (!element) return

  const clamped = Math.max(0, Math.min(props.images.length - 1, target))

  element.scrollTo({ left: clamped * element.clientWidth, behavior: 'smooth' })
  index.value = clamped
}
</script>

<template>
  <div class="gallery">
    <div
      v-if="images.length"
      class="gallery-main"
      tabindex="0"
      aria-label="Rasmlar"
      @keydown.left.prevent="go(index - 1)"
      @keydown.right.prevent="go(index + 1)"
    >
      <!-- Suzish — brauzerning o'z scroll-snap mexanizmi: JS siz ishlaydi
           va barmoq harakatiga tabiiy javob beradi -->
      <div ref="track" class="gallery-track" @scroll.passive="onScroll">
        <a
          v-for="(image, position) in images"
          :key="image.id"
          class="gallery-slide"
          :href="image.large"
          target="_blank"
          rel="noopener"
          :aria-label="`${position + 1}-rasmni kattalashtirish`"
        >
          <img
            :src="image.medium"
            :alt="`${alt} — ${position + 1}`"
            :loading="position === 0 ? 'eager' : 'lazy'"
            decoding="async"
            width="800"
            height="1000"
          />
        </a>
      </div>

      <template v-if="images.length > 1">
        <button
          class="gallery-arrow prev"
          type="button"
          aria-label="Oldingi rasm"
          :disabled="index === 0"
          @click="go(index - 1)"
        >
          ‹
        </button>

        <button
          class="gallery-arrow next"
          type="button"
          aria-label="Keyingi rasm"
          :disabled="index === images.length - 1"
          @click="go(index + 1)"
        >
          ›
        </button>

        <span class="gallery-counter">{{ index + 1 }} / {{ images.length }}</span>
      </template>
    </div>

    <div v-else class="gallery-placeholder">
      <svg aria-hidden="true"><use href="#i-image" /></svg>
      <span>Rasm yo‘q</span>
    </div>

    <div v-if="images.length > 1" class="gallery-thumbs">
      <button
        v-for="(image, position) in images"
        :key="image.id"
        class="gallery-thumb"
        :class="{ active: position === index }"
        type="button"
        :aria-label="`${position + 1}-rasm`"
        :aria-current="position === index"
        @click="go(position)"
      >
        <img :src="image.thumb" alt="" loading="lazy" decoding="async" width="200" height="250" />
      </button>
    </div>
  </div>
</template>

<style scoped>
.gallery {
  display: flex;
  flex-direction: column;
  gap: 8px;
  min-width: 0;
}

.gallery-main {
  position: relative;
  overflow: hidden;
  border-radius: var(--radius-card);
  background: var(--surface-soft);
  outline: none;
}

.gallery-main:focus-visible {
  box-shadow: 0 0 0 2px var(--accent);
}

.gallery-track {
  display: flex;
  overflow-x: auto;
  scroll-snap-type: x mandatory;
  overscroll-behavior-x: contain;
  scrollbar-width: none;
}

.gallery-track::-webkit-scrollbar {
  display: none;
}

.gallery-slide {
  flex: 0 0 100%;
  display: block;
  aspect-ratio: 4 / 5;
  scroll-snap-align: start;
}

/* Mahsulot sahifasida kiyim kesilmasin — `cover` emas, `contain` */
.gallery-slide img {
  display: block;
  width: 100%;
  height: 100%;
  object-fit: contain;
}

.gallery-arrow {
  position: absolute;
  top: 50%;
  width: 40px;
  height: 40px;
  transform: translateY(-50%);
  border: 1px solid var(--border-strong);
  border-radius: 50%;
  background: rgb(255 255 255 / 90%);
  color: var(--text);
  font-size: 24px;
  line-height: 1;
  cursor: pointer;
}

.gallery-arrow.prev {
  left: 8px;
}

.gallery-arrow.next {
  right: 8px;
}

.gallery-arrow:disabled {
  opacity: 0.3;
  cursor: default;
}

/* Sensorli ekranda strelka kerak emas — rasm barmoq bilan suriladi */
@media (hover: none) {
  .gallery-arrow {
    display: none;
  }
}

.gallery-counter {
  position: absolute;
  right: 8px;
  bottom: 8px;
  padding: 2px 8px;
  border-radius: 999px;
  background: rgb(0 0 0 / 55%);
  color: #fff;
  font-size: 12px;
}

/* Rasm bo'lmasa joy egallamasin: telefonda 4:5 bo'sh maydon narx va
   o'lchamlarni ekrandan pastga surib yuborardi */
.gallery-placeholder {
  aspect-ratio: 16 / 9;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  border-radius: var(--radius-card);
  background: var(--surface-soft);
  color: var(--text-muted);
  font-size: 13px;
}

.gallery-placeholder svg {
  width: 48px;
  height: 48px;
  fill: none;
  stroke: currentColor;
  stroke-width: 1.4;
}

.gallery-thumbs {
  display: flex;
  gap: 6px;
  overflow-x: auto;
}

.gallery-thumb {
  flex: 0 0 56px;
  height: 70px;
  padding: 0;
  overflow: hidden;
  border: 2px solid transparent;
  border-radius: var(--radius);
  background: var(--surface-soft);
  cursor: pointer;
}

.gallery-thumb.active {
  border-color: var(--accent);
}

.gallery-thumb img {
  display: block;
  width: 100%;
  height: 100%;
  object-fit: cover;
}
</style>
