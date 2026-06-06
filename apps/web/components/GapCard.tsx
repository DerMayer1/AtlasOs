import type { Gap } from '@atlasos/types'

interface Props {
  gap: Gap
  index: number
}

export function GapCard({ gap, index }: Props) {
  return (
    <article
      className="bg-zinc-900 border border-zinc-800 rounded-lg p-5"
      aria-label={`Market gap ${index + 1}`}
    >
      <p className="text-sm text-zinc-100 mb-3 leading-relaxed">{gap.description}</p>
      <dl className="grid grid-cols-2 gap-4 text-xs">
        <div>
          <dt className="text-zinc-500 mb-1">Addressability</dt>
          <dd className="text-zinc-300">{gap.addressability}</dd>
        </div>
        <div>
          <dt className="text-zinc-500 mb-1">Risk</dt>
          <dd className="text-zinc-300">{gap.risk}</dd>
        </div>
      </dl>
    </article>
  )
}
