<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'

import BarcodeImage from '@/components/BarcodeImage.vue'
import * as agentApi from '@/api/agent'
import { catalogApi } from '@/api/catalog'
import { salesApi } from '@/api/sales'
import { lastReceiptHeight, printWithPageSize } from '@/utils/print'
import { useAgentStore } from '@/stores/agent'
import { useAuthStore } from '@/stores/auth'
import { useToastStore } from '@/stores/toast'

/** Nazorat raqami to'g'ri bo'lgan sinov kodi */
const TEST_EAN13 = '2000000000015'
const TEST_RECEIPT_CODE = '2026000001'

const auth = useAuthStore()

const labelWidth = computed(() => auth.shop?.label_width_mm ?? 40)
const labelHeight = computed(() => auth.shop?.label_height_mm ?? 30)

/** Chek qog'ozi — sozlamalardagi, ya'ni drayverdagi bilan bir xil */
const receiptWidth = computed(() => auth.shop?.receipt_width_mm ?? 80)
const receiptHeight = computed(() => auth.shop?.receipt_page_height_mm ?? 110)

/** Oxirgi chop etilgan chek mazmunining balandligi */
const lastHeight = ref<number | null>(lastReceiptHeight())

const sheet = ref<'label' | 'receipt' | null>(null)

function printLabel() {
  sheet.value = 'label'

  // Varaq DOM'ga chiqishi uchun keyingi kadrda chop etamiz
  setTimeout(() => {
    printWithPageSize(`@page { size: ${labelWidth.value}mm ${labelHeight.value}mm; margin: 0; }`)
    sheet.value = null
  }, 60)
}

function printReceipt() {
  sheet.value = 'receipt'

  setTimeout(() => {
    // Haqiqiy chek bilan bir xil qog'oz — drayver sozlamasi shu yerdan
    // tekshiriladi
    printWithPageSize(
      `@page { size: ${receiptWidth.value}mm ${receiptHeight.value}mm; margin: 0; }`,
    )
    sheet.value = null
  }, 60)
}

// --- Chop etish agenti -----------------------------------------------

const agent = useAgentStore()
const toast = useToastStore()

const agentBusy = ref(false)

onMounted(() => {
  void agent.probe()
})

/** Vaqtni qisqartiradi: `2026-09-18T10:00:00.000Z` → `2026-09-18 10:00` */
function shortTime(iso: string): string {
  return iso.replace('T', ' ').slice(0, 16)
}

async function send(what: string, action: () => Promise<void>) {
  agentBusy.value = true

  try {
    await action()
    toast.show(`${what} agentga yuborildi`)
  } catch (error) {
    toast.show(`${what} yuborilmadi: ${(error as Error).message}`, 'error')
  } finally {
    agentBusy.value = false

    // Agent oxirgi xatoni eslab qoladi — jadval yangilansin
    await agent.probe()
  }
}

/** Sinov cheki: haqiqiy sotuv yaratilmaydi, faqat printer tekshiriladi. */
function sendTestReceipt() {
  return send('Sinov cheki', () =>
    agentApi.sendReceipt({
      shopName: auth.shop?.shop_name ?? '',
      number: 'SINOV',
      dateTime: new Date().toISOString().replace('T', ' ').slice(0, 16),
      cashier: 'sinov',
      lines: [
        {
          name: 'Sinov tovari',
          variant: 'M / Oq',
          quantity: 1,
          unitPrice: '100000.00',
          lineTotal: '100000.00',
        },
      ],
      discount: '0.00',
      total: '100000.00',
      payments: { cash: '100000.00', card: '0.00' },
      barcode: TEST_RECEIPT_CODE,
      footer: 'Sinov cheki — hisobga olinmaydi',
    }),
  )
}

function sendTestLabel() {
  return send('Sinov yorlig‘i', () =>
    agentApi.sendLabels({
      widthMm: labelWidth.value,
      heightMm: labelHeight.value,
      labels: [
        {
          shopName: auth.shop?.shop_name ?? '',
          name: 'Sinov yorlig‘i',
          variant: `${labelWidth.value}×${labelHeight.value} mm`,
          price: '0 so‘m',
          barcode: TEST_EAN13,
          quantity: 1,
        },
      ],
    }),
  )
}

// --- Skaner sinovi ---------------------------------------------------

interface ScanResult {
  code: string
  length: number
  hadEnter: boolean
  gapMs: number
  nonDigits: string[]
  match: string
  checking: boolean
}

const scanInput = ref<HTMLInputElement | null>(null)
const current = ref('')
const results = ref<ScanResult[]>([])

