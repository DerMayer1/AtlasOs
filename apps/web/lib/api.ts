import type { Analysis, CompanyInput, Memo, PaginatedAnalyses } from '@atlasos/types'
import { createClient } from './supabase/client'

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'

async function getAuthHeader(): Promise<Record<string, string>> {
  const supabase = createClient()
  const { data } = await supabase.auth.getSession()
  const token = data.session?.access_token
  if (!token) throw new Error('Not authenticated')
  return { Authorization: `Bearer ${token}` }
}

async function apiFetch<T>(path: string, options: RequestInit = {}): Promise<T> {
  const auth = await getAuthHeader()
  const res = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: { 'Content-Type': 'application/json', ...auth, ...options.headers },
  })
  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    throw Object.assign(new Error(body?.error?.message ?? 'Request failed'), { status: res.status, code: body?.error?.code })
  }
  return res.json()
}

export const api = {
  analyses: {
    create: (input: CompanyInput) =>
      apiFetch<Analysis>('/v1/analyses', { method: 'POST', body: JSON.stringify(input) }),

    list: (params?: { limit?: number; offset?: number; status?: string }) => {
      const qs = new URLSearchParams(params as Record<string, string>).toString()
      return apiFetch<PaginatedAnalyses>(`/v1/analyses${qs ? `?${qs}` : ''}`)
    },

    get: (id: string) => apiFetch<Analysis>(`/v1/analyses/${id}`),

    delete: (id: string) =>
      apiFetch<void>(`/v1/analyses/${id}`, { method: 'DELETE' }),

    getMemo: (id: string) => apiFetch<Memo>(`/v1/analyses/${id}/memo`),

    exportMemo: async (id: string, format: 'pdf' | 'markdown') => {
      const auth = await getAuthHeader()
      const res = await fetch(`${API_BASE}/v1/analyses/${id}/memo/export`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...auth },
        body: JSON.stringify({ format }),
      })
      if (!res.ok) throw new Error('Export failed')
      return format === 'pdf' ? res.blob() : res.json()
    },
  },
}
