'use client'

import { useCallback, useEffect, useRef, useState } from 'react'
import { api } from './api'
import type { Analysis } from '@atlasos/types'

const POLL_INTERVAL_MS = 3000
const TERMINAL_STATUSES = new Set(['complete', 'failed'])

/**
 * Polls GET /analyses/:id every 3 seconds until the analysis reaches
 * a terminal state (complete or failed). Used as a fallback when SSE
 * is unavailable or the connection drops.
 */
export function useAnalysisPolling(id: string, initialStatus: string) {
  const [analysis, setAnalysis] = useState<Analysis | null>(null)
  const [error, setError] = useState<string | null>(null)
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  const poll = useCallback(async () => {
    try {
      const data = await api.analyses.get(id)
      setAnalysis(data)
      if (!TERMINAL_STATUSES.has(data.status)) {
        timerRef.current = setTimeout(poll, POLL_INTERVAL_MS)
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Polling failed')
    }
  }, [id])

  useEffect(() => {
    if (TERMINAL_STATUSES.has(initialStatus)) return
    poll()
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current)
    }
  }, [poll, initialStatus])

  return { analysis, error }
}