let times: number[] = []
let idleTimer: ReturnType<typeof setTimeout> | null = null

function onKeydown(event: KeyboardEvent) {
  if (event.key === 'Enter') {
    finish(true)
    return
  }

  if (event.key.length === 1) {
    times.push(performance.now())

    // Enter kelmasa ham natijani ko'rsatamiz — bu ham muhim ma'lumot
    if (idleTimer) clearTimeout(idleTimer)
    idleTimer = setTimeout(() => finish(false), 500)
  }
}

/** Belgilar orasidagi eng katta oraliq — skaner tezligi shundan ko'rinadi. */
function longestGap(): number {
  let longest = 0

  for (let i = 1; i < times.length; i += 1) {
    longest = Math.max(longest, times[i]! - times[i - 1]!)
  }

  return Math.round(longest)
}

async function finish(hadEnter: boolean) {
  if (idleTimer) {
    clearTimeout(idleTimer)
    idleTimer = null
  }

  const code = current.value.trim()

  current.value = ''

  if (!code) {
    times = []
    return
  }

  const result: ScanResult = {
    code,
    length: code.length,
    hadEnter,
    gapMs: longestGap(),
    nonDigits: [...new Set(code.split('').filter((ch) => !/\d/.test(ch)))],
    match: '',
    checking: true,
  }

  times = []
  results.value.unshift(result)

  scanInput.value?.focus()

  result.match = await lookup(code)
  result.checking = false
}

/** Kod bazadagi tovarga yoki chekka to'g'ri keladimi. */
async function lookup(code: string): Promise<string> {
  try {
    const variant = await catalogApi.byBarcode(code)

    return `Tovar: ${variant.product_name} ${variant.label}`.trim()
  } catch {
    // Tovar emas — chek bo'lishi mumkin
  }

  try {
    const sale = await salesApi.byNumber(code)

    if (sale) return `Chek: ${sale.number}`
  } catch {
    // e'tiborsiz
  }

  return 'Bazada topilmadi'
}
</script>

