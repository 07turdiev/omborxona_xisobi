<script setup lang="ts">
import { reactive, ref, watch } from 'vue'

import { catalogApi } from '@/api/catalog'
import { useCatalogStore } from '@/stores/catalog'
import type { AttributeDefinition, Product, ProductInput } from '@/types'

const props = defineProps<{ show: boolean; product: Product | null }>()
const emit = defineEmits<{ close: []; saved: [] }>()

const store = useCatalogStore()

const errors = ref<Record<string, string[]>>({})
const definitions = ref<AttributeDefinition[]>([])
const loadingAttributes = ref(false)

/** Atribut qiymatlari — xom holicha (`{"qalinlik": "12 mm"}`). */
const attributeValues = reactive<Record<string, string | boolean>>({})

function emptyForm(): ProductInput {
  return {
    name: '',
    category: undefined,
    brand: '',
    model: '',
    base_unit: '',
    description: '',
    is_active: true,
    sku: '',
  }
}

const form = reactive<ProductInput>(emptyForm())

/** Kategoriya almashganda maydonlar ham almashadi — jonli meros shu yerda ko'rinadi. */
async function loadAttributes(categoryId: number | undefined) {
  Object.keys(attributeValues).forEach((key) => delete attributeValues[key])

  if (!categoryId) {
    definitions.value = []
    return
  }

  loadingAttributes.value = true

  try {
    definitions.value = await store.attributesFor(categoryId)

    const existing = props.product?.variants?.[0]?.attributes ?? {}

    for (const definition of definitions.value) {
      const current = existing[definition.key]

      attributeValues[definition.key] =
        current != null
          ? (current as string | boolean)
          : definition.value_type === 'boolean'
            ? false
            : definition.default_value
    }
  } finally {
    loadingAttributes.value = false
  }
}

watch(
  () => [props.show, props.product] as const,
  async ([show, product]) => {
    if (!show) return

    errors.value = {}
    Object.assign(form, emptyForm())

    if (product) {
      Object.assign(form, {
        name: product.name,
        category: product.category,
        brand: product.brand,
        model: product.model,
        base_unit: product.base_unit,
        description: product.description,
        is_active: product.is_active,
      })
    }

    await loadAttributes(form.category)
  },
  { immediate: true },
)

// Kategoriya o'zgarsa — atribut maydonlarini qayta yuklaymiz
watch(
  () => form.category,
  (categoryId) => {
    if (props.show) loadAttributes(categoryId as number | undefined)
  },
)

