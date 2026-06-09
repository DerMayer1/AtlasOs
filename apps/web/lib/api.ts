import type {
  Analysis,
  CompanyInput,
  CreateAnalysisResponse,
  CreateWorkspaceInput,
  Memo,
  PaginatedAnalyses,
  SnapshotListResponse,
  Workspace,
  WorkspaceListResponse,
} from '@atlasos/types'
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
    const apiError = body?.error ?? body?.detail
    throw Object.assign(new Error(apiError?.message ?? 'Request failed'), {
      status: res.status,
      code: apiError?.code,
    })
  }
  if (res.status === 204) return undefined as T
  return res.json()
}

export const api = {
  workspaces: {
    create: (input: CreateWorkspaceInput) =>
      apiFetch<Workspace>('/v1/workspaces', {
        method: 'POST',
        body: JSON.stringify(input),
      }),

    list: () => apiFetch<WorkspaceListResponse>('/v1/workspaces'),

    get: (id: string) => apiFetch<Workspace>(`/v1/workspaces/${id}`),

    discover: (id: string) =>
      apiFetch<{ id: string; status: 'discovering' }>(
        `/v1/workspaces/${id}/discover`,
        { method: 'POST' },
      ),

    confirmCompanies: (id: string, companyIds: string[]) =>
      apiFetch<Workspace>(`/v1/workspaces/${id}/companies`, {
        method: 'PUT',
        body: JSON.stringify({ company_ids: companyIds }),
      }),

    captureSnapshots: (id: string) =>
      apiFetch<{ id: string; status: 'pending' }>(
        `/v1/workspaces/${id}/snapshots`,
        { method: 'POST' },
      ),

    listSnapshots: (id: string, companyId?: string) => {
      const query = companyId
        ? `?company_id=${encodeURIComponent(companyId)}`
        : ''
      return apiFetch<SnapshotListResponse>(
        `/v1/workspaces/${id}/snapshots${query}`,
      )
    },

    delete: (id: string) =>
      apiFetch<void>(`/v1/workspaces/${id}`, { method: 'DELETE' }),
  },

  analyses: {
    create: (input: CompanyInput) =>
      apiFetch<CreateAnalysisResponse>('/v1/analyses', {
        method: 'POST',
        body: JSON.stringify(input),
      }),

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
