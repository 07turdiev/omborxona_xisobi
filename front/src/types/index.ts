export interface User {
  id: number
  username: string
  email: string
  first_name: string
  last_name: string
  role: 'admin' | 'manager' | 'storekeeper'
  phone: string
}

export interface TokenPair {
  access: string
  refresh: string
}

/** DRF PageNumberPagination javobi */
export interface Paginated<T> {
  count: number
  next: string | null
  previous: string | null
  results: T[]
}
