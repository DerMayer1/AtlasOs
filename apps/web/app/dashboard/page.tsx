import Link from 'next/link'
import { notFound } from 'next/navigation'
import { createClient } from '@/lib/supabase/server'
import type { AnalysisListItem } from '@atlasos/types'

async function getAnalyses(token: string): Promise<AnalysisListItem[]> {
  const apiBase = process.env.API_URL ?? 'http://localhost:8000'
  const res = await fetch(`${apiBase}/v1/analyses?limit=50`, {
    headers: { Authorization: `Bearer ${token}` },
    cache: 'no-store',
  })
  if (!res.ok) return []
  const data = await res.json()
  return data.items ?? []
}

export default async function DashboardPage() {
  const supabase = await createClient()
  const { data: { session } } = await supabase.auth.getSession()
  if (!session) notFound()

  const analyses = await getAnalyses(session.access_token)

  return (
    <div className="min-h-screen bg-black text-white">
      <div className="max-w-4xl mx-auto px-6 py-12">

        <div className="flex items-center justify-between mb-10">
          <div>
            <h1 className="text-3xl font-semibold">AtlasOS</h1>
            <p className="text-zinc-400 text-sm mt-1">Market intelligence</p>
          </div>
          <Link
            href="/dashboard/new"
            className="bg-white text-black text-sm font-medium px-4 py-2 rounded-md hover:bg-zinc-200 transition"
          >
            + New analysis
          </Link>
        </div>

        {analyses.length === 0 ? (
          <EmptyState />
        ) : (
          <div className="space-y-2">
            {analyses.map((a) => (
              <Link
                key={a.id}
                href={a.status === 'complete' ? `/dashboard/analyses/${a.id}` : `/dashboard/analyses/${a.id}/progress`}
                className="flex items-center justify-between p-4 bg-zinc-900 border border-zinc-800 rounded-lg hover:border-zinc-600 transition group"
              >
                <div>
                  <p className="text-sm font-medium group-hover:text-white transition">{a.company_name ?? '—'}</p>
                  <p className="text-xs text-zinc-500 mt-0.5">
                    {new Date(a.created_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}
                  </p>
                </div>
                <StatusBadge status={a.status} />
              </Link>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

function StatusBadge({ status }: { status: string }) {
  const styles = {
    complete: 'bg-zinc-800 text-zinc-300',
    running:  'bg-blue-950 text-blue-300 animate-pulse',
    pending:  'bg-zinc-800 text-zinc-500',
    failed:   'bg-red-950 text-red-300',
  }
  return (
    <span className={`text-xs px-2 py-0.5 rounded capitalize ${styles[status as keyof typeof styles] ?? styles.pending}`}>
      {status}
    </span>
  )
}

function EmptyState() {
  return (
    <div className="text-center py-24">
      <p className="text-zinc-500 text-sm mb-4">No analyses yet.</p>
      <Link
        href="/dashboard/new"
        className="text-sm text-white underline underline-offset-4 hover:text-zinc-300"
      >
        Run your first analysis →
      </Link>
    </div>
  )
}
