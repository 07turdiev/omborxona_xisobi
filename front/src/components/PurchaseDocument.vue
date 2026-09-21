<script setup lang="ts">
import { computed, ref } from 'vue'

import { formatDate, formatTime } from '@/utils/date'
import { formatMoney, formatSum, multiplyMoney } from '@/utils/money'
import { groupCell, groupLines } from '@/utils/receiving'
import type { Purchase, PurchaseLine } from '@/types'

/**
 * Ochilgan kirim hujjati.
 *
 * Qatorlar model bo'yicha guruhlanadi va kelgandagidek o'lcham × rang
 * katakchasi bo'lib ko'rsatiladi: yigirmata qatorli ro'yxatdan ko'ra
 * "qaysi o'lchamdan nechta keldi" degan savolga darhol javob beradi.
 * Shtrix-kodli to'liq ro'yxat "Batafsil" ostida turadi.
 */

const props = defineProps<{ purchase: Purchase }>()

const emit = defineEmits<{
  close: []
  edit: [purchase: Purchase]
  print: [lines: PurchaseLine[]]
  cancel: [purchase: Purchase]
}>()

const detailed = ref(false)

const groups = computed(() => groupLines(props.purchase.lines))
const confirmed = computed(() => props.purchase.status === 'confirmed')
</script>

