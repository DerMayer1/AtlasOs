import type { Competitor, ThreatLevel } from '@atlasos/types'
import { cn } from '@/lib/utils'

interface Props {
  competitor: Competitor
}

const threatStyles: Record<ThreatLevel, string> = {
  high:   'bg-red-950 text-red-300 border-red-800',
  medium: 'bg-yellow-950 text-yellow-300 border-yellow-800',
  low:    'bg-zinc-800 text-zinc-400 border-zinc-700',
}

export function CompetitorCard({ competitor: c }: Props) {
  return (
    <article
      className="bg-zinc-900 border border-zinc-800 rounded-lg p-4 hover:border-zinc-700 transition"
      aria-label={`${c.name} — ${c.type} competitor`}
    >
      <div className="flex items-center justify-between mb-2">
        <span className="font-medium text-sm">{c.name}</span>
        <span
          className={cn('text-xs px-2 py-0.5 rounded border capitalize', threatStyles[c.threat_level])}
          aria-label={`Threat level: ${c.threat_level}`}
        >
          {c.threat_level}
        </span>
      </div>
      <p className="text-zinc-400 text-xs leading-relaxed">{c.summary}</p>
      {c.website && (
        <a
          href={c.website}
          target="_blank"
          rel="noopener noreferrer"
          className="text-zinc-600 hover:text-zinc-400 text-xs mt-2 block transition"
          aria-label={`Visit ${c.name} website`}
        >
          {c.website.replace(/^https?:\/\//, '')} ↗
        </a>
      )}
    </article>
  )
}
