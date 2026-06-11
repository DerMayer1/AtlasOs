'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { api } from '@/lib/api'

export default function NewWorkspacePage() {
  const router = useRouter()
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [form, setForm] = useState({
    name: '',
    company_name: '',
    website_url: '',
    description: '',
    target_market: '',
  })

  function update(field: keyof typeof form, value: string) {
    setForm((current) => ({ ...current, [field]: value }))
  }

  async function submit(event: React.FormEvent) {
    event.preventDefault()
    setLoading(true)
    setError('')
    try {
      const workspace = await api.workspaces.create({
        ...form,
        target_market: form.target_market || undefined,
      })
      router.push(`/dashboard/workspaces/${workspace.id}`)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not create market')
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-black text-white">
      <div className="max-w-2xl mx-auto px-6 py-16">
        <p className="text-xs uppercase tracking-widest text-zinc-500 mb-3">
          New monitored market
        </p>
        <h1 className="text-3xl font-semibold mb-2">Define the market</h1>
        <p className="text-sm text-zinc-400 mb-10">
          AtlasOS will discover a candidate competitor set for your review.
        </p>

        <form onSubmit={submit} className="space-y-6">
          <Field label="Workspace name">
            <input
              required
              value={form.name}
              onChange={(event) => update('name', event.target.value)}
              placeholder="Developer tools market"
              className={inputClass}
            />
          </Field>
          <Field label="Your company">
            <input
              required
              value={form.company_name}
              onChange={(event) => update('company_name', event.target.value)}
              placeholder="Linear"
              className={inputClass}
            />
          </Field>
          <Field label="Website URL">
            <input
              required
              type="url"
              value={form.website_url}
              onChange={(event) => update('website_url', event.target.value)}
              placeholder="https://linear.app"
              className={inputClass}
            />
          </Field>
          <Field label="What does the company do?">
            <textarea
              required
              maxLength={500}
              rows={4}
              value={form.description}
              onChange={(event) => update('description', event.target.value)}
              placeholder="Project management software designed for modern product and engineering teams."
              className={`${inputClass} resize-none`}
            />
          </Field>
          <Field label="Target market" hint="Optional">
            <input
              value={form.target_market}
              onChange={(event) => update('target_market', event.target.value)}
              placeholder="B2B SaaS, software teams"
              className={inputClass}
            />
          </Field>

          {error && <p className="text-sm text-red-400">{error}</p>}

          <button
            type="submit"
            disabled={loading}
            className="w-full bg-white text-black text-sm font-medium py-3 rounded-md hover:bg-zinc-200 disabled:opacity-50"
          >
            {loading ? 'Creating and discovering…' : 'Create market and discover competitors'}
          </button>
        </form>
      </div>
    </div>
  )
}

const inputClass =
  'w-full bg-zinc-900 border border-zinc-700 rounded-md px-3 py-2.5 text-sm text-white placeholder-zinc-600 focus:outline-none focus:border-zinc-400'

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
      <label className="block text-sm text-zinc-300 mb-1">
        {label}
        {hint && <span className="text-zinc-600"> · {hint}</span>}
      </label>
      {children}
    </div>
  )
}