<template>
  <section class="app-section active">
    <div class="cards">
      <!-- Chop etish agenti -->
      <div class="table-card card-padded agent-card">
        <h3>Chop etish agenti</h3>

        <p class="agent-status">
          <span v-if="agent.available" class="pill pill-green">Agent ishlayapti</span>
          <span v-else class="pill pill-grey">Agent topilmadi</span>

          <span v-if="agent.available" class="muted">v{{ agent.version }}</span>

          <button class="button button-outline" type="button" @click="agent.probe()">
            Qayta tekshirish
          </button>
        </p>

        <p class="hint">
          Agent ishlab tursa chek va yorliq to‘g‘ridan-to‘g‘ri printerga ketadi:
          chop etish oynasi ochilmaydi, qog‘oz bo‘shga ketmaydi va shtrix-kodni
          printerning o‘zi chizadi. Agent o‘chirilgan bo‘lsa hamma narsa
          avvalgidek brauzer orqali chiqadi — sotuv to‘xtamaydi.
          Ishga tushirish: <code>agent</code> papkasida <code>npm start</code>.
        </p>

        <table v-if="agent.printers.length" class="data-table">
          <thead>
            <tr>
              <th>Printer</th>
              <th>Ulanish</th>
              <th>Holat</th>
              <th>Oxirgi xato</th>
            </tr>
          </thead>

          <tbody>
            <tr v-for="printer in agent.printers" :key="printer.name">
              <td>
                <strong>{{ printer.name === 'receipt' ? 'Chek' : 'Yorliq' }}</strong>
              </td>

              <td>
                {{ printer.transport }}
                <small class="cell-sub">{{ printer.target }}</small>
              </td>

              <td>
                <span class="pill" :class="printer.responds ? 'pill-green' : 'pill-red'">
                  {{ printer.responds ? 'javob bermoqda' : 'javob yo‘q' }}
                </span>
              </td>

              <td>
                <template v-if="printer.lastError">
                  <span class="bad">{{ printer.lastError.message }}</span>
                  <small class="cell-sub">{{ shortTime(printer.lastError.at) }}</small>
                </template>
                <span v-else class="muted">—</span>
              </td>
            </tr>
          </tbody>
        </table>

        <div class="actions agent-actions">
          <button
            class="button button-gradient"
            type="button"
            :disabled="!agent.available || agentBusy"
            @click="sendTestReceipt"
          >
            <svg><use href="#i-print" /></svg>
            <span>Agent orqali sinov cheki</span>
          </button>

          <button
            class="button button-outline"
            type="button"
            :disabled="!agent.available || agentBusy"
            @click="sendTestLabel"
          >
            <svg><use href="#i-print" /></svg>
            <span>Agent orqali sinov yorlig‘i</span>
          </button>
        </div>
      </div>

      <!-- Chop etish sinovi (brauzer orqali) -->
      <div class="table-card card-padded">
        <h3>Printerlarni sinash</h3>

        <p class="hint">
          Chop etish oynasida <strong>printerni to‘g‘ri tanlang</strong>,
          <strong>Margins (hoshiya): None</strong>,
          <strong>Scale (masshtab): 100 %</strong> bo‘lsin va
          <strong>Headers and footers</strong> o‘chirilgan bo‘lsin. Aks holda
          brauzer rasmni kichraytiradi va shtrix-kod o‘qilmaydi.
        </p>

        <div class="actions">
          <button class="button button-gradient" type="button" @click="printLabel">
            <svg><use href="#i-print" /></svg>
            <span>Sinov yorlig‘i ({{ labelWidth }}×{{ labelHeight }} mm)</span>
          </button>

          <button class="button button-outline" type="button" @click="printReceipt">
            <svg><use href="#i-print" /></svg>
            <span>Sinov cheki ({{ receiptWidth }}×{{ receiptHeight }} mm)</span>
          </button>
        </div>

        <p class="paper-note">
          Chek qog‘ozi: <strong>{{ receiptWidth }} × {{ receiptHeight }} mm</strong>.
          Shu o‘lchamdagi maxsus qog‘oz printer drayverida ham yaratilgan
          bo‘lishi kerak, aks holda Chrome o‘z qog‘ozini oladi va har chekdan
          keyin uzun bo‘sh lenta chiqadi.
          <template v-if="lastHeight">
            Oxirgi chop etilgan chek mazmuni <strong>{{ lastHeight }} mm</strong> edi —
            qog‘oz bo‘yini shundan katta qilib tanlang.
          </template>
          <template v-else>
            Bitta chek chop etilgach, bu yerda uning haqiqiy balandligi ko‘rinadi.
          </template>
        </p>

        <ul class="checklist">
          <li>Yorliqdagi chiziq chizg‘ich bilan o‘lchaganda <strong>30 mm</strong> chiqsin.</li>
          <li>Yorliq ramkasi to‘liq ko‘rinsin — chetlari kesilmasin.</li>
          <li>Chekdagi chiziq <strong>50 mm</strong> bo‘lsin.</li>
          <li>Chiqqan shtrix-kodlarni skaner o‘qiy olsin.</li>
        </ul>
      </div>

      <!-- Skaner sinovi -->
      <div class="table-card card-padded">
        <h3>Skanerni sinash</h3>

        <p class="hint">
          Quyidagi maydonni bosing va istalgan shtrix-kodni skanerlang. Skaner
          klaviatura kabi yozishi va oxirida <strong>Enter</strong> yuborishi kerak.
        </p>

        <div class="scan-box">
          <input
            ref="scanInput"
            v-model="current"
            type="text"
            autocomplete="off"
            placeholder="Shu yerga skanerlang…"
            @keydown="onKeydown"
          />
        </div>

        <table v-if="results.length" class="data-table">
          <thead>
            <tr>
              <th>Kod</th>
              <th class="num">Uzunligi</th>
              <th>Enter</th>
              <th class="num">Oraliq</th>
              <th>Bazada</th>
            </tr>
          </thead>

          <tbody>
            <tr v-for="(item, index) in results" :key="index">
              <td>
                <strong>{{ item.code }}</strong>
                <small v-if="item.nonDigits.length" class="cell-sub bad">
                  Raqam bo‘lmagan belgi: {{ item.nonDigits.join(' ') }} — klaviatura tili
                  muammosi
                </small>
              </td>

              <td class="num">{{ item.length }}</td>

              <td>
                <span class="pill" :class="item.hadEnter ? 'pill-green' : 'pill-red'">
                  {{ item.hadEnter ? 'bor' : 'yo‘q' }}
                </span>
              </td>

              <td class="num">{{ item.gapMs }} ms</td>

              <td>
                <span v-if="item.checking" class="muted">tekshirilmoqda…</span>
                <span v-else>{{ item.match }}</span>
              </td>
            </tr>
          </tbody>
        </table>

        <p v-else class="empty-state small">Hali skanerlanmadi.</p>

        <ul class="checklist">
          <li><strong>Enter</strong> ustuni «bor» bo‘lsin — aks holda kassada kod yuborilmaydi.</li>
          <li>Oraliq <strong>50 ms</strong> dan kichik bo‘lsin: sekin skaner kodni bo‘lib yuboradi.</li>
          <li>
            Klaviatura tilini <strong>RU</strong> ga o‘tkazib ham sinang — kod o‘zgarmasligi kerak.
          </li>
        </ul>
      </div>
    </div>

    <!-- === Chop etiladigan varaqlar ===
         <body> ga chiqariladi: ilova qatlami sahifani kichraytirmasin
         (izoh: assets/main.css) -->

    <Teleport to="body">
    <div v-if="sheet === 'label'" class="print-sheet">
      <div class="test-label" :style="{ width: `${labelWidth}mm`, height: `${labelHeight}mm` }">
        <span class="tiny">Sinov yorlig‘i {{ labelWidth }}×{{ labelHeight }} mm</span>

        <BarcodeImage :value="TEST_EAN13" format="EAN13" :height-mm="12" :text-mm="2.2" />

        <div class="ruler">
          <div class="ruler-line"></div>
          <span class="tiny">30 mm</span>
        </div>
      </div>
    </div>

    <div v-if="sheet === 'receipt'" class="print-sheet test-receipt">
      <strong class="size-45">4.5 mm — do‘kon nomi</strong>
      <div class="size-40">4.0 mm — JAMI summa</div>
      <div class="size-30">3.0 mm — asosiy matn, qatorlar va summalar</div>
      <div class="size-30">3.0 mm — eng kichik matn (qonun: kamida 2 mm)</div>

      <div class="ruler wide">
        <div class="ruler-line"></div>
        <span class="size-30">50 mm</span>
      </div>

      <BarcodeImage :value="TEST_RECEIPT_CODE" format="CODE128" :height-mm="15" :text-mm="3" />

      <div class="size-30">Shtrix-kodni skanerlab ko‘ring</div>
    </div>
    </Teleport>
  </section>
