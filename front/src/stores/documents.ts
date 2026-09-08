import { computed, ref } from 'vue'
import { defineStore } from 'pinia'

import {
  documentsApi,
  partnersApi,
  type DocumentFilters,
  type DocumentInput,
} from '@/api/documents'
import type { Document, DocumentKind, DocumentSummary, Partner } from '@/types'

export const useDocumentStore = defineStore('documents', () => {
  const items = ref<Document[]>([])
  const partners = ref<Partner[]>([])
  const summary = ref<DocumentSummary | null>(null)

  const loading = ref(false)
  const saving = ref(false)
  const error = ref('')

  const filters = ref<DocumentFilters>({
    kind: undefined,
    status: '',
    warehouse: '',
    search: '',
  })

  const isEmpty = computed(() => !loading.value && items.value.length === 0)

  const suppliers = computed(() => partners.value.filter((p) => p.is_supplier))
  const customers = computed(() => partners.value.filter((p) => p.is_customer))

  async function load(kind: DocumentKind) {
    loading.value = true
    error.value = ''

    try {
      const query = { ...filters.value, kind }
      const [list, totals] = await Promise.all([
        documentsApi.list(query),
        documentsApi.summary(query),
      ])

      items.value = list.results
      summary.value = totals
    } catch {
      error.value = 'Hujjatlarni olishda xatolik.'
    } finally {
      loading.value = false
    }
  }

  async function loadPartners() {
    if (partners.value.length) return
    partners.value = (await partnersApi.list()).results
  }

  /** Xatolarni forma maydonlariga bog'lanadigan ko'rinishda qaytaradi. */
  function asErrors(err: unknown): Record<string, string[]> {
    const response = (err as { response?: { data?: unknown } }).response
    const data = response?.data

    if (Array.isArray(data)) return { detail: data.map(String) }
    if (data && typeof data === 'object') return data as Record<string, string[]>

    return { detail: ['Kutilmagan xatolik.'] }
  }

  async function save(payload: DocumentInput, id?: number) {
    saving.value = true

    try {
      const document = id
        ? await documentsApi.update(id, payload)
        : await documentsApi.create(payload)

      await load(payload.kind)
      return { ok: true as const, document, errors: {} }
    } catch (err) {
      return { ok: false as const, document: null, errors: asErrors(err) }
    } finally {
      saving.value = false
    }
  }

  async function confirm(document: Document) {
    saving.value = true

    try {
      await documentsApi.confirm(document.id)
      await load(document.kind)
      return { ok: true as const, errors: {} }
    } catch (err) {
      return { ok: false as const, errors: asErrors(err) }
    } finally {
      saving.value = false
    }
  }

  async function cancel(document: Document, note = '') {
    saving.value = true

    try {
      await documentsApi.cancel(document.id, note)
      await load(document.kind)
      return { ok: true as const, errors: {} }
    } catch (err) {
      return { ok: false as const, errors: asErrors(err) }
    } finally {
      saving.value = false
    }
  }

  async function remove(document: Document) {
    await documentsApi.remove(document.id)
    await load(document.kind)
  }

  return {
    items, partners, summary, loading, saving, error, filters, isEmpty,
    suppliers, customers,
    load, loadPartners, save, confirm, cancel, remove,
  }
})
