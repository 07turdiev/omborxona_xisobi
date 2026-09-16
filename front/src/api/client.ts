import axios, { AxiosError, type AxiosInstance, type InternalAxiosRequestConfig } from 'axios'

const ACCESS_KEY = 'access_token'
const REFRESH_KEY = 'refresh_token'

export const tokenStorage = {
  get access(): string | null {
    try {
      return localStorage.getItem(ACCESS_KEY)
    } catch {
      return null
    }
  },
  get refresh(): string | null {
    try {
      return localStorage.getItem(REFRESH_KEY)
    } catch {
      return null
    }
  },
  set(access: string, refresh?: string) {
    try {
      localStorage.setItem(ACCESS_KEY, access)
      if (refresh) localStorage.setItem(REFRESH_KEY, refresh)
    } catch {
      // Shaxsiy oynada saqlash yopiq bo'lishi mumkin
    }
  },
  clear() {
    try {
      localStorage.removeItem(ACCESS_KEY)
      localStorage.removeItem(REFRESH_KEY)
    } catch {
      // e'tiborsiz
    }
  },
}

const api: AxiosInstance = axios.create({
  baseURL: '/api',
  headers: { 'Content-Type': 'application/json' },
})

api.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  const token = tokenStorage.access

  if (token) config.headers.Authorization = `Bearer ${token}`

  return config
})

/** Bir vaqtda kelgan 401 larda token bir marta yangilanadi. */
let refreshing: Promise<string> | null = null

api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const original = error.config as InternalAxiosRequestConfig & { _retried?: boolean }
    const refresh = tokenStorage.refresh

    if (error.response?.status !== 401 || !refresh || original?._retried) {
      return Promise.reject(error)
    }

    original._retried = true

    try {
      refreshing ??= axios
        .post<{ access: string }>('/api/auth/refresh/', { refresh })
        .then((response) => {
          tokenStorage.set(response.data.access)
          return response.data.access
        })
        .finally(() => {
          refreshing = null
        })

      const access = await refreshing
      original.headers.Authorization = `Bearer ${access}`

      return api(original)
    } catch {
      tokenStorage.clear()
      window.location.href = '/login'

      return Promise.reject(error)
    }
  },
)

/**
 * Faylni yuklab oladi (Excel eksport).
 *
 * Oddiy havola ishlamaydi: `Authorization` sarlavhasi `<a href>` da
 * yuborilmaydi. Shuning uchun fayl `blob` sifatida olinadi.
 */
export async function downloadFile(url: string, params: Record<string, unknown> = {}) {
  const response = await api.get<Blob>(url, { params, responseType: 'blob' })

  const disposition = String(response.headers['content-disposition'] ?? '')
  const encoded = /filename\*=UTF-8''([^;]+)/i.exec(disposition)?.[1]
  const plain = /filename="?([^";]+)"?/i.exec(disposition)?.[1]

  let name = 'hisobot.xlsx'

  if (encoded) {
    try {
      name = decodeURIComponent(encoded)
    } catch {
      name = encoded
    }
  } else if (plain) {
    name = plain
  }

  const href = URL.createObjectURL(response.data)
  const link = document.createElement('a')

  link.href = href
  link.download = name
  document.body.appendChild(link)
  link.click()
  link.remove()

  setTimeout(() => URL.revokeObjectURL(href), 10_000)
}

/** Server xatosini foydalanuvchiga ko'rsatiladigan matnga aylantiradi. */
export function errorMessage(error: unknown, fallback = 'Xatolik yuz berdi.'): string {
  const data = (error as AxiosError<Record<string, unknown>>)?.response?.data

  if (!data) return fallback

  const detail = data.detail

  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) return detail.join(' ')

  const first = Object.values(data).flat()[0]

  return typeof first === 'string' ? first : fallback
}

export default api
