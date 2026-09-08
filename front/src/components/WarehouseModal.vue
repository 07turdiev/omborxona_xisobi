<script setup lang="ts">
import { reactive, ref, watch } from 'vue'

import { useWarehouseStore } from '@/stores/warehouses'
import type { Warehouse, WarehouseInput } from '@/types'

const props = defineProps<{ show: boolean; warehouse: Warehouse | null }>()
const emit = defineEmits<{ close: []; saved: [] }>()

const store = useWarehouseStore()

const errors = ref<Record<string, string[]>>({})

function emptyForm(): Partial<WarehouseInput> {
  return {
    name: '',
    code: '',
    goods_type: 'universal',
    purpose: 'main',
    manager: '',
    phone: '',
    address: '',
    area: null,
    capacity: null,
    temperature: '',
    notes: '',
    is_active: true,
  }
}

const form = reactive<Partial<WarehouseInput>>(emptyForm())

watch(
  () => [props.show, props.warehouse] as const,
  ([show, warehouse]) => {
    if (!show) return

    errors.value = {}
    Object.assign(form, emptyForm())

    if (warehouse) {
      Object.assign(form, {
        name: warehouse.name,
        code: warehouse.code,
        goods_type: warehouse.goods_type,
        purpose: warehouse.purpose,
        manager: warehouse.manager,
        phone: warehouse.phone,
        address: warehouse.address,
        area: warehouse.area,
        capacity: warehouse.capacity,
        temperature: warehouse.temperature,
        notes: warehouse.notes,
        is_active: warehouse.is_active,
      })
    }
  },
  { immediate: true },
)

async function onSubmit() {
  // Bo'sh son maydonlari `null` bo'lib ketsin — '' Decimal uchun xato
  const payload: Partial<WarehouseInput> = {
    ...form,
    area: form.area || null,
    capacity: form.capacity || null,
  }

  const result = await store.save(payload, props.warehouse?.id)

  if (result.ok) {
    emit('saved')
    emit('close')
    return
  }

  errors.value = result.errors
}

/** Serverdan kelgan xatoni maydon ostida ko'rsatish uchun. */
function fieldError(field: string): string {
  return errors.value[field]?.[0] ?? ''
}
</script>

<template>
  <div class="modal" :class="{ show }">
    <div class="modal-backdrop" @click="emit('close')"></div>

    <div class="modal-dialog modal-large">
      <div class="modal-header">
        <div>
          <span class="modal-eyebrow">OMBOR</span>
          <h3>{{ warehouse ? 'Omborni tahrirlash' : 'Ombor qo‘shish' }}</h3>
          <p>Ombor haqidagi ma’lumotlarni kiriting.</p>
        </div>

        <button class="modal-close" type="button" @click="emit('close')">
          <svg><use href="#i-close" /></svg>
        </button>
      </div>

      <form @submit.prevent="onSubmit">
        <div class="modal-body">
          <p v-if="fieldError('detail') || fieldError('non_field_errors')" class="form-error">
            {{ fieldError('detail') || fieldError('non_field_errors') }}
          </p>

          <div class="form-grid three">
            <div class="field span-2">
              <label>Ombor nomi</label>
              <input v-model="form.name" required />
              <small v-if="fieldError('name')" class="field-error">
                {{ fieldError('name') }}
              </small>
            </div>

            <div class="field">
              <label>Ombor kodi</label>
              <input v-model="form.code" required placeholder="MARKAZ" />
              <small v-if="fieldError('code')" class="field-error">
                {{ fieldError('code') }}
              </small>
            </div>

            <div class="field">
              <label>Tovar turi</label>
              <select v-model="form.goods_type">
                <option
                  v-for="choice in store.choices?.goods_types ?? []"
                  :key="choice.value"
                  :value="choice.value"
                >
                  {{ choice.label }}
                </option>
              </select>
            </div>

            <div class="field">
              <label>Vazifasi</label>
              <select v-model="form.purpose">
                <option
                  v-for="choice in store.choices?.purposes ?? []"
                  :key="choice.value"
                  :value="choice.value"
                >
                  {{ choice.label }}
                </option>
              </select>
              <small class="field-hint">Tranzit ombordagi tovar sotuvga chiqmaydi</small>
            </div>

            <div class="field">
              <label>Mas’ul shaxs</label>
              <input v-model="form.manager" />
            </div>

            <div class="field span-2">
              <label>Manzil</label>
              <input v-model="form.address" />
            </div>

            <div class="field">
              <label>Telefon</label>
              <input v-model="form.phone" />
            </div>

            <div class="field">
              <label>Maydoni, m²</label>
              <input v-model="form.area" type="number" step="0.001" min="0" />
              <small v-if="fieldError('area')" class="field-error">
                {{ fieldError('area') }}
              </small>
            </div>

            <div class="field">
              <label>Sig‘imi</label>
              <input v-model="form.capacity" type="number" step="0.001" min="0" />
            </div>

            <div class="field">
              <label>Harorat rejimi</label>
              <input v-model="form.temperature" placeholder="+10°C / +25°C" />
            </div>

            <div class="field full">
              <label>Izoh</label>
              <textarea v-model="form.notes" rows="2"></textarea>
            </div>

            <div class="field">
              <label>Holati</label>
              <select v-model="form.is_active">
                <option :value="true">Faol</option>
                <option :value="false">Faol emas</option>
              </select>
            </div>
          </div>
        </div>

        <div class="modal-footer">
          <button class="button button-outline" type="button" @click="emit('close')">
            Bekor qilish
          </button>

          <button
            class="button button-gradient warehouse-gradient"
            type="submit"
            :disabled="store.saving"
          >
            {{ store.saving ? 'Saqlanmoqda…' : 'Saqlash' }}
          </button>
        </div>
      </form>
    </div>
  </div>
</template>

<style scoped>
/* Dizaynda maydon xatolari uchun sinf yo'q — qo'shamiz, uslub o'sha yerdagi
   rang o'zgaruvchilaridan olinadi. */
.field-error {
  margin-top: 4px;
  color: var(--red);
  font-size: 7px;
}

.field-hint {
  margin-top: 4px;
  color: var(--text-muted);
  font-size: 7px;
}

.form-error {
  margin-bottom: 12px;
  padding: 10px 12px;
  border-radius: var(--radius-small);
  background: var(--red-soft);
  color: var(--red);
  font-size: 8px;
}
</style>
