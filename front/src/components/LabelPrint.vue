<script setup lang="ts">
import { computed } from 'vue'

import BarcodeImage from '@/components/BarcodeImage.vue'
import { formatMoney } from '@/utils/money'
import { printWithPageSize } from '@/utils/print'
import { useAgentStore } from '@/stores/agent'
import { useAuthStore } from '@/stores/auth'
import type { LabelItem } from '@/api/agent'

const props = defineProps<{ items: LabelItem[] }>()

const agent = useAgentStore()
const auth = useAuthStore()

const shopName = computed(() => auth.shop?.shop_name ?? '')
const width = computed(() => auth.shop?.label_width_mm ?? 40)
const height = computed(() => auth.shop?.label_height_mm ?? 30)

/** Har dona uchun bitta yorliq. */
const labels = computed(() =>
  props.items.flatMap((item) => Array.from({ length: Math.max(1, item.quantity) }, () => item)),
)

/**
 * Yorliqlarni chop etadi.
 *
 * Agent bo'lsa — shtrix-kodni printerning o'zi chizadi va yorliqlar
 * orasida bo'sh yorliq chiqmaydi. Bo'lmasa har yorliq alohida sahifa
 * bo'lib brauzer orqali chiqadi.
 */
async function printLabels() {
  if (await agent.printLabels(props.items)) return

  printWithPageSize(`@page { size: ${width.value}mm ${height.value}mm; margin: 0; }`)
}

defineExpose({ printLabels })
</script>

<template>
  <!-- Varaq to'g'ridan-to'g'ri <body> ga chiqariladi: ilova qatlami
       chop etishda sahifani kichraytirib yubormasin (assets/main.css) -->
  <Teleport to="body">
    <div
      class="print-sheet labels"
      :style="{ '--label-w': `${width}mm`, '--label-h': `${height}mm` }"
    >
    <div v-for="(item, index) in labels" :key="index" class="label">
      <span class="label-shop">{{ shopName }}</span>
      <span class="label-name">{{ item.name }}</span>
      <span class="label-variant">{{ item.label }}</span>
      <strong class="label-price">
        <s v-if="item.oldPrice" class="label-old-price">{{ formatMoney(item.oldPrice) }}</s>
        {{ formatMoney(item.price) }} so‘m
      </strong>

      <!-- Chiziq balandligi 12 mm — standart talab qiladigan eng kam o'lcham -->
        <BarcodeImage :value="item.barcode" format="EAN13" :height-mm="12" :text-mm="2.2" />
      </div>
    </div>
  </Teleport>
</template>

<style scoped>
.label {
  width: var(--label-w);
  height: var(--label-h);
  /* Tepada 2.5 mm: printer yorliqni biroz siljitib boshlasa ham do'kon
     nomi qog'ozda qoladi (1 mm da chiqib ketardi). Ko'prog'iga joy yo'q:
     o'lchamli tovarda mazmun 30 mm ga shunda sig'adi. */
  padding: 2.5mm 1mm 1mm;
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

.label:last-child {
  page-break-after: auto;
  break-after: auto;
}

/* Yorliqdagi o'lchamlar millimetrda: 30 mm balandlikka shtrix-kod
   uchun 12 mm qoldirish kerak, shuning uchun matnlar aniq o'lchangan. */
.label-shop {
  font-size: 2mm;
  line-height: 1.1;
}

/* Nom, o'lcham va narx — bir guruh, shtrix-kod ustida. Ortiqcha joy
   do'kon nomi bilan nom orasida qoladi, guruh ichida emas */
.label-name {
  margin-top: auto;
  font-size: 2.6mm;
  font-weight: 600;
  line-height: 1.1;
  max-height: 2.9mm;
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;
  max-width: 100%;
}

.label-variant {
  font-size: 2.2mm;
  line-height: 1.1;
}

.label-price {
  font-size: 3.2mm;
  line-height: 1.1;
}

/* Aksiyadan oldingi narx: kichik va chizilgan */
.label-old-price {
  margin-right: 1mm;
  font-size: 2.2mm;
  font-weight: 400;
}
</style>
