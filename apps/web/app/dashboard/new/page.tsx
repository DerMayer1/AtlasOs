'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { api } from '@/lib/api'

export default function NewAnalysisPage() {
  const router = useRouter()
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [form, setForm] = useState({
    company_name: '',
    website_url: '',
    description: '',
    target_market: '',
    known_competitors: '',
    analysis_depth: 'standard' as 'quick' | 'standard' | 'deep',
  })

  function update(field: string, value: string) {
    setForm((prev) => ({ ...prev, [field]: value }))
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setLoading(true)
    setError('')
    try {
      const analysis = await api.analyses.create({
        company_name: form.company_name,
        website_url: form.website_url,
        description: form.description,
        target_market: form.target_market || undefined,
        known_competitors: form.known_competitors
          ? form.known_competitors.split(',').map((s) => s.trim()).filter(Boolean)
          : [],
        analysis_depth: form.analysis_depth,
      })
      router.push(
        analysis.status === 'complete'
          ? `/dashboard/analyses/${analysis.id}`
          : `/dashboard/analyses/${analysis.id}/progress`,
      )
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Something went wrong')
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-black text-white">
      <div className="max-w-2xl mx-auto px-6 py-16">
        <h1 className="text-3xl font-semibold tracking-tight mb-2">New Analysis</h1>
        <p className="text-zinc-400 text-sm mb-10">
          Enter a company to map its competitive landscape.
        </p>

        <form onSubmit={handleSubmit} className="space-y-6">
          <Field label="Company name *">
            <input
              type="text"
              value={form.company_name}
              onChange={(e) => update('company_name', e.target.value)}
              required
              placeholder="Linear"
              className={inputCls}
            />
          </Field>

          <Field label="Website URL *">
            <input
              type="url"
              value={form.website_url}
              onChange={(e) => update('website_url', e.target.value)}
              required
              placeholder="https://linear.app"
              className={inputCls}
            />
          </Field>

          <Field label="Description *" hint="1–3 sentences. Max 500 characters.">
            <textarea
              value={form.description}
              onChange={(e) => update('description', e.target.value)}
              required
              maxLength={500}
              rows={3}
              placeholder="Linear is a project management tool built for modern software teams…"
              className={inputCls + ' resize-none'}
            />
            <span className="text-xs text-zinc-500 mt-1 block text-right">
              {form.description.length}/500
            </span>
          </Field>

          <Field label="Target market" hint="Optional — industry or geography">
            <input
              type="text"
              value={form.target_market}
              onChange={(e) => update('target_market', e.target.value)}
              placeholder="B2B SaaS, North America"
              className={inputCls}
            />
          </Field>

          <Field label="Known competitors" hint="Optional — comma separated, up to 5">
            <input
              type="text"
              value={form.known_competitors}
              onChange={(e) => update('known_competitors', e.target.value)}
              placeholder="Jira, Asana, Monday"
              className={inputCls}
            />
          </Field>

          <Field label="Analysis depth">
            <div className="flex gap-3">
              {(['quick', 'standard', 'deep'] as const).map((d) => (
                <button
                  key={d}
                  type="button"
                  onClick={() => update('analysis_depth', d)}
                  className={`flex-1 py-2 text-sm rounded-md border transition capitalize ${
                    form.analysis_depth === d
                      ? 'bg-white text-black border-white'
                      : 'bg-transparent text-zinc-400 border-zinc-700 hover:border-zinc-500'
                  }`}
                >
                  {d}
                </button>
              ))}
            </div>
          </Field>

          {error && <p className="text-red-400 text-sm">{error}</p>}

          <button
            type="submit"
            disabled={loading}
            className="w-full bg-white text-black font-medium text-sm py-3 rounded-md hover:bg-zinc-200 transition disabled:opacity-50"
          >
            {loading ? 'Starting analysis…' : 'Run analysis →'}
          </button>
        </form>
      </div>
    </div>
  )
}

const inputCls =
  'w-full bg-zinc-900 border border-zinc-700 rounded-md px-3 py-2 text-sm text-white placeholder-zinc-500 focus:outline-none focus:border-zinc-400'

function Field({
  label,
  hint,
  children,
}: {
  label: string
  hint?: string
  children: React.ReactNode
}) {
  return (
    <div>
      <label className="block text-sm text-zinc-300 mb-1">{label}</label>
      {hint && <p className="text-xs text-zinc-500 mb-1">{hint}</p>}
      {children}
    </div>
  )
}
