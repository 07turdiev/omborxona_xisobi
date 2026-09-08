import api from '@/api/client'
import type { DashboardBundle, ReportBundle } from '@/types'

export interface ReportPeriod {
  date_from?: string
  date_to?: string
  warehouse?: string | number
}

function clean(params: object) {
  return Object.fromEntries(
    Object.entries(params).filter(([, value]) => value !== '' && value != null),
  )
}

export const reportsApi = {
  async bundle(period: ReportPeriod = {}) {
    const { data } = await api.get<ReportBundle>('/reports/', { params: clean(period) })
    return data
  },

  async dashboard(period: ReportPeriod = {}) {
    const { data } = await api.get<DashboardBundle>('/reports/dashboard/', {
      params: clean(period),
    })
    return data
  },
}
