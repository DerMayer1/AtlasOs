import { notFound, redirect } from 'next/navigation'
import Link from 'next/link'
import { createClient } from '@/lib/supabase/server'
import { PositioningMap } from '@/components/PositioningMap'
import type { Analysis } from '@atlasos/types'

async function getAnalysis(id: string, token: string): Promise<Analysis | null> {
  const apiBase = process.env.API_URL ?? 'http://localhost:8000'
  const res = await fetch(`${apiBase}/v1/analyses/${id}`, {
    headers: { Authorization: `Bearer ${token}` },
    cache: 'no-store',
  })
  if (!res.ok) return null
  return res.json()
}

export default async function AnalysisPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params
  const supabase = await createClient()
  const { data: { session } } = await supabase.auth.getSession()
  if (!session) redirect('/auth/login')

  const analysis = await getAnalysis(id, session.access_token)
  if (!analysis) notFound()

  // Redirect to progress if not yet complete
  if (analysis.status === 'pending' || analysis.status === 'running') {
    redirect(`/dashboard/analyses/${id}/progress`)
  }

  if (analysis.status === 'failed' || !analysis.result) notFound()

  const { category, competitors, positioning_map, gaps, recommendations } = analysis.result
  const byType = (type: string) => competitors.filter((c) => c.type === type)

  return (
    <div className="min-h-screen bg-black text-white">
      <div className="max-w-4xl mx-auto px-6 py-12 space-y-16">

        {/* Header */}
        <div className="flex items-start justify-between">
          <div>
            <Link href="/dashboard" className="text-zinc-500 text-sm hover:text-white transition">← Dashboard</Link>
            <h1 className="text-3xl font-semibold mt-4">{analysis.input.company_name}</h1>
            <p className="text-zinc-400 text-sm mt-2">{category.label}</p>
            {analysis.duration_ms && (
              <p className="text-zinc-600 text-xs mt-1">Completed in {(analysis.duration_ms / 1000).toFixed(1)}s</p>
            )}
          </div>
          <div className="flex gap-3 mt-8">
            <Link
              href={`/dashboard/analyses/${id}/memo`}
              className="text-sm px-4 py-2 bg-white text-black rounded-md font-medium hover:bg-zinc-200 transition"
            >
              Market Memo →
            </Link>
          </div>
        </div>

        {/* Category */}
        <section>
          <SectionLabel>Market Category</SectionLabel>
          <p className="text-zinc-200">{category.definition}</p>
        </section>

        {/* Competitors */}
        <section>
          <SectionLabel>Competitive Set</SectionLabel>
          <div className="space-y-6">
            {(['direct', 'indirect', 'substitute', 'adjacent', 'future'] as const).map((type) => {
              const group = byType(type)
              if (!group.length) return null
              return (
                <div key={type}>
                  <h3 className="text-sm font-medium capitalize text-zinc-400 mb-3">{type}</h3>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    {group.map((c) => (
                      <div key={c.name} className="bg-zinc-900 border border-zinc-800 rounded-lg p-4">
                        <div className="flex items-center justify-between mb-2">
                          <span className="font-medium text-sm">{c.name}</span>
                          <ThreatBadge level={c.threat_level} />
                        </div>
                        <p className="text-zinc-400 text-xs leading-relaxed">{c.summary}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )
            })}
          </div>
        </section>

        {/* Positioning Map */}
        {positioning_map && (
          <section>
            <SectionLabel>Positioning Map</SectionLabel>
            <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-6">
              <PositioningMap map={positioning_map} />
            </div>
          </section>
        )}

        {/* Gaps */}
        {gaps.length > 0 && (
          <section>
            <SectionLabel>Market Gaps</SectionLabel>
            <div className="space-y-4">
              {gaps.map((gap, i) => (
                <div key={i} className="bg-zinc-900 border border-zinc-800 rounded-lg p-5">
                  <p className="text-sm text-zinc-100 mb-3">{gap.description}</p>
                  <div className="grid grid-cols-2 gap-4 text-xs">
                    <div><span className="text-zinc-500 block mb-1">Addressability</span><span className="text-zinc-300">{gap.addressability}</span></div>
                    <div><span className="text-zinc-500 block mb-1">Risk</span><span className="text-zinc-300">{gap.risk}</span></div>
                  </div>
                </div>
              ))}
            </div>
          </section>
        )}

        {/* Recommendations */}
        {recommendations.length > 0 && (
          <section>
            <SectionLabel>Strategic Recommendations</SectionLabel>
            <div className="space-y-4">
              {recommendations.map((rec, i) => (
                <div key={i} className="border border-zinc-800 rounded-lg p-5">
                  <div className="flex items-center gap-2 mb-3">
                    <span className="text-xs font-medium bg-zinc-800 text-zinc-300 px-2 py-0.5 rounded">{rec.type}</span>
                    <span className="text-xs text-zinc-600">#{i + 1}</span>
                  </div>
                  <p className="text-sm text-zinc-100 mb-3">{rec.description}</p>
                  <div className="grid grid-cols-2 gap-4 text-xs">
                    <div><span className="text-zinc-500 block mb-1">Expected impact</span><span className="text-zinc-300">{rec.impact}</span></div>
                    <div><span className="text-zinc-500 block mb-1">Key risk</span><span className="text-zinc-300">{rec.risk}</span></div>
                  </div>
                </div>
              ))}
            </div>
          </section>
        )}

      </div>
    </div>
  )
}

function SectionLabel({ children }: { children: React.ReactNode }) {
  return <h2 className="text-xs font-medium uppercase tracking-widest text-zinc-500 mb-6">{children}</h2>
}

function ThreatBadge({ level }: { level: string }) {
  const colors: Record<string, string> = {
    high:   'bg-red-950 text-red-300 border-red-800',
    medium: 'bg-yellow-950 text-yellow-300 border-yellow-800',
    low:    'bg-zinc-800 text-zinc-400 border-zinc-700',
  }
  return (
    <span className={`text-xs px-2 py-0.5 rounded border capitalize ${colors[level] ?? colors.low}`}>
      {level}
    </span>
  )
}
