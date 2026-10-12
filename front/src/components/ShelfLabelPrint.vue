<script setup lang="ts">
import { computed, nextTick, ref } from 'vue'

import { SHELF_TEXT_MM } from '@/api/agent'
import { printWithPageSize } from '@/utils/print'
import { useAgentStore } from '@/stores/agent'
import { useAuthStore } from '@/stores/auth'

/**
 * Ombor javonlarining yorliqlari: yorliqning o'rtasida manzil (`A1`).
 *
 * Agent bo'lsa — printerga to'g'ridan-to'g'ri, bo'lmasa brauzer orqali.
 * Ikkala yo'lda ham harf o'lchami bitta: `SHELF_TEXT_MM`.
 */

const agent = useAgentStore()
const auth = useAuthStore()

const cells = ref<string[]>([])

const width = computed(() => auth.shop?.label_width_mm ?? 40)
const height = computed(() => auth.shop?.label_height_mm ?? 30)

/** Qalin shriftda bitta belgining eni, em — kengroq harflar uchun zaxira bilan */
const CHAR_WIDTH_EM = 0.7

/**
 * Manzil shriftining o'lchami, mm.
 *
 * Odatda `SHELF_TEXT_MM`, lekin yorliqqa sig'masa kichrayadi: `A10`
 * tor yorliqqa ham sig'sin.
 */
function codeSize(cell: string): number {
  const byWidth = (width.value - 2) / (Math.max(1, cell.length) * CHAR_WIDTH_EM)

  return Math.max(4, Math.min(SHELF_TEXT_MM, height.value - 2, byWidth))
}

/** Javonlarning yorliqlarini chop etadi: har javonga bitta. */
async function print(list: string[]) {
  cells.value = list

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
      <div v-for="cell in cells" :key="cell" class="shelf-label">
        <strong class="shelf-code" :style="{ fontSize: `${codeSize(cell)}mm` }">{{ cell }}</strong>
      </div>
    </div>
  </Teleport>
</template>

<style scoped>
.shelf-label {
  width: var(--label-w);
  height: var(--label-h);
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  color: #000;
  font-family: 'Segoe UI', sans-serif;

  /* Har yorliq o'z sahifasida chiqadi */
  page-break-after: always;
  break-after: page;
}

.shelf-label:last-child {
  page-break-after: auto;
  break-after: auto;
}

.shelf-code {
  font-weight: 800;
  line-height: 1;
  white-space: nowrap;
}
</style>