<template>
  <div class="table-card card-padded opened" data-testid="opened-purchase">
    <div class="opened-head">
      <h3>
        {{ purchase.number }}
        <span
          class="pill"
          :class="{
            'pill-green': purchase.status === 'confirmed',
            'pill-red': purchase.status === 'cancelled',
            'pill-grey': purchase.status === 'draft',
          }"
        >
          {{ purchase.status_display }}
        </span>
      </h3>

      <button class="icon-button" type="button" aria-label="Yopish" @click="emit('close')">
        <svg><use href="#i-close" /></svg>
      </button>
    </div>

    <p class="opened-meta">
      {{ formatDate(purchase.date) }}<template v-if="purchase.created_at">,
      {{ formatTime(purchase.created_at) }}</template>
      · {{ purchase.supplier_name ?? 'Ta’minotchisiz' }} · {{ formatSum(purchase.total) }}
      <template v-if="purchase.created_by_name"> · {{ purchase.created_by_name }}</template>
    </p>

    <!-- Model bo'yicha katakcha -->
    <div v-for="group in groups" :key="group.product" class="doc-model">
      <div class="doc-model-head">
        <div>
          <strong>{{ group.name }}</strong>
          <small class="cell-sub">
            {{ group.units }} dona ·
            {{ group.cost ? `${formatMoney(group.cost)} tannarx` : 'tannarx har xil' }} ·
            {{ formatSum(group.total) }}
          </small>
        </div>

        <button
          v-if="confirmed"
          class="button button-outline"
          type="button"
          :aria-label="`${group.name}: yorliqlarni chop etish`"
          @click="emit('print', group.lines)"
        >
          <svg><use href="#i-print" /></svg>
          <span>Yorliqlar</span>
        </button>
      </div>

      <div class="doc-grid-scroll">
        <table class="doc-grid">
          <thead>
            <tr>
              <th></th>
              <th v-for="size in group.sizes" :key="String(size.id)">{{ size.name }}</th>
            </tr>
          </thead>

          <tbody>
            <tr v-for="color in group.colors" :key="String(color.id)">
              <th>{{ color.name }}</th>

              <td v-for="size in group.sizes" :key="String(size.id)">
                <span
                  class="doc-cell"
                  :class="{ empty: !groupCell(group, size.id, color.id) }"
                  :aria-label="`${size.name} ${color.name}: ${
                    groupCell(group, size.id, color.id)?.quantity ?? 0
                  } dona`"
                >
                  {{ groupCell(group, size.id, color.id)?.quantity ?? '—' }}
                </span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <button
      class="button button-outline detail-toggle"
      type="button"
      :aria-expanded="detailed"
      @click="detailed = !detailed"
    >
      Batafsil
    </button>

    <!-- To'liq ro'yxat: shtrix-kod va qator bo'yicha yorliq -->
    <div v-if="detailed" class="table-scroll">
      <table class="data-table">
        <thead>
          <tr>
            <th>Variant</th>
            <th>Shtrix-kod</th>
            <th class="num">Soni</th>
            <th class="num">Tannarx</th>
            <th class="num">Summa</th>
            <th></th>
          </tr>
        </thead>

        <tbody>
          <tr v-for="line in purchase.lines" :key="line.id ?? line.variant">
            <td>
              {{ line.product_name }}
              <small class="cell-sub">{{ line.variant_label || line.sku }}</small>
            </td>
            <td class="barcode-cell">{{ line.barcode }}</td>
            <td class="num">{{ line.quantity }}</td>
            <td class="num">{{ formatMoney(line.unit_cost) }}</td>
            <td class="num">
              {{ formatMoney(line.line_total ?? multiplyMoney(line.unit_cost, line.quantity)) }}
            </td>

            <td class="num">
              <button
                v-if="confirmed && line.barcode"
                class="icon-button"
                type="button"
                :aria-label="`${line.product_name} ${line.variant_label}: yorliqni qayta chop etish`"
                @click="emit('print', [line])"
              >
                <svg><use href="#i-print" /></svg>
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <div class="opened-actions">
      <button
        v-if="purchase.status === 'draft'"
        class="button button-gradient"
        type="button"
        @click="emit('edit', purchase)"
      >
        Qoralamani davom ettirish
      </button>

      <button
        v-if="confirmed"
        class="button button-outline"
        type="button"
        @click="emit('print', purchase.lines)"
      >
        <svg><use href="#i-print" /></svg>
        <span>Yorliqlar chop etish</span>
      </button>
    </div>

    <!-- Bekor qilish chop etishdan ataylab ajratilgan: tasodifan
         bosilmasin, oqibati esa oldindan yozilgan -->
    <div v-if="confirmed" class="danger-zone">
      <div>
        <strong>Kirimni bekor qilish</strong>
        <small>Tovar ombordan chiqariladi, hujjat tarixda qoladi.</small>
      </div>

      <button class="button button-danger" type="button" @click="emit('cancel', purchase)">
        Bekor qilish
      </button>
    </div>
  </div>
</template>

<style scoped>
.opened {
  margin-bottom: 12px;
}

.opened-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.opened-head h3 {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 0;
  font-family: var(--font-display);
  font-size: 24px;
  font-weight: 500;
}

.opened-meta {
  margin: 4px 0 12px;
  color: var(--text-muted);
  font-size: 14px;
}

.doc-model {
  margin-bottom: 12px;
  padding: 12px 14px;
  border: 1px solid var(--border);
  border-radius: var(--radius-card);
  background: var(--surface-soft);
}

.doc-model-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 10px;
}

.doc-model-head strong {
  font-size: 15px;
}

.doc-grid-scroll {
  overflow-x: auto;
}

.doc-grid {
  border-collapse: collapse;
}

.doc-grid th {
  padding: 3px 8px;
  color: var(--text-secondary);
  font-size: 13px;
  font-weight: 600;
  white-space: nowrap;
}

.doc-grid tbody th {
  text-align: right;
}

.doc-grid td {
  padding: 2px;
}

.doc-cell {
  display: grid;
  place-items: center;
  width: 56px;
  height: 34px;
  border: 1px solid var(--border);
  border-radius: var(--radius-small);
  background: var(--surface);
  font-size: 15px;
  font-variant-numeric: tabular-nums;
  font-weight: 600;
}

.doc-cell.empty {
  border-style: dashed;
  background: transparent;
  color: var(--gray-4);
  font-weight: 400;
}

.detail-toggle {
  margin-bottom: 10px;
}

.barcode-cell {
  font-variant-numeric: tabular-nums;
  color: var(--text-muted);
}

.opened-actions {
  display: flex;
  gap: 8px;
  margin-top: 12px;
}

.danger-zone {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-top: 16px;
  padding: 12px;
  border: 1px solid var(--red);
  border-radius: var(--radius);
  background: var(--red-soft);
}

.danger-zone strong {
  display: block;
  font-size: 14px;
}

.danger-zone small {
  color: var(--text-secondary);
  font-size: 13px;
}
</style>
