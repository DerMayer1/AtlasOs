import { notFound } from 'next/navigation'
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
  if (!session) notFound()

  const analysis = await getAnalysis(id, session.access_token)
  if (!analysis || analysis.status !== 'complete' || !analysis.result) notFound()

  const { category, competitors, positioning_map, gaps, recommendations } = analysis.result

  const byType = (type: string) => competitors.filter((c) => c.type === type)

  return (
    <div className="min-h-screen bg-black text-white">
      <div className="max-w-4xl mx-auto px-6 py-12 space-y-16">

        {/* Header */}
        <div className="flex items-start justify-between">
          <div>
            <p className="text-zinc-500 text-sm mb-1">Market Analysis</p>
            <h1 className="text-3xl font-semibold">{analysis.input.company_name}</h1>
            <p className="text-zinc-400 text-sm mt-2">{category.label}</p>
          </div>
          <div className="flex gap-3">
            <Link
              href={`/dashboard/analyses/${id}/memo`}
              className="text-sm px-4 py-2 border border-zinc-700 rounded-md text-zinc-300 hover:border-zinc-500 transition"
            >
              View Memo
            </Link>
          </div>
        </div>

        {/* Category */}
        <section>
          <h2 className="text-xs font-medium uppercase tracking-widest text-zinc-500 mb-3">Market Category</h2>
          <p className="text-zinc-200">{category.definition}</p>
        </section>

        {/* Competitors */}
        <section>
          <h2 className="text-xs font-medium uppercase tracking-widest text-zinc-500 mb-6">Competitive Set</h2>
          <div className="space-y-6">
            {['direct', 'indirect', 'substitute', 'adjacent', 'future'].map((type) => {
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
            <h2 className="text-xs font-medium uppercase tracking-widest text-zinc-500 mb-6">Positioning Map</h2>
            <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-6">
              <PositioningMap map={positioning_map} />
            </div>
          </section>
        )}

        {/* Gaps */}
        {gaps.length > 0 && (
          <section>
            <h2 className="text-xs font-medium uppercase tracking-widest text-zinc-500 mb-6">Market Gaps</h2>
            <div className="space-y-4">
              {gaps.map((gap, i) => (
                <div key={i} className="bg-zinc-900 border border-zinc-800 rounded-lg p-5">
                  <p className="text-sm text-zinc-100 mb-3">{gap.description}</p>
                  <div className="grid grid-cols-2 gap-4 text-xs">
                    <div>
                      <span className="text-zinc-500 block mb-1">Addressability</span>
                      <span className="text-zinc-300">{gap.addressability}</span>
                    </div>
                    <div>
                      <span className="text-zinc-500 block mb-1">Risk</span>
                      <span className="text-zinc-300">{gap.risk}</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </section>
        )}

        {/* Recommendations */}
        {recommendations.length > 0 && (
          <section>
            <h2 className="text-xs font-medium uppercase tracking-widest text-zinc-500 mb-6">Strategic Recommendations</h2>
            <div className="space-y-4">
              {recommendations.map((rec, i) => (
                <div key={i} className="border border-zinc-800 rounded-lg p-5">
                  <div className="flex items-center gap-2 mb-3">
                    <span className="text-xs font-medium bg-zinc-800 text-zinc-300 px-2 py-0.5 rounded">
                      {rec.type}
                    </span>
                    <span className="text-xs text-zinc-500">#{i + 1}</span>
                  </div>
                  <p className="text-sm text-zinc-100 mb-3">{rec.description}</p>
                  <div className="grid grid-cols-2 gap-4 text-xs">
                    <div>
                      <span className="text-zinc-500 block mb-1">Expected impact</span>
                      <span className="text-zinc-300">{rec.impact}</span>
                    </div>
                    <div>
                      <span className="text-zinc-500 block mb-1">Key risk</span>
                      <span className="text-zinc-300">{rec.risk}</span>
                    </div>
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

function ThreatBadge({ level }: { level: string }) {
  const colors = {
    high: 'bg-red-950 text-red-300 border-red-800',
    medium: 'bg-yellow-950 text-yellow-300 border-yellow-800',
    low: 'bg-zinc-800 text-zinc-400 border-zinc-700',
  }
  return (
    <span className={`text-xs px-2 py-0.5 rounded border capitalize ${colors[level as keyof typeof colors] ?? colors.low}`}>
      {level}
    </span>
  )
}
