import type { Recommendation } from '@atlasos/types'

interface Props {
  recommendation: Recommendation
  index: number
}

export function RecommendationCard({ recommendation: rec, index }: Props) {
  return (
    <article
      className="border border-zinc-800 rounded-lg p-5 hover:border-zinc-700 transition"
      aria-label={`Recommendation ${index + 1}: ${rec.type}`}
    >
      <div className="flex items-center gap-2 mb-3">
        <span className="text-xs font-medium bg-zinc-800 text-zinc-300 px-2 py-0.5 rounded">
          {rec.type}
        </span>
        <span className="text-xs text-zinc-600" aria-hidden="true">#{index + 1}</span>
      </div>
      <p className="text-sm text-zinc-100 mb-3 leading-relaxed">{rec.description}</p>
      <dl className="grid grid-cols-2 gap-4 text-xs">
        <div>
          <dt className="text-zinc-500 mb-1">Expected impact</dt>
          <dd className="text-zinc-300">{rec.impact}</dd>
        </div>
        <div>
          <dt className="text-zinc-500 mb-1">Key risk</dt>
          <dd className="text-zinc-300">{rec.risk}</dd>
        </div>
      </dl>
    </article>
  )
}
