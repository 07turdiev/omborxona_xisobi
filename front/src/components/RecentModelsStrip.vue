<script setup lang="ts">
import { onMounted, ref } from 'vue'

import { catalogApi } from '@/api/catalog'
import type { CatalogCard } from '@/types'

/**
 * Kirim ekranining tepasidagi tezkor qator: oxirgi qo'shilgan modellar.
 *
 * Do'konga tovar to'lqin bilan keladi — bir partiyada bir necha model,
 * ko'pincha o'tgan haftada kiritilganining o'zi. Shuning uchun ularni
 * qidirmasdan, bir bosishda ochish kerak.
 */

const emit = defineEmits<{ pick: [product: number] }>()

const cards = ref<CatalogCard[]>([])

async function reload() {
  try {
    const page = await catalogApi.catalog({ ordering: 'newest' })

    cards.value = page.results.slice(0, 12)
  } catch {
    // Qator — qulaylik, qidiruv baribir ishlaydi
    cards.value = []
  }
}

/** «S–L · 3 rang» */
function summary(card: CatalogCard): string {
  const sizes = card.size_stock ?? []

  const range =
    sizes.length > 1
      ? `${sizes[0]!.size_name}–${sizes[sizes.length - 1]!.size_name}`
      : (sizes[0]?.size_name ?? '')

  const colors = card.color_count ? `${card.color_count} rang` : ''
  const parts = [range, colors].filter(Boolean)

  return parts.length ? parts.join(' · ') : 'Bitta variant'
}

onMounted(reload)

defineExpose({ reload })
</script>

<template>
  <div v-if="cards.length" class="model-strip" data-testid="model-strip">
    <button
      v-for="card in cards"
      :key="card.id"
      class="model-chip"
      type="button"
      :aria-label="`${card.name}: kirimga qo‘shish`"
      @click="emit('pick', card.id)"
    >
      <span class="chip-photo">
        <img
          v-if="card.primary_image"
          :src="card.primary_image.thumb"
          alt=""
          loading="lazy"
          decoding="async"
          width="52"
          height="52"
        />
        <svg v-else aria-hidden="true"><use href="#i-image" /></svg>
      </span>

      <span class="chip-copy">
        <strong>{{ card.name }}</strong>
        <small>{{ summary(card) }}</small>
      </span>

      <span class="chip-plus" aria-hidden="true">+</span>
    </button>
  </div>
</template>

<style scoped>
.model-strip {
  display: flex;
  gap: 10px;
  margin-bottom: 14px;
  padding: 2px 0 6px;
  overflow-x: auto;
  scrollbar-width: thin;
}

.model-chip {
  flex: none;
  display: flex;
  align-items: center;
  gap: 10px;
  width: 232px;
  padding: 8px 10px;
  border: 1px solid var(--border);
  border-radius: var(--radius-card);
  background: var(--surface);
  text-align: left;
  cursor: pointer;
  transition:
    transform 0.15s,
    box-shadow 0.15s;
}

.model-chip:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow);
}

.chip-photo {
  display: grid;
  flex: none;
  place-items: center;
  width: 52px;
  height: 52px;
  overflow: hidden;
  border-radius: var(--radius);
  background: var(--gray-1);
}

.chip-photo img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.chip-photo svg {
  width: 22px;
  height: 22px;
  fill: none;
  stroke: var(--gray-4);
  stroke-width: 1.3;
}

.chip-copy {
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
}

.chip-copy strong {
  overflow: hidden;
  font-size: 14px;
  font-weight: 600;
  white-space: nowrap;
  text-overflow: ellipsis;
}

.chip-copy small {
  color: var(--text-muted);
  font-size: 12px;
}

.chip-plus {
  margin-left: auto;
  color: var(--accent);
  font-size: 22px;
  line-height: 1;
}
</style>