</template>

<style scoped>
.cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(340px, 1fr));
  gap: 12px;
  align-items: start;
}

.hint {
  margin: 0 0 12px;
  font-size: 13px;
  line-height: 1.6;
}

.agent-status {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 0 0 12px;
  font-size: 13px;
}

.agent-status .button {
  margin-left: auto;
}

.agent-actions {
  margin-top: 12px;
  margin-bottom: 0;
}

.agent-card code {
  padding: 1px 5px;
  border-radius: 4px;
  background: var(--gray-1);
  font-size: 12px;
}

.paper-note {
  margin: 0 0 12px;
  padding: 10px 12px;
  border: 1px solid var(--orange);
  border-radius: var(--radius);
  background: var(--orange-soft);
  font-size: 13px;
  line-height: 1.6;
}

.actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 12px;
}

.checklist {
  margin: 12px 0 0;
  padding-left: 18px;
  font-size: 13px;
  line-height: 1.7;
}

.scan-box input {
  width: 100%;
  height: 44px;
  padding: 0 12px;
  border: 2px solid var(--accent);
  border-radius: var(--radius);
  font-size: 16px;
}

.scan-box {
  margin-bottom: 12px;
}

.bad {
  color: var(--red);
}

.muted {
  color: var(--text-muted);
}

.empty-state.small {
  padding: 10px 0;
  font-size: 13px;
}

/* === Chop etiladigan qismlar === */

.test-label {
  box-sizing: border-box;
  padding: 1mm;
  border: 0.2mm solid #000;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: space-between;
  overflow: hidden;
  color: #000;
  font-family: 'Segoe UI', sans-serif;
}

.test-receipt {
  width: 72mm;
  margin: 0 auto;
  padding: 3mm 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2mm;
  color: #000;
  font-family: 'Segoe UI', sans-serif;
  text-align: center;
}

.tiny {
  font-size: 2mm;
  line-height: 1.1;
}

.size-30 {
  font-size: 3mm;
}

.size-40 {
  font-size: 4mm;
  font-weight: 700;
}

.size-45 {
  font-size: 4.5mm;
}

.ruler {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.5mm;
}

/* Chizg'ich: uzunligi aniq, ikki uchida belgi bor */
.ruler-line {
  width: 30mm;
  height: 1mm;
  border-left: 0.3mm solid #000;
  border-right: 0.3mm solid #000;
  border-bottom: 0.3mm solid #000;
}

.ruler.wide .ruler-line {
  width: 50mm;
}
</style>
