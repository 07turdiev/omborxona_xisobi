import api, { downloadFile } from '@/api/client'

export type ImportType = 'categories' | 'products' | 'purchases' | 'sales'

export interface ImportRow {
  row: number
  values: Record<string, string>
  errors: string[]
  warnings: string[]
  action: 'create' | 'update' | 'skip' | 'error'
}

export interface ImportDuplicate {
  imported_at: string
  user_name: string
  object_repr: string
}

export interface ImportPreview {
  type: ImportType
  title: string
  file_name: string
  sheet: string
  header_row: number
  columns: { key: string; label: string; required: boolean }[]
  missing_columns: string[]
  unknown_columns: string[]
  hidden_columns: string[]
  total: number
  valid: number
  invalid: number
  with_warnings: number
  summary: { create: number; update: number; skip: number; documents: number }
  duplicate: ImportDuplicate | null
  can_commit: boolean
  rows: ImportRow[]
}

export interface ImportResult {
  type: ImportType
  confirmed: boolean
  created: number
  updated: number
  documents?: { id: number; number: string; status: string; lines: number }[]
}

function form(file: File, options: Record<string, boolean> = {}) {
  const data = new FormData()
  data.append('file', file)

  for (const [key, value] of Object.entries(options)) {
    data.append(key, value ? 'true' : 'false')
  }

  return data
}

// Axios 1.x standart JSON sarlavhasi bilan FormData'ni JSON'ga aylantiradi
const multipart = { headers: { 'Content-Type': 'multipart/form-data' } }

export const importsApi = {
  template(type: ImportType) {
    return downloadFile(`/import/${type}/template/`, {}, `import-${type}.xlsx`)
  },

  async preview(type: ImportType, file: File, confirm = true) {
    const { data } = await api.post<ImportPreview>(
      `/import/${type}/preview/`,
      form(file, { confirm }),
      multipart,
    )
    return data
  },

  async commit(type: ImportType, file: File, options: { confirm: boolean; allowDuplicate: boolean }) {
    const { data } = await api.post<ImportResult>(
      `/import/${type}/commit/`,
      form(file, { confirm: options.confirm, allow_duplicate: options.allowDuplicate }),
      multipart,
    )
    return data
  },
}
