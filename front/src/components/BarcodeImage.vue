<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import JsBarcode from 'jsbarcode'

/**
 * Shtrix-kod rasmi. Yorliqda EAN-13, chekda CODE128 ishlatiladi.
 * Chizish brauzerda bajariladi — printer uchun maxsus drayver kerak emas.
 */
const props = withDefaults(
  defineProps<{
    value: string
    format?: 'EAN13' | 'CODE128'
    height?: number
    width?: number
    fontSize?: number
    displayValue?: boolean
  }>(),
  { format: 'EAN13', height: 40, width: 1.6, fontSize: 12, displayValue: true },
)

const target = ref<SVGSVGElement | null>(null)

function draw() {
  if (!target.value || !props.value) return

  try {
    JsBarcode(target.value, props.value, {
      format: props.format,
      height: props.height,
      width: props.width,
      fontSize: props.fontSize,
      displayValue: props.displayValue,
      margin: 0,
    })
  } catch {
    // Noto'g'ri kod (masalan EAN-13 uchun 13 xonali emas) — bo'sh qoladi
  }
}

onMounted(draw)
watch(() => [props.value, props.format], draw)
</script>

<template>
  <svg ref="target" class="barcode"></svg>
</template>

<style scoped>
.barcode {
  display: block;
  max-width: 100%;
}
</style>