async function onSubmit() {
  errors.value = {}

  const result = await store.saveProduct(form, props.product?.id)

  if (!result.ok) {
    errors.value = result.errors
    return
  }

  // Atributlar variantda saqlanadi. Yangi mahsulotda variant serverda
  // avtomatik yaratilgani uchun uni ro'yxatdan topib olamiz.
  const target =
    props.product ??
    store.products.find((item) => item.name === form.name && item.category === form.category)

  const variant = target?.variants?.[0]

  if (variant && definitions.value.length) {
    const attributeResult = await store.saveVariantAttributes(variant.id, {
      ...attributeValues,
    })

    if (!attributeResult.ok) {
      errors.value = attributeResult.errors
      return
    }
  }

  emit('saved')
  emit('close')
}

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
          <span class="modal-eyebrow">MAHSULOT</span>
          <h3>{{ product ? 'Mahsulotni tahrirlash' : 'Mahsulot qo‘shish' }}</h3>
          <p>Kategoriyani tanlang — atribut maydonlari shunga qarab o‘zgaradi.</p>
        </div>

        <button class="modal-close" type="button" @click="emit('close')">
          <svg><use href="#i-close" /></svg>
        </button>
      </div>

      <form @submit.prevent="onSubmit">
        <div class="modal-body">
          <div class="form-grid three">
            <div class="field span-2">
              <label>Nomi</label>
              <input v-model="form.name" required />
              <small v-if="fieldError('name')" class="field-error">
                {{ fieldError('name') }}
              </small>
            </div>

            <div class="field">
              <label>Kategoriya</label>
              <select v-model="form.category" required>
                <option :value="undefined" disabled>Tanlang…</option>
                <option
                  v-for="option in store.categoryOptions"
                  :key="option.id"
                  :value="option.id"
                >
                  {{ option.label }}
                </option>
              </select>
              <small v-if="fieldError('category')" class="field-error">
                {{ fieldError('category') }}
              </small>
            </div>

            <div class="field">
              <label>Brend</label>
              <input v-model="form.brand" />
            </div>

            <div class="field">
              <label>Model</label>
              <input v-model="form.model" />
            </div>

            <div class="field">
              <label>Asosiy birlik</label>
              <input v-model="form.base_unit" placeholder="kg, dona, m2" />
              <small class="field-hint">Bo‘sh qoldirilsa kategoriyadan olinadi</small>
            </div>

            <div v-if="!product" class="field">
              <label>SKU</label>
              <input v-model="form.sku" placeholder="CEM-M400" />
              <small class="field-hint">Bo‘sh qoldirilsa avtomatik beriladi</small>
            </div>

            <div class="field">
              <label>Holati</label>
              <select v-model="form.is_active">
                <option :value="true">Faol</option>
                <option :value="false">Faol emas</option>
              </select>
            </div>
          </div>

          <!-- Kategoriyaga bog'liq atributlar -->
          <div v-if="form.category" class="attribute-block">
            <h4>
              Atributlar
              <small v-if="loadingAttributes">yuklanmoqda…</small>
            </h4>

            <p v-if="!loadingAttributes && !definitions.length" class="field-hint">
              Bu kategoriyada atribut ta’riflanmagan.
            </p>

            <div v-else class="form-grid three">
              <div v-for="definition in definitions" :key="definition.key" class="field">
                <label>
                  {{ definition.name }}
                  <span v-if="definition.unit" class="unit-tag">{{ definition.unit }}</span>
                  <span v-if="definition.is_required" class="required-mark">*</span>
                </label>

                <select
                  v-if="definition.value_type === 'choice'"
                  v-model="attributeValues[definition.key]"
                >
                  <option value="">—</option>
                  <option v-for="choice in definition.choices" :key="choice" :value="choice">
                    {{ choice }}
                  </option>
                </select>

                <select
                  v-else-if="definition.value_type === 'boolean'"
                  v-model="attributeValues[definition.key]"
                >
                  <option :value="false">Yo‘q</option>
                  <option :value="true">Ha</option>
                </select>

                <input
                  v-else
                  v-model="attributeValues[definition.key]"
                  :placeholder="definition.unit ? `12 ${definition.unit}` : ''"
                />

                <small v-if="fieldError(definition.key)" class="field-error">
                  {{ fieldError(definition.key) }}
                </small>
              </div>
            </div>
          </div>
        </div>

        <div class="modal-footer">
          <button class="button button-outline" type="button" @click="emit('close')">
            Bekor qilish
          </button>

          <button class="button button-gradient" type="submit" :disabled="store.saving">
            {{ store.saving ? 'Saqlanmoqda…' : 'Saqlash' }}
          </button>
        </div>
      </form>
    </div>
  </div>
</template>

<style scoped>
.attribute-block {
  margin-top: 18px;
  padding-top: 16px;
  border-top: 1px solid var(--border);
}

.attribute-block h4 {
  margin-bottom: 12px;
  font-size: 9px;
  color: var(--text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.06em;
}

.attribute-block h4 small {
  margin-left: 6px;
  color: var(--text-muted);
  text-transform: none;
  letter-spacing: 0;
}

.unit-tag {
  margin-left: 4px;
  padding: 1px 5px;
  border-radius: 4px;
  background: var(--surface-hover);
  color: var(--text-muted);
  font-size: 6px;
}

.required-mark {
  margin-left: 2px;
  color: var(--red);
}

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
</style>
