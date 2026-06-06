import Link from 'next/link'
import { PositioningMap } from '@/components/PositioningMap'

// Pre-generated demo analysis for Linear
const DEMO = {
  company_name: 'Linear',
  category: {
    label: 'Engineering-first project tracking tools',
    definition:
      'Software for planning, tracking, and shipping product work, built specifically for the speed and workflow preferences of modern engineering teams.',
  },
  competitors: [
    { name: 'Jira', type: 'direct', threat_level: 'high' as const, summary: 'Market-dominant project tracker with deep enterprise integrations. Slow, complex UX that Linear explicitly positions against.' },
    { name: 'Asana', type: 'direct', threat_level: 'medium' as const, summary: 'Cross-functional work management. Strong in marketing and ops teams; lighter in engineering.' },
    { name: 'GitHub Issues', type: 'indirect', threat_level: 'medium' as const, summary: 'Built into the dev workflow. Lacks roadmapping and cross-team visibility.' },
    { name: 'Notion', type: 'substitute', threat_level: 'low' as const, summary: 'Flexible docs+tasks workspace. Used as a lightweight PM tool by early-stage teams.' },
  ],
  positioning_map: {
    x_axis: { label: 'Target user', low: 'All teams', high: 'Engineering only' },
    y_axis: { label: 'Speed/UX', low: 'Heavy / complex', high: 'Fast / opinionated' },
    entities: [
      { name: 'Linear', x: 0.75, y: 0.85, is_subject: true },
      { name: 'Jira', x: -0.6, y: -0.7, is_subject: false },
      { name: 'Asana', x: -0.5, y: 0.2, is_subject: false },
      { name: 'GitHub Issues', x: 0.9, y: 0.1, is_subject: false },
      { name: 'Notion', x: -0.8, y: 0.5, is_subject: false },
    ],
  },
  gaps: [
    {
      description: 'No strong player serves fast-growing startups transitioning from GitHub Issues to a full PM tool without sacrificing developer ergonomics.',
      addressability: 'High — large cohort of Series A/B companies hitting this wall.',
      risk: 'Linear is already the default winner here; gap may be closing.',
    },
  ],
  recommendations: [
    {
      type: 'Vertically Focus',
      description: 'Double down on engineering-led companies at Series A–C with 10–50 engineers. Build deeper integrations with CI/CD, deployment, and on-call tooling.',
      impact: 'Defensible moat in the segment with highest LTV and expansion potential.',
      risk: 'Narrows TAM narrative for future fundraising rounds.',
    },
  ],
}

export default function DemoPage() {
  const byType = (type: string) => DEMO.competitors.filter((c) => c.type === type)
  const threatColors = { high: 'text-red-400', medium: 'text-yellow-400', low: 'text-zinc-500' }

  return (
    <div className="min-h-screen bg-black text-white">
      <div className="max-w-4xl mx-auto px-6 py-12 space-y-16">

        <div className="flex items-center justify-between">
          <div>
            <Link href="/" className="text-zinc-500 text-sm hover:text-white transition">← AtlasOS</Link>
            <h1 className="text-3xl font-semibold mt-4">Demo: Linear</h1>
            <p className="text-zinc-400 text-sm mt-1">{DEMO.category.label}</p>
          </div>
          <Link
            href="/auth/login"
            className="text-sm bg-white text-black px-4 py-2 rounded-md font-medium hover:bg-zinc-200 transition"
          >
            Analyze your company →
          </Link>
        </div>

        <section>
          <h2 className="text-xs font-medium uppercase tracking-widest text-zinc-500 mb-3">Market Category</h2>
          <p className="text-zinc-200">{DEMO.category.definition}</p>
        </section>

        <section>
          <h2 className="text-xs font-medium uppercase tracking-widest text-zinc-500 mb-6">Competitive Set</h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {DEMO.competitors.map((c) => (
              <div key={c.name} className="bg-zinc-900 border border-zinc-800 rounded-lg p-4">
                <div className="flex items-center justify-between mb-2">
                  <span className="font-medium text-sm">{c.name}</span>
                  <span className={`text-xs capitalize ${threatColors[c.threat_level]}`}>{c.threat_level}</span>
                </div>
                <p className="text-zinc-400 text-xs leading-relaxed">{c.summary}</p>
              </div>
            ))}
          </div>
        </section>

        <section>
          <h2 className="text-xs font-medium uppercase tracking-widest text-zinc-500 mb-6">Positioning Map</h2>
          <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-6">
            <PositioningMap map={DEMO.positioning_map} />
          </div>
        </section>

        <section>
          <h2 className="text-xs font-medium uppercase tracking-widest text-zinc-500 mb-4">Market Gap</h2>
          {DEMO.gaps.map((g, i) => (
            <div key={i} className="bg-zinc-900 border border-zinc-800 rounded-lg p-5">
              <p className="text-sm text-zinc-100 mb-3">{g.description}</p>
              <div className="grid grid-cols-2 gap-4 text-xs">
                <div><span className="text-zinc-500 block mb-1">Addressability</span><span className="text-zinc-300">{g.addressability}</span></div>
                <div><span className="text-zinc-500 block mb-1">Risk</span><span className="text-zinc-300">{g.risk}</span></div>
              </div>
            </div>
          ))}
        </section>

        <section>
          <h2 className="text-xs font-medium uppercase tracking-widest text-zinc-500 mb-4">Strategic Recommendation</h2>
          {DEMO.recommendations.map((r, i) => (
            <div key={i} className="border border-zinc-800 rounded-lg p-5">
              <span className="text-xs font-medium bg-zinc-800 text-zinc-300 px-2 py-0.5 rounded">{r.type}</span>
              <p className="text-sm text-zinc-100 mt-3 mb-3">{r.description}</p>
              <div className="grid grid-cols-2 gap-4 text-xs">
                <div><span className="text-zinc-500 block mb-1">Expected impact</span><span className="text-zinc-300">{r.impact}</span></div>
                <div><span className="text-zinc-500 block mb-1">Key risk</span><span className="text-zinc-300">{r.risk}</span></div>
              </div>
            </div>
          ))}
        </section>

        <div className="text-center pt-8 border-t border-zinc-900">
          <p className="text-zinc-500 text-sm mb-4">This is a pre-generated demo. Run a live analysis on any company.</p>
          <Link
            href="/auth/login"
            className="inline-block bg-white text-black text-sm font-medium px-6 py-3 rounded-md hover:bg-zinc-200 transition"
          >
            Get started free →
          </Link>
        </div>

      </div>
    </div>
  )
}
