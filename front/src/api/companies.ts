import api from '@/api/client'
import type { Company, CompanyInput, CompanySummary, Paginated } from '@/types'

function clean(params: object) {
  return Object.fromEntries(
    Object.entries(params).filter(([, value]) => value !== '' && value != null),
  )
}

/**
 * Logotip bilan saqlash uchun multipart tana.
 *
 * Obyekt va `null` qiymatlar tashlab yuboriladi: `owner` kabi faqat
 * o'qiladigan maydonlar forma ichida "[object Object]" satriga aylanib
 * ketmasin. `logo` — faqat yangi tanlangan fayl, eski URL satri emas.
 */
function toFormData(payload: CompanyInput, logo: File): FormData {
  const body = new FormData()

  for (const [key, value] of Object.entries(payload)) {
    if (key === 'logo' || value === undefined || value === null || typeof value === 'object') {
      continue
    }

    body.append(key, String(value))
  }

  body.append('logo', logo)

  return body
}

export const companiesApi = {
  async list(filters: { search?: string; is_active?: string } = {}) {
    const { data } = await api.get<Paginated<Company>>('/companies/', {
      params: clean(filters),
    })
    return data
  },

  async summary() {
    const { data } = await api.get<CompanySummary>('/companies/summary/')
    return data
  },

  async save(payload: CompanyInput, id?: string, logo?: File | null) {
    const { logo: _url, ...fields } = payload
    const body = logo ? toFormData(fields, logo) : fields

    // Axios 1.x standart JSON sarlavhasini ko'rsa FormData'ni JSON'ga
    // aylantirib yuboradi — fayl bo'lsa sarlavha aniq beriladi
    const config = logo ? { headers: { 'Content-Type': 'multipart/form-data' } } : undefined

    const { data } = id
      ? await api.patch<Company>(`/companies/${id}/`, body, config)
      : await api.post<Company>('/companies/', body, config)

    return data
  },
}
