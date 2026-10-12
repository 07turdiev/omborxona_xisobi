<script setup lang="ts">
import { computed, nextTick, ref } from 'vue'

import { printWithPageSize } from '@/utils/print'
import { useAgentStore } from '@/stores/agent'
import { useAuthStore } from '@/stores/auth'
import type { ShelfLabel } from '@/api/agent'

/**
 * Ombor javonlarining yorliqlari: katta manzil (`A1`) va qator nomi.
 *
 * Yorliq javonga yopishtiriladi va uzoqdan o'qilishi kerak, shuning
 * uchun manzil yorliqqa sig'adigan eng katta harf bilan chiqadi.
 * Agent bo'lsa — printerga to'g'ridan-to'g'ri, bo'lmasa brauzer orqali.
 */

const agent = useAgentStore()
const auth = useAuthStore()

const shelves = ref<ShelfLabel[]>([])

const width = computed(() => auth.shop?.label_width_mm ?? 40)
const height = computed(() => auth.shop?.label_height_mm ?? 30)

/** Nom qatori va hoshiyalarga ketadigan balandlik, mm */
const NAME_ROOM_MM = 6

/** Qalin shriftda bitta belgining eni, em — kengroq harflar uchun zaxira bilan */
const CHAR_WIDTH_EM = 0.7

/**
 * Manzil harfining o'lchami, mm.
 *
 * Bo'yi bo'yicha — nom qatoridan qolgan joy, eni bo'yicha — belgilar
 * soni. Kichigi olinadi: `A10` torroq yorliqqa ham sig'sin.
 */
function codeSize(cell: string): number {
  const byHeight = height.value - NAME_ROOM_MM
  const byWidth = (width.value - 2) / (Math.max(1, cell.length) * CHAR_WIDTH_EM)

  return Math.max(4, Math.min(byHeight, byWidth))
}

/** Javonlarning yorliqlarini chop etadi: har javonga bitta. */
async function print(list: ShelfLabel[]) {
  shelves.value = list

  if (await agent.printShelfLabels(list)) return

  // Varaq DOM ga chiqishi uchun
  await nextTick()

  printWithPageSize(`@page { size: ${width.value}mm ${height.value}mm; margin: 0; }`)
}

defineExpose({ print })
</script>

<template>
  <!-- Varaq to'g'ridan-to'g'ri <body> ga chiqariladi (assets/main.css) -->
  <Teleport to="body">
    <div
      class="print-sheet shelf-labels"
      :style="{ '--label-w': `${width}mm`, '--label-h': `${height}mm` }"
    >
      <div v-for="shelf in shelves" :key="shelf.cell" class="shelf-label">
        <span v-if="shelf.name" class="shelf-name">{{ shelf.name }}</span>
        <strong class="shelf-code" :style="{ fontSize: `${codeSize(shelf.cell)}mm` }">
          {{ shelf.cell }}
        </strong>
      </div>
    </div>
  </Teleport>
</template>

<style scoped>
.shelf-label {
  width: var(--label-w);
  height: var(--label-h);
  padding: 1mm;
  display: flex;
  flex-direction: column;
  align-items: center;
  overflow: hidden;
  color: #000;
  font-family: 'Segoe UI', sans-serif;
  text-align: center;

  /* Har yorliq o'z sahifasida chiqadi */
  page-break-after: always;
  break-after: page;
}

.shelf-label:last-child {
  page-break-after: auto;
  break-after: auto;
}

.shelf-name {
  max-width: 100%;
  font-size: 3mm;
  line-height: 1.1;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* Qolgan joyning hammasi — manzilga */
.shelf-code {
  flex: 1;
  display: flex;
  align-items: center;
  font-weight: 800;
  line-height: 1;
  white-space: nowrap;
}
</style>
