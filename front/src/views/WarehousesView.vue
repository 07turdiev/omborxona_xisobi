<script setup lang="ts">
import { onMounted, ref } from 'vue'

import WarehouseModal from '@/components/WarehouseModal.vue'
import { useWarehouseStore } from '@/stores/warehouses'
import type { Warehouse } from '@/types'

const store = useWarehouseStore()

const modalOpen = ref(false)
const editing = ref<Warehouse | null>(null)

onMounted(() => {
  store.loadChoices()
  store.load()
})

let searchTimer: ReturnType<typeof setTimeout> | undefined

function onSearchInput() {
  clearTimeout(searchTimer)
  searchTimer = setTimeout(() => store.load(), 300)
}

function openCreate() {
  editing.value = null
  modalOpen.value = true
}

function openEdit(warehouse: Warehouse) {
  editing.value = warehouse
  modalOpen.value = true
}

async function onDelete(warehouse: Warehouse) {
  const ok = window.confirm(
    `"${warehouse.name}" omborini o‘chirasizmi? Bu amalni qaytarib bo‘lmaydi.`,
  )

  if (ok) await store.remove(warehouse.id)
}

function formatNumber(value: string | null): string {
  if (!value) return '—'
  return new Intl.NumberFormat('uz-UZ').format(Number(value))
}
</script>

<template>
  <section class="app-section active">
    <div class="section-toolbar">
      <div class="filters">
        <div class="search-field">
          <svg><use href="#i-search" /></svg>

          <input
            v-model="store.filters.search"
            type="search"
            placeholder="Ombor nomi, kodi yoki manzili..."
            @input="onSearchInput"
          />
        </div>

        <select v-model="store.filters.goods_type" @change="store.load()">
          <option value="">Barcha turlar</option>
          <option
            v-for="choice in store.choices?.goods_types ?? []"
            :key="choice.value"
            :value="choice.value"
          >
            {{ choice.label }}
          </option>
        </select>

        <select v-model="store.filters.purpose" @change="store.load()">
          <option value="">Barcha vazifalar</option>
          <option
            v-for="choice in store.choices?.purposes ?? []"
            :key="choice.value"
            :value="choice.value"
          >
            {{ choice.label }}
          </option>
        </select>
      </div>

      <button class="button button-gradient warehouse-gradient" @click="openCreate">
        <svg><use href="#i-plus" /></svg>
        <span>Ombor qo‘shish</span>
      </button>
    </div>

    <p v-if="store.error" class="load-error">{{ store.error }}</p>

    <div class="warehouse-cards">
      <article
        v-for="warehouse in store.items"
        :key="warehouse.id"
        class="warehouse-card"
      >
        <div class="warehouse-card-header">
          <div class="warehouse-card-icon">
            <svg><use href="#i-warehouse" /></svg>
          </div>

          <span class="warehouse-code">{{ warehouse.code }}</span>
        </div>

        <h3>{{ warehouse.name }}</h3>
        <p>{{ warehouse.address || '—' }}</p>

        <div class="warehouse-card-metrics">
          <div>
            <span>Vazifasi</span>
            <strong>{{ warehouse.purpose_display }}</strong>
          </div>

          <div>
            <span>Sig‘imi</span>
            <strong>{{ formatNumber(warehouse.capacity) }}</strong>
          </div>
        </div>
      </article>
    </div>

    <div class="table-card">
      <div class="table-scroll">
        <table class="data-table">
          <thead>
            <tr>
              <th>Ombor</th>
              <th>Tovar turi</th>
              <th>Vazifasi</th>
              <th>Mas’ul</th>
              <th>Manzil</th>
              <th>Maydoni</th>
              <th>Sig‘imi</th>
              <th>Holat</th>
              <th></th>
            </tr>
          </thead>

          <tbody>
            <tr v-if="store.loading">
              <td colspan="9" class="empty-state">Yuklanmoqda…</td>
            </tr>

            <tr v-else-if="store.isEmpty">
              <td colspan="9" class="empty-state">
                Ombor topilmadi. «Ombor qo‘shish» tugmasi bilan birinchisini yarating.
              </td>
            </tr>

            <tr v-for="warehouse in store.items" v-else :key="warehouse.id">
              <td>
                <strong>{{ warehouse.name }}</strong>
                <small class="cell-sub">{{ warehouse.code }}</small>
              </td>

              <td>{{ warehouse.goods_type_display }}</td>

              <td>
                <span class="pill" :class="`pill-${warehouse.purpose}`">
                  {{ warehouse.purpose_display }}
                </span>
              </td>

              <td>{{ warehouse.manager || '—' }}</td>
              <td>{{ warehouse.address || '—' }}</td>
              <td>{{ formatNumber(warehouse.area) }}</td>
              <td>{{ formatNumber(warehouse.capacity) }}</td>

              <td>
                <span class="pill" :class="warehouse.is_active ? 'pill-on' : 'pill-off'">
                  {{ warehouse.is_active ? 'Faol' : 'Faol emas' }}
                </span>
              </td>

              <td class="row-actions">
                <button class="button button-soft" type="button" @click="openEdit(warehouse)">
                  Tahrirlash
                </button>

                <button class="button button-danger" type="button" @click="onDelete(warehouse)">
                  <svg><use href="#i-trash" /></svg>
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <WarehouseModal
      :show="modalOpen"
      :warehouse="editing"
      @close="modalOpen = false"
      @saved="store.load()"
    />
  </section>
</template>

<style scoped>
/* Quyidagi sinflar dizaynda yo'q edi — ranglar app.css o'zgaruvchilaridan. */

.pill-main {
  background: var(--accent-soft);
  color: var(--accent);
}

.pill-retail {
  background: var(--teal-soft);
  color: var(--teal);
}

.pill-transit {
  background: var(--orange-soft);
  color: var(--orange);
}

</style>
