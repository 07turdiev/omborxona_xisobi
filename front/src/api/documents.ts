import api, { downloadFile } from '@/api/client'
import type {
  Document,
  DocumentKind,
  DocumentLineInput,
  DocumentSummary,
  Paginated,
  Partner,
} from '@/types'

export interface DocumentFilters {
  kind?: DocumentKind
  status?: string
  warehouse?: string | number
  partner?: string | number
  search?: string
  date_from?: string
  date_to?: string
}

export interface DocumentInput {
  kind: DocumentKind
  date: string
  warehouse: number | null
  partner: number | null
  currency?: string
  external_number?: string
  note?: string
  payment_method?: string
  is_credit?: boolean
  credit_markup_percent?: string
  due_date?: string | null
  customer_name?: string
  customer_phone?: string
  customer_document?: string
  items: DocumentLineInput[]
}

function clean(filters: object) {
  return Object.fromEntries(
    Object.entries(filters).filter(([, value]) => value !== '' && value != null),
  )
}

export const documentsApi = {
  async list(filters: DocumentFilters = {}) {
    const { data } = await api.get<Paginated<Document>>('/documents/', {
      params: clean(filters),
    })
    return data
  },

  async get(id: number) {
    const { data } = await api.get<Document>(`/documents/${id}/`)
    return data
  },

  async create(payload: DocumentInput) {
    const { data } = await api.post<Document>('/documents/', payload)
    return data
  },

  async update(id: number, payload: Partial<DocumentInput>) {
    const { data } = await api.patch<Document>(`/documents/${id}/`, payload)
    return data
  },

  async remove(id: number) {
    await api.delete(`/documents/${id}/`)
  },

  async confirm(id: number) {
    const { data } = await api.post<Document>(`/documents/${id}/confirm/`)
    return data
  },

  async cancel(id: number, note = '') {
    const { data } = await api.post<Document>(`/documents/${id}/cancel/`, { note })
    return data
  },

  async summary(filters: DocumentFilters = {}) {
    const { data } = await api.get<DocumentSummary>('/documents/summary/', {
      params: clean(filters),
    })
    return data
  },

  /** Hujjatlar va ularning qatorlarini Excel'ga chiqaradi. */
  exportExcel(filters: DocumentFilters = {}) {
    return downloadFile('/documents/export/', clean(filters), 'hujjatlar.xlsx')
  },
}

export const partnersApi = {
  async list(params: { search?: string; role?: string } = {}) {
    const { data } = await api.get<Paginated<Partner>>('/partners/', {
      params: clean(params),
    })
    return data
  },

  async create(payload: Partial<Partner>) {
    const { data } = await api.post<Partner>('/partners/', payload)
    return data
  },

  async update(id: number, payload: Partial<Partner>) {
    const { data } = await api.patch<Partner>(`/partners/${id}/`, payload)
    return data
  },

  async remove(id: number) {
    await api.delete(`/partners/${id}/`)
  },
}
