<script setup lang="ts">
import { computed } from 'vue'

import BarcodeImage from '@/components/BarcodeImage.vue'
import { formatMoney } from '@/utils/money'
import { printWithPageSize } from '@/utils/print'
import { useAuthStore } from '@/stores/auth'

interface LabelItem {
  barcode: string
  name: string
  label: string
  price: string
  quantity: number
}

const props = defineProps<{ items: LabelItem[] }>()

const auth = useAuthStore()

const shopName = computed(() => auth.shop?.shop_name ?? '')
const width = computed(() => auth.shop?.label_width_mm ?? 40)
const height = computed(() => auth.shop?.label_height_mm ?? 30)

/** Har dona uchun bitta yorliq. */
const labels = computed(() =>
  props.items.flatMap((item) => Array.from({ length: Math.max(1, item.quantity) }, () => item)),
)

/** Har yorliq — alohida sahifa, o'lchami sozlamalardan. */
function printLabels() {
  printWithPageSize(`@page { size: ${width.value}mm ${height.value}mm; margin: 0; }`)
}

defineExpose({ printLabels })
</script>

<template>
  <div
    class="print-sheet labels"
    :style="{ '--label-w': `${width}mm`, '--label-h': `${height}mm` }"
  >
    <div v-for="(item, index) in labels" :key="index" class="label">
      <span class="label-shop">{{ shopName }}</span>
      <span class="label-name">{{ item.name }}</span>
      <span class="label-variant">{{ item.label }}</span>
      <strong class="label-price">{{ formatMoney(item.price) }} so‘m</strong>

      <BarcodeImage :value="item.barcode" format="EAN13" :height="22" :width="1.1" :font-size="9" />
    </div>
  </div>
</template>

<style scoped>
.label {
  width: var(--label-w);
  height: var(--label-h);
  padding: 1mm;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: space-between;
  overflow: hidden;
  color: #000;
  font-family: 'Segoe UI', sans-serif;
  text-align: center;

  /* Har yorliq o'z sahifasida chiqadi */
  page-break-after: always;
  break-after: page;
}

.label:last-child {
  page-break-after: auto;
  break-after: auto;
}

.label-shop {
  font-size: 6pt;
}

.label-name {
  font-size: 7pt;
  font-weight: 600;
  line-height: 1.1;
  max-height: 2.4em;
  overflow: hidden;
}

.label-variant {
  font-size: 6pt;
}

.label-price {
  font-size: 9pt;
}
</style>
