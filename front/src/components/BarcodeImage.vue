<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import JsBarcode from 'jsbarcode'

import { MODULE_MM, QUIET_ZONES, type BarcodeFormat } from '@/utils/barcode'

/**
 * Shtrix-kod — millimetrda aniq o'lchangan SVG.
 *
 * JsBarcode odatda piksel bilan chizadi: 203 dpi printerda modul
 * kengligi nuqtaga butun bo'linmaydi, chiziqlar teng chiqmaydi va
 * skaner kodni o'qiy olmaydi.
 *
 * Shuning uchun JsBarcode'dan faqat **modullar to'ri** olinadi
 * (`width: 1` — har modul 1 birlik), so'ng o'lcham `viewBox` orqali
 * millimetrga bog'lanadi: 1 modul = `moduleMm` mm, ya'ni 2 nuqta.
 *
 * Chizish to'g'ridan-to'g'ri shu elementga bajariladi: JsBarcode
 * DOM'ga ulanmagan SVG ni qabul qilmaydi.
 *
 * `shape-rendering="crispEdges"` — brauzer chiziq chetlarini
 * silliqlamasin: termal printerda silliqlangan chet kulrang nuqta
 * bo'lib chiqadi.
 */
const props = withDefaults(
  defineProps<{
    value: string
    format?: BarcodeFormat
    /** Eng tor chiziq kengligi, mm */
    moduleMm?: number
    /** Chiziqlar balandligi, mm */
    heightMm?: number
    /** Ostida raqamlarni ko'rsatish */
    showText?: boolean
    /** Raqamlar o'lchami, mm */
    textMm?: number
  }>(),
  {
    format: 'EAN13',
    moduleMm: MODULE_MM,
    heightMm: 12,
    showText: true,
    textMm: 2.5,
  },
)

const SVG_NS = 'http://www.w3.org/2000/svg'

/** Chiziq balandligi `viewBox` ichida — mm ga viewBox orqali bog'lanadi */
const BAR_UNITS = 100

const target = ref<SVGSVGElement | null>(null)
const failure = ref('')

/** Modullar soni — to'rtburchaklar geometriyasidan (har modul 1 birlik). */
function countModules(svg: SVGSVGElement): number {
  let right = 0

  for (const rect of Array.from(svg.querySelectorAll('rect'))) {
    const x = Number(rect.getAttribute('x')) || 0
    const width = Number(rect.getAttribute('width')) || 0

    right = Math.max(right, x + width)
  }

  return Math.round(right)
}

function draw() {
  const svg = target.value

  if (!svg || !props.value) return

  failure.value = ''

  // Oldingi chizmani tozalaymiz va o'lchamlarni bekor qilamiz
  svg.replaceChildren()
  svg.removeAttribute('viewBox')

  try {
    JsBarcode(svg, props.value, {
      format: props.format,
      width: 1,
      height: BAR_UNITS,
      margin: 0,
      displayValue: false,
    })
  } catch (error) {
    failure.value = error instanceof Error ? error.message : 'chizib bo‘lmadi'
    svg.replaceChildren()
    return
  }

  const symbolModules = countModules(svg)

  if (!symbolModules) {
    failure.value = 'kod bo‘sh chiqdi'
    return
  }

  // Tinch zonalarni qo'shib, o'lchamni millimetrga bog'laymiz
  const quiet = QUIET_ZONES[props.format]
  const modules = quiet.left + symbolModules + quiet.right
  const width = Math.round(modules * props.moduleMm * 100) / 100

  const group = document.createElementNS(SVG_NS, 'g')
  group.setAttribute('transform', `translate(${quiet.left} 0)`)
  group.append(...Array.from(svg.childNodes))

  svg.replaceChildren(group)

  svg.setAttribute('width', `${width}mm`)
  svg.setAttribute('height', `${props.heightMm}mm`)
  svg.setAttribute('viewBox', `0 0 ${modules} ${BAR_UNITS}`)
  // Ikki o'q bo'yicha aniq moslik: chiziqlar tik to'rtburchak, cho'zilmaydi
  svg.setAttribute('preserveAspectRatio', 'none')
  svg.setAttribute('shape-rendering', 'crispEdges')
}

onMounted(draw)
watch(() => [props.value, props.format, props.moduleMm, props.heightMm], draw)
</script>

<template>
  <div class="barcode-block">
    <svg ref="target" class="barcode"></svg>

    <span v-if="showText && !failure" class="barcode-text" :style="{ fontSize: `${textMm}mm` }">
      {{ value }}
    </span>

    <span v-if="failure" class="barcode-error">
      Shtrix-kod chizilmadi ({{ value }}): {{ failure }}
    </span>
  </div>
</template>

<style scoped>
.barcode-block {
  display: flex;
  flex-direction: column;
  align-items: center;
}

/* DIQQAT: bu yerda `width`, `max-width` yoki `transform` bo'lmasligi
   kerak. SVG o'lchami millimetrda berilgan; CSS uni cho'zsa yoki
   kichraytirsa, modul kengligi printer nuqtasiga tushmay qoladi. */
.barcode {
  display: block;
}

.barcode-text {
  margin-top: 0.5mm;
  font-family: 'Segoe UI', sans-serif;
  letter-spacing: 0.3mm;
  line-height: 1.1;
}

.barcode-error {
  color: #c00;
  font-size: 2.5mm;
}
</style>
