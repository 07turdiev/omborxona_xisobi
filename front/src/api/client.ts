import axios, {
  AxiosError,
  type AxiosInstance,
  type InternalAxiosRequestConfig,
} from 'axios'

const ACCESS_KEY = 'access_token'
const REFRESH_KEY = 'refresh_token'
const TENANT_KEY = 'active_tenant'

/**
 * Tanlangan tashkilot.
 *
 * Foydalanuvchi bir nechta do'konda ishlashi mumkin. Server `X-Tenant-Id`
 * sarlavhasini ko'rsa o'shani ishlatadi, aks holda birinchi a'zolikni
 * oladi. Tanlov brauzerda saqlanadi — sahifa yangilanganda ham qoladi.
 *
 * A'zoligi yo'q tashkilot ID si yuborilsa server hech narsa qaytarmaydi
 * (fail-closed), ya'ni bu sarlavha ruxsat bermaydi — u faqat tanlov.
 */
export const tenantStorage = {
  get id(): string | null {
    try {
      return localStorage.getItem(TENANT_KEY)
    } catch {
      return null
    }
  },
  set(id: string) {
    try {
      localStorage.setItem(TENANT_KEY, id)
    } catch {
      // Shaxsiy oynada localStorage yopiq bo'lishi mumkin
    }
  },
  clear() {
    try {
      localStorage.removeItem(TENANT_KEY)
    } catch {
      // e'tiborsiz
    }
  },
}

export const tokenStorage = {
  get access() {
    return localStorage.getItem(ACCESS_KEY)
  },
  get refresh() {
    return localStorage.getItem(REFRESH_KEY)
  },
  set(access: string, refresh?: string) {
    localStorage.setItem(ACCESS_KEY, access)
    if (refresh) localStorage.setItem(REFRESH_KEY, refresh)
  },
  clear() {
    localStorage.removeItem(ACCESS_KEY)
    localStorage.removeItem(REFRESH_KEY)
  },
}

const api: AxiosInstance = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL ?? '/api',
  headers: { 'Content-Type': 'application/json' },
})

api.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  const token = tokenStorage.access
  if (token) config.headers.Authorization = `Bearer ${token}`

  const tenant = tenantStorage.id
  if (tenant) config.headers['X-Tenant-Id'] = tenant

  return config
})

/** 401 kelganda refresh token bilan bir marta qayta urinamiz. */
let refreshing: Promise<string> | null = null

api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const original = error.config as InternalAxiosRequestConfig & { _retried?: boolean }

    if (error.response?.status !== 401 || original?._retried || !tokenStorage.refresh) {
      return Promise.reject(error)
    }

    original._retried = true

    try {
      refreshing ??= axios
        .post<{ access: string }>(`${api.defaults.baseURL}/auth/refresh/`, {
          refresh: tokenStorage.refresh,
        })
        .then((res) => {
          tokenStorage.set(res.data.access)
          return res.data.access
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

export default api
