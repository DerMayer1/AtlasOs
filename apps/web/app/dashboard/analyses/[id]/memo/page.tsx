'use client'

import { useEffect, useState } from 'react'
import { useParams, useRouter } from 'next/navigation'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { api } from '@/lib/api'
import type { Memo } from '@atlasos/types'

export default function MemoPage() {
  const { id } = useParams<{ id: string }>()
  const router = useRouter()
  const [memo, setMemo] = useState<Memo | null>(null)
  const [loading, setLoading] = useState(true)
  const [exporting, setExporting] = useState(false)

  useEffect(() => {
    api.analyses.getMemo(id)
      .then(setMemo)
      .catch(() => router.push(`/dashboard/analyses/${id}`))
      .finally(() => setLoading(false))
  }, [id, router])

  async function downloadPDF() {
    setExporting(true)
    try {
      const blob = await api.analyses.exportMemo(id, 'pdf') as Blob
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `market-memo-${id.slice(0, 8)}.pdf`
      a.click()
      URL.revokeObjectURL(url)
    } finally {
      setExporting(false)
    }
  }

  async function downloadMarkdown() {
    if (!memo) return
    const blob = new Blob([memo.content_md], { type: 'text/markdown' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `market-memo-${id.slice(0, 8)}.md`
    a.click()
    URL.revokeObjectURL(url)
  }

  if (loading) return <LoadingState />

  return (
    <div className="min-h-screen bg-black text-white">
      <div className="max-w-3xl mx-auto px-6 py-12">

        {/* Toolbar */}
        <div className="flex items-center justify-between mb-12">
          <button
            onClick={() => router.back()}
            className="text-sm text-zinc-500 hover:text-white transition"
          >
            ← Back
          </button>
          <div className="flex gap-3">
            <button
              onClick={downloadMarkdown}
              className="text-sm px-4 py-2 border border-zinc-700 rounded-md text-zinc-300 hover:border-zinc-500 transition"
            >
              .md
            </button>
            <button
              onClick={downloadPDF}
              disabled={exporting}
              className="text-sm px-4 py-2 bg-white text-black rounded-md hover:bg-zinc-200 transition disabled:opacity-50"
            >
              {exporting ? 'Generating…' : 'Export PDF'}
            </button>
          </div>
        </div>

        {/* Memo content */}
        <article className="prose prose-invert prose-zinc max-w-none
          prose-headings:font-semibold prose-headings:tracking-tight
          prose-h1:text-3xl prose-h2:text-xl prose-h2:mt-12
          prose-p:text-zinc-300 prose-p:leading-relaxed
          prose-li:text-zinc-300 prose-strong:text-white
          prose-em:text-zinc-400">
          <ReactMarkdown remarkPlugins={[remarkGfm]}>
            {memo?.content_md ?? ''}
          </ReactMarkdown>
        </article>

      </div>
    </div>
  )
}

function LoadingState() {
  return (
    <div className="min-h-screen bg-black flex items-center justify-center">
      <div className="text-zinc-500 text-sm">Loading memo…</div>
    </div>
  )
}
