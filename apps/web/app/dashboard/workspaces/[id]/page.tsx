'use client'

import { useCallback, useEffect, useMemo, useState } from 'react'
import Link from 'next/link'
import { useParams } from 'next/navigation'
import type { Workspace } from '@atlasos/types'
import { api } from '@/lib/api'

export default function WorkspacePage() {
  const { id } = useParams<{ id: string }>()
  const [workspace, setWorkspace] = useState<Workspace | null>(null)
  const [selected, setSelected] = useState<Set<string>>(new Set())
  const [error, setError] = useState('')
  const [saving, setSaving] = useState(false)

  const load = useCallback(async () => {
    try {
      const data = await api.workspaces.get(id)
      setWorkspace(data)
      setSelected(
        new Set(
          data.companies
            .filter((company) => !company.is_subject && company.is_confirmed)
            .map((company) => company.id),
        ),
      )
      return data
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not load market')
      return null
    }
  }, [id])

  useEffect(() => {
    void load()
  }, [load])

  useEffect(() => {
    if (workspace?.status !== 'discovering') return

    const timer = setTimeout(() => {
      void load()
    }, 2500)

    return () => clearTimeout(timer)
  }, [load, workspace?.status])

  const candidates = useMemo(
    () => workspace?.companies.filter((company) => !company.is_subject) ?? [],
    [workspace],
  )

  function toggle(companyId: string) {
    setSelected((current) => {
      const next = new Set(current)
      if (next.has(companyId)) next.delete(companyId)
      else next.add(companyId)
      return next
    })
  }

  async function confirm() {
    setSaving(true)
    setError('')
    try {
      setWorkspace(await api.workspaces.confirmCompanies(id, [...selected]))
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not confirm competitors')
    } finally {
      setSaving(false)
    }
  }

  async function retryDiscovery() {
    setError('')
    try {
      await api.workspaces.discover(id)
      setWorkspace((current) =>
        current ? { ...current, status: 'discovering', error: null } : current,
      )
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not start discovery')
    }
  }

  if (!workspace) {
    return (
      <div className="min-h-screen bg-black text-zinc-500 flex items-center justify-center">
        {error || 'Loading market…'}
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-black text-white">
      <div className="max-w-5xl mx-auto px-6 py-12">
        <Link href="/dashboard" className="text-sm text-zinc-500 hover:text-white">
          ← Markets
        </Link>

        <header className="mt-8 mb-12">
          <div className="flex items-start justify-between gap-6">
            <div>
              <h1 className="text-3xl font-semibold">{workspace.name}</h1>
              <p className="text-zinc-400 mt-2">{workspace.company_name}</p>
            </div>
            <Status status={workspace.status} />
          </div>
          {workspace.category_label && (
            <div className="mt-6 border-l border-zinc-700 pl-4">
              <p className="text-sm font-medium">{workspace.category_label}</p>
              <p className="text-sm text-zinc-500 mt-1">
                {workspace.category_definition}
              </p>
            </div>
          )}
        </header>

        {workspace.status === 'discovering' && <DiscoveryState />}

        {workspace.status === 'failed' && (
          <div className="border border-red-900 bg-red-950/40 rounded-lg p-5">
            <p className="text-sm font-medium text-red-300">Discovery failed</p>
            <p className="text-xs text-red-400 mt-2">{workspace.error}</p>
            <button
              onClick={retryDiscovery}
              className="text-sm mt-4 px-3 py-2 bg-white text-black rounded-md"
            >
              Retry discovery
            </button>
          </div>
        )}

        {(workspace.status === 'review' || workspace.status === 'active') && (
          <section>
            <div className="flex items-end justify-between mb-5">
              <div>
                <h2 className="text-xl font-semibold">Competitive set</h2>
                <p className="text-sm text-zinc-500 mt-1">
                  Confirm only the companies AtlasOS should monitor.
                </p>
              </div>
              <span className="text-xs text-zinc-500">{selected.size} selected</span>
            </div>

            <div className="space-y-3">
              {candidates.map((company) => (
                <label
                  key={company.id}
                  className={`block border rounded-lg p-4 cursor-pointer transition ${
                    selected.has(company.id)
                      ? 'border-white bg-zinc-900'
                      : 'border-zinc-800 hover:border-zinc-600'
                  }`}
                >
                  <div className="flex gap-4">
                    <input
                      type="checkbox"
                      checked={selected.has(company.id)}
                      onChange={() => toggle(company.id)}
                      className="mt-1"
                    />
                    <div className="flex-1">
                      <div className="flex items-center justify-between gap-4">
                        <p className="font-medium">{company.name}</p>
                        <span className="text-xs text-zinc-500 capitalize">
                          {company.type} · {company.threat_level ?? 'unrated'}
                        </span>
                      </div>
                      <p className="text-sm text-zinc-400 mt-2">{company.summary}</p>
                      {company.website_url && (
                        <p className="text-xs text-zinc-600 mt-2">
                          {company.website_url}
                        </p>
                      )}
                    </div>
                  </div>
                </label>
              ))}
            </div>

            {candidates.length === 0 && (
              <p className="text-sm text-zinc-500 border border-zinc-800 rounded-lg p-6">
                No competitor candidates were returned.
              </p>
            )}

            {error && <p className="text-sm text-red-400 mt-4">{error}</p>}

            <div className="flex justify-end mt-6">
              <button
                onClick={confirm}
                disabled={saving || selected.size === 0}
                className="bg-white text-black text-sm font-medium px-5 py-2.5 rounded-md disabled:opacity-40"
              >
                {saving ? 'Saving…' : 'Confirm competitive set'}
              </button>
            </div>
          </section>
        )}

        {workspace.status === 'draft' && (
          <button
            onClick={retryDiscovery}
            className="bg-white text-black text-sm font-medium px-5 py-2.5 rounded-md"
          >
            Discover competitors
          </button>
        )}
      </div>
    </div>
  )
}

function DiscoveryState() {
  return (
    <div className="border border-zinc-800 bg-zinc-900 rounded-xl p-8">
      <p className="text-sm font-medium">Discovering the market</p>
      <p className="text-sm text-zinc-500 mt-2">
        Extracting the company site, defining the category, and classifying competitors.
      </p>
      <div className="h-1 bg-zinc-800 rounded mt-6 overflow-hidden">
        <div className="h-full w-1/2 bg-white animate-pulse" />
      </div>
    </div>
  )
}

function Status({ status }: { status: Workspace['status'] }) {
  const label = {
    draft: 'Draft',
    discovering: 'Discovering',
    review: 'Needs review',
    active: 'Active',
    failed: 'Failed',
  }[status]
  return (
    <span className="text-xs px-2.5 py-1 rounded bg-zinc-900 border border-zinc-800 text-zinc-300">
      {label}
    </span>
  )
}
