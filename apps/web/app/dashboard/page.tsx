import Link from 'next/link'
import { redirect } from 'next/navigation'
import type { WorkspaceListItem } from '@atlasos/types'
import { createClient } from '@/lib/supabase/server'

async function getWorkspaces(token: string): Promise<WorkspaceListItem[]> {
  const apiBase = process.env.API_URL ?? 'http://localhost:8000'
  const response = await fetch(`${apiBase}/v1/workspaces`, {
    headers: { Authorization: `Bearer ${token}` },
    cache: 'no-store',
  })
  if (!response.ok) return []
  const data = await response.json()
  return data.items ?? []
}

export default async function DashboardPage() {
  const supabase = await createClient()
  const {
    data: { session },
  } = await supabase.auth.getSession()
  if (!session) redirect('/auth/login')

  const workspaces = await getWorkspaces(session.access_token)

  return (
    <div className="min-h-screen bg-black text-white">
      <div className="max-w-5xl mx-auto px-6 py-12">
        <header className="flex items-start justify-between mb-12">
          <div>
            <p className="text-xs uppercase tracking-widest text-zinc-500 mb-2">
              AtlasOS
            </p>
            <h1 className="text-3xl font-semibold">Monitored markets</h1>
            <p className="text-zinc-400 text-sm mt-2">
              Define a market, confirm its competitors, and capture a monitoring baseline.
            </p>
          </div>
          <Link
            href="/dashboard/workspaces/new"
            className="bg-white text-black text-sm font-medium px-4 py-2 rounded-md hover:bg-zinc-200 transition"
          >
            + Create market
          </Link>
        </header>

        {workspaces.length === 0 ? (
          <EmptyState />
        ) : (
          <div className="grid gap-3">
            {workspaces.map((workspace) => (
              <Link
                key={workspace.id}
                href={`/dashboard/workspaces/${workspace.id}`}
                className="flex items-center justify-between p-5 bg-zinc-900 border border-zinc-800 rounded-lg hover:border-zinc-600 transition"
              >
                <div>
                  <p className="font-medium">{workspace.name}</p>
                  <p className="text-sm text-zinc-500 mt-1">
                    {workspace.company_name}
                    {workspace.category_label ? ` · ${workspace.category_label}` : ''}
                  </p>
                </div>
                <WorkspaceStatus status={workspace.status} />
              </Link>
            ))}
          </div>
        )}

        <div className="mt-12 pt-8 border-t border-zinc-900">
          <Link
            href="/dashboard/new"
            className="text-xs text-zinc-600 hover:text-zinc-300 transition"
          >
            Legacy one-time analysis
          </Link>
        </div>
      </div>
    </div>
  )
}

function WorkspaceStatus({ status }: { status: WorkspaceListItem['status'] }) {
  const styles = {
    draft: 'bg-zinc-800 text-zinc-400',
    discovering: 'bg-blue-950 text-blue-300',
    review: 'bg-yellow-950 text-yellow-300',
    active: 'bg-emerald-950 text-emerald-300',
    failed: 'bg-red-950 text-red-300',
  }
  const labels = {
    draft: 'Draft',
    discovering: 'Discovering',
    review: 'Needs review',
    active: 'Active',
    failed: 'Failed',
  }
  return (
    <span className={`text-xs px-2.5 py-1 rounded ${styles[status]}`}>
      {labels[status]}
    </span>
  )
}

function EmptyState() {
  return (
    <div className="border border-dashed border-zinc-800 rounded-xl py-24 text-center">
      <p className="text-zinc-300 text-sm">No monitored markets yet.</p>
      <p className="text-zinc-600 text-xs mt-2 mb-5">
        Start with your company and AtlasOS will propose the competitive set.
      </p>
      <Link
        href="/dashboard/workspaces/new"
        className="text-sm underline underline-offset-4"
      >
        Create your first market
      </Link>
    </div>
  )
}
