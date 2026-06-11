'use client'

import { useCallback, useEffect, useMemo, useState } from 'react'
import Link from 'next/link'
import { useParams } from 'next/navigation'
import type { CompanyChange, Workspace, WorkspaceReport } from '@atlasos/types'
import { api } from '@/lib/api'

export default function WorkspacePage() {
  const { id } = useParams<{ id: string }>()
  const [workspace, setWorkspace] = useState<Workspace | null>(null)
  const [changes, setChanges] = useState<CompanyChange[]>([])
  const [reports, setReports] = useState<WorkspaceReport[]>([])
  const [selected, setSelected] = useState<Set<string>>(new Set())
  const [error, setError] = useState('')
  const [saving, setSaving] = useState(false)
  const [refreshing, setRefreshing] = useState(false)
  const [startingDiscovery, setStartingDiscovery] = useState(false)

  const load = useCallback(async () => {
    try {
      const data = await api.workspaces.get(id)
      setWorkspace(data)
      // Changes and reports only exist (and are only rendered) once the
      // workspace is active, so skip those requests in earlier states.
      if (data.status === 'active') {
        const [changeData, reportData] = await Promise.all([
          api.workspaces.listChanges(id),
          api.workspaces.listReports(id),
        ])
        setChanges(changeData.items)
        setReports(reportData.items)
      }
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
    // The state update happens after the asynchronous API requests resolve.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void load()
  }, [load])

  useEffect(() => {
    if (workspace?.status !== 'discovering') return

    const timer = setTimeout(() => {
      void load()
    }, 2500)

    return () => clearTimeout(timer)
  }, [load, workspace?.status])

  const monitoringInProgress =
    workspace?.companies.some(
      (company) =>
        company.is_confirmed &&
        (company.monitoring_status === 'pending' || company.monitoring_status === 'running'),
    ) ?? false

  useEffect(() => {
    if (!monitoringInProgress) return

    const timer = setTimeout(() => {
      void load()
    }, 2500)

    return () => clearTimeout(timer)
  }, [load, monitoringInProgress])

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
    setStartingDiscovery(true)
    setError('')
    try {
      await api.workspaces.discover(id)
      setWorkspace((current) =>
        current ? { ...current, status: 'discovering', error: null } : current,
      )
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not start discovery')
    } finally {
      setStartingDiscovery(false)
    }
  }

  async function captureSnapshots() {
    setRefreshing(true)
    setError('')
    try {
      await api.workspaces.captureSnapshots(id)
      setWorkspace((current) =>
        current
          ? {
              ...current,
              companies: current.companies.map((company) =>
                company.is_confirmed
                  ? {
                      ...company,
                      monitoring_status: 'pending',
                      snapshot_error: null,
                    }
                  : company,
              ),
            }
          : current,
      )
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not refresh snapshots')
    } finally {
      setRefreshing(false)
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
              <p className="text-sm text-zinc-500 mt-1">{workspace.category_definition}</p>
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
                        <p className="text-xs text-zinc-600 mt-2">{company.website_url}</p>
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

        {workspace.status === 'active' && (
          <>
            <MonitoringBaseline
              companies={workspace.companies.filter(
                (company) => company.is_subject || company.is_confirmed,
              )}
              refreshing={refreshing || monitoringInProgress}
              onRefresh={captureSnapshots}
            />
            <ChangeTimeline changes={changes} companies={workspace.companies} />
            <ReportList workspaceId={id} reports={reports} />
          </>
        )}

        {workspace.status === 'draft' && (
          <div>
            <p className="text-sm text-zinc-500 mb-4">Discovery has not started yet.</p>
            {error ? <p className="text-sm text-red-400 mb-4">{error}</p> : null}
            <button
              onClick={retryDiscovery}
              disabled={startingDiscovery}
              className="bg-white text-black text-sm font-medium px-5 py-2.5 rounded-md disabled:opacity-40"
            >
              {startingDiscovery ? 'Starting…' : 'Discover competitors'}
            </button>
          </div>
        )}
      </div>
    </div>
  )
}

function ChangeTimeline({
  changes,
  companies,
}: {
  changes: CompanyChange[]
  companies: Workspace['companies']
}) {
  const [relevance, setRelevance] = useState('all')
  const [category, setCategory] = useState('all')
  const [companyId, setCompanyId] = useState('all')
  const [expanded, setExpanded] = useState<Set<string>>(new Set())
  const companiesById = new Map(companies.map((company) => [company.id, company]))
  const categories = [...new Set(changes.map((change) => change.category))]
  const changedCompanyIds = new Set(changes.map((change) => change.company_id))
  const changedCompanies = companies.filter((company) => changedCompanyIds.has(company.id))
  const filteredChanges = changes.filter(
    (change) =>
      (relevance === 'all' || change.relevance === relevance) &&
      (category === 'all' || change.category === category) &&
      (companyId === 'all' || change.company_id === companyId),
  )

  function toggleEvidence(changeId: string) {
    setExpanded((current) => {
      const next = new Set(current)
      if (next.has(changeId)) next.delete(changeId)
      else next.add(changeId)
      return next
    })
  }

  return (
    <section className="mt-14 pt-10 border-t border-zinc-800">
      <p className="text-xs uppercase tracking-widest text-zinc-500 mb-2">Change timeline</p>
      <h2 className="text-xl font-semibold">Meaningful market changes</h2>
      <p className="text-sm text-zinc-500 mt-1 mb-5">
        Routine page noise is filtered before a change reaches this timeline.
      </p>

      {changes.length === 0 ? (
        <div className="border border-zinc-800 rounded-lg p-6 text-sm text-zinc-500">
          No meaningful changes detected after the baseline yet.
        </div>
      ) : (
        <>
          <div className="grid sm:grid-cols-3 gap-3 mb-5">
            <TimelineFilter
              label="Relevance"
              value={relevance}
              onChange={setRelevance}
              options={[
                ['all', 'All priorities'],
                ['high', 'High'],
                ['medium', 'Medium'],
                ['low', 'Low'],
              ]}
            />
            <TimelineFilter
              label="Category"
              value={category}
              onChange={setCategory}
              options={[
                ['all', 'All categories'],
                ...categories.map((value) => [value, capitalize(value)]),
              ]}
            />
            <TimelineFilter
              label="Company"
              value={companyId}
              onChange={setCompanyId}
              options={[
                ['all', 'All companies'],
                ...changedCompanies.map((company) => [company.id, company.name]),
              ]}
            />
          </div>

          <div className="flex items-center justify-between mb-3">
            <p className="text-xs text-zinc-500 tabular-nums">
              Showing {filteredChanges.length} of {changes.length} changes
            </p>
            {filteredChanges.length !== changes.length ? (
              <button
                onClick={() => {
                  setRelevance('all')
                  setCategory('all')
                  setCompanyId('all')
                }}
                className="text-xs text-zinc-400 hover:text-white transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-zinc-500"
              >
                Clear filters
              </button>
            ) : null}
          </div>

          {filteredChanges.length === 0 ? (
            <div className="border border-zinc-800 rounded-lg p-6 text-sm text-zinc-500">
              No changes match these filters.
            </div>
          ) : (
            <div className="space-y-3">
              {filteredChanges.map((change) => (
                <article
                  key={change.id}
                  className="border border-zinc-800 bg-zinc-950 rounded-lg p-5 transition hover:border-zinc-700"
                >
                  <div className="flex items-start justify-between gap-5">
                    <div>
                      <p className="font-medium">
                        {companiesById.get(change.company_id)?.name ?? 'Company'}
                      </p>
                      <p className="text-sm text-zinc-300 mt-2">{change.summary}</p>
                    </div>
                    <span
                      className={`text-xs capitalize whitespace-nowrap ${
                        change.relevance === 'high'
                          ? 'text-red-300'
                          : change.relevance === 'medium'
                            ? 'text-amber-300'
                            : 'text-zinc-500'
                      }`}
                    >
                      {change.category} · {change.relevance}
                    </span>
                  </div>
                  <div className="flex items-center justify-between gap-4 mt-4">
                    <p className="text-xs text-zinc-600">{formatCapturedAt(change.created_at)}</p>
                    <button
                      onClick={() => toggleEvidence(change.id)}
                      className="text-xs text-zinc-400 hover:text-white transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-zinc-500"
                      aria-expanded={expanded.has(change.id)}
                    >
                      {expanded.has(change.id) ? 'Hide evidence' : 'View evidence'}
                    </button>
                  </div>
                  {expanded.has(change.id) ? <Evidence evidence={change.evidence} /> : null}
                </article>
              ))}
            </div>
          )}
        </>
      )}
    </section>
  )
}

function TimelineFilter({
  label,
  value,
  onChange,
  options,
}: {
  label: string
  value: string
  onChange: (value: string) => void
  options: string[][]
}) {
  return (
    <label className="text-xs text-zinc-500">
      <span className="block mb-2">{label}</span>
      <select
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="w-full bg-zinc-950 border border-zinc-800 rounded-md px-3 py-2.5 text-sm text-zinc-200 focus:outline-none focus:border-zinc-500"
      >
        {options.map(([optionValue, optionLabel]) => (
          <option key={optionValue} value={optionValue}>
            {optionLabel}
          </option>
        ))}
      </select>
    </label>
  )
}

function Evidence({ evidence }: { evidence: CompanyChange['evidence'] }) {
  return (
    <div className="grid md:grid-cols-2 gap-4 mt-5 pt-5 border-t border-zinc-800">
      <EvidenceColumn title="Added" items={evidence.added ?? []} />
      <EvidenceColumn title="Removed" items={evidence.removed ?? []} />
    </div>
  )
}

function EvidenceColumn({ title, items }: { title: string; items: string[] }) {
  return (
    <div>
      <p className="text-[11px] uppercase tracking-widest text-zinc-600 mb-2">{title}</p>
      {items.length ? (
        <ul className="space-y-2">
          {items.map((item, index) => (
            <li key={`${item}-${index}`} className="text-xs leading-relaxed text-zinc-400">
              {item}
            </li>
          ))}
        </ul>
      ) : (
        <p className="text-xs text-zinc-600">No excerpt available.</p>
      )}
    </div>
  )
}

function ReportList({ workspaceId, reports }: { workspaceId: string; reports: WorkspaceReport[] }) {
  return (
    <section className="mt-14 pt-10 border-t border-zinc-800">
      <p className="text-xs uppercase tracking-widest text-zinc-500 mb-2">Reports</p>
      <h2 className="text-xl font-semibold">Monitoring reports</h2>
      <p className="text-sm text-zinc-500 mt-1 mb-5">
        Baselines and meaningful change summaries are available for export.
      </p>

      {reports.length === 0 ? (
        <div className="border border-zinc-800 rounded-lg p-6 text-sm text-zinc-500">
          The first report is created when baseline capture completes.
        </div>
      ) : (
        <div className="grid gap-3">
          {reports.map((report) => (
            <Link
              key={report.id}
              href={`/dashboard/workspaces/${workspaceId}/reports/${report.id}`}
              className="border border-zinc-800 rounded-lg p-4 flex items-center justify-between gap-6 hover:border-zinc-600 transition"
            >
              <div>
                <p className="text-sm font-medium">{report.title}</p>
                <p className="text-xs text-zinc-500 mt-1">{formatCapturedAt(report.created_at)}</p>
              </div>
              <span className="text-xs text-zinc-500 capitalize">{report.report_type}</span>
            </Link>
          ))}
        </div>
      )}
    </section>
  )
}

function MonitoringBaseline({
  companies,
  refreshing,
  onRefresh,
}: {
  companies: Workspace['companies']
  refreshing: boolean
  onRefresh: () => void
}) {
  const ready = companies.filter((company) => company.monitoring_status === 'ready').length

  return (
    <section className="mt-14 pt-10 border-t border-zinc-800">
      <div className="flex items-end justify-between gap-6 mb-5">
        <div>
          <p className="text-xs uppercase tracking-widest text-zinc-500 mb-2">
            Monitoring baseline
          </p>
          <h2 className="text-xl font-semibold">
            {ready} of {companies.length} companies captured
          </h2>
          <p className="text-sm text-zinc-500 mt-1">
            AtlasOS stores the visible website state used for future comparisons.
          </p>
        </div>
        <button
          onClick={onRefresh}
          disabled={refreshing}
          className="border border-zinc-700 text-sm px-4 py-2 rounded-md hover:border-zinc-500 disabled:opacity-40"
        >
          {refreshing ? 'Capturing…' : 'Refresh baseline'}
        </button>
      </div>

      <div className="grid gap-3">
        {companies.map((company) => (
          <div
            key={company.id}
            className="border border-zinc-800 rounded-lg p-4 flex items-start justify-between gap-6"
          >
            <div>
              <div className="flex items-center gap-2">
                <p className="text-sm font-medium">{company.name}</p>
                {company.is_subject ? (
                  <span className="text-[10px] uppercase tracking-wide text-zinc-600">
                    Your company
                  </span>
                ) : null}
              </div>
              {company.latest_snapshot ? (
                <p className="text-xs text-zinc-500 mt-1">
                  Captured {formatCapturedAt(company.latest_snapshot.captured_at)}
                  {company.latest_snapshot.metadata.character_count
                    ? ` · ${company.latest_snapshot.metadata.character_count.toLocaleString()} characters`
                    : ''}
                </p>
              ) : (
                <p className="text-xs text-zinc-600 mt-1">No baseline captured yet.</p>
              )}
              {company.snapshot_error ? (
                <p className="text-xs text-red-400 mt-2">{company.snapshot_error}</p>
              ) : null}
            </div>
            <MonitoringStatus status={company.monitoring_status} />
          </div>
        ))}
      </div>
    </section>
  )
}

function MonitoringStatus({
  status,
}: {
  status: Workspace['companies'][number]['monitoring_status']
}) {
  const labels = {
    idle: 'Not captured',
    pending: 'Queued',
    running: 'Capturing',
    ready: 'Ready',
    failed: 'Failed',
  }
  const styles = {
    idle: 'text-zinc-500',
    pending: 'text-blue-300',
    running: 'text-blue-300',
    ready: 'text-emerald-300',
    failed: 'text-red-300',
  }
  return <span className={`text-xs whitespace-nowrap ${styles[status]}`}>{labels[status]}</span>
}

function formatCapturedAt(value: string) {
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(new Date(value))
}

function capitalize(value: string) {
  return value.charAt(0).toUpperCase() + value.slice(1)
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
