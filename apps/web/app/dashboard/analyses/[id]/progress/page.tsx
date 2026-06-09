'use client'

import { useEffect, useState } from 'react'
import { useRouter, useParams } from 'next/navigation'
import { api } from '@/lib/api'

const STAGES = [
  'Website Extractor',
  'Category Classifier',
  'Competitor Searcher',
  'Competitor Classifier',
  'Positioning Analyzer',
  'Gap Detector',
  'Recommendation Engine',
  'Memo Composer',
]

interface StageState {
  status: 'pending' | 'running' | 'complete' | 'failed'
  duration_ms?: number
}

export default function ProgressPage() {
  const { id } = useParams<{ id: string }>()
  const router = useRouter()
  const [stages, setStages] = useState<StageState[]>(STAGES.map(() => ({ status: 'pending' })))
  const [failed, setFailed] = useState(false)
  const [errorMsg, setErrorMsg] = useState('')

  useEffect(() => {
    let source: EventSource | null = null
    let pollTimer: ReturnType<typeof setTimeout> | null = null
    let stopped = false

    async function pollStatus() {
      try {
        const analysis = await api.analyses.get(id)
        if (analysis.status === 'complete') {
          router.push(`/dashboard/analyses/${id}`)
          return
        }
        if (analysis.status === 'failed') {
          setFailed(true)
          setErrorMsg(analysis.error ?? 'Analysis failed')
          return
        }
      } catch (error) {
        setFailed(true)
        setErrorMsg(error instanceof Error ? error.message : 'Could not load analysis status')
        return
      }

      if (!stopped) pollTimer = setTimeout(pollStatus, 3000)
    }

    function connect() {
      source = new EventSource(`/api/analyses/${id}/stream`)

      source.addEventListener('stage_start', (e) => {
        const { stage } = JSON.parse(e.data)
        const idx = stage - 1
        setStages((prev) => {
          const next = [...prev]
          next[idx] = { status: 'running' }
          return next
        })
      })

      source.addEventListener('stage_complete', (e) => {
        const { stage, duration_ms } = JSON.parse(e.data)
        const idx = stage - 1
        setStages((prev) => {
          const next = [...prev]
          next[idx] = { status: 'complete', duration_ms }
          return next
        })
      })

      source.addEventListener('stage_failed', (e) => {
        const { stage, error } = JSON.parse(e.data)
        const idx = stage - 1
        setStages((prev) => {
          const next = [...prev]
          next[idx] = { status: 'failed' }
          return next
        })
        setFailed(true)
        setErrorMsg(error)
      })

      source.addEventListener('analysis_complete', () => {
        stopped = true
        source?.close()
        router.push(`/dashboard/analyses/${id}`)
      })

      source.addEventListener('analysis_failed', (e) => {
        const { error } = JSON.parse(e.data)
        stopped = true
        setFailed(true)
        setErrorMsg(error)
        source?.close()
      })

      source.onerror = () => {
        source?.close()
        if (!stopped && !pollTimer) void pollStatus()
      }
    }

    connect()
    return () => {
      stopped = true
      source?.close()
      if (pollTimer) clearTimeout(pollTimer)
    }
  }, [id, router])

  return (
    <div className="min-h-screen bg-black text-white flex items-center justify-center">
      <div className="max-w-md w-full px-6">
        <h1 className="text-2xl font-semibold mb-2">Running analysis</h1>
        <p className="text-zinc-400 text-sm mb-10">Processing 8 stages. This takes under 60 seconds.</p>

        <div className="space-y-3">
          {STAGES.map((name, i) => {
            const s = stages[i]
            return (
              <div key={name} className="flex items-center gap-3">
                <div className={`w-6 h-6 rounded-full flex items-center justify-center text-xs flex-shrink-0 ${
                  s.status === 'complete' ? 'bg-white text-black' :
                  s.status === 'running'  ? 'bg-zinc-700 text-white animate-pulse' :
                  s.status === 'failed'   ? 'bg-red-500 text-white' :
                  'bg-zinc-800 text-zinc-600'
                }`}>
                  {s.status === 'complete' ? '✓' : i + 1}
                </div>
                <span className={`text-sm ${s.status === 'pending' ? 'text-zinc-600' : 'text-white'}`}>
                  {name}
                </span>
                {s.duration_ms && (
                  <span className="ml-auto text-xs text-zinc-500">{s.duration_ms}ms</span>
                )}
              </div>
            )
          })}
        </div>

        {failed && (
          <div className="mt-8 p-4 bg-red-950 border border-red-800 rounded-md">
            <p className="text-red-300 text-sm font-medium">Analysis failed</p>
            <p className="text-red-400 text-xs mt-1">{errorMsg}</p>
          </div>
        )}
      </div>
    </div>
  )
}
