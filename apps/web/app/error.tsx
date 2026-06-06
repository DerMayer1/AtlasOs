'use client'

import Link from 'next/link'

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string }
  reset: () => void
}) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-black text-white flex items-center justify-center">
        <div className="text-center px-6">
          <p className="text-zinc-600 text-xs uppercase tracking-widest mb-4">Error</p>
          <h1 className="text-white text-2xl font-semibold mb-3">Something went wrong</h1>
          <p className="text-zinc-500 text-sm mb-8 max-w-sm">
            {error.message || 'An unexpected error occurred. Our team has been notified.'}
          </p>
          <div className="flex gap-3 justify-center">
            <button
              onClick={reset}
              className="text-sm bg-white text-black px-4 py-2 rounded-md hover:bg-zinc-200 transition"
            >
              Try again
            </button>
            <Link
              href="/"
              className="text-sm border border-zinc-700 text-zinc-300 px-4 py-2 rounded-md hover:border-zinc-500 transition"
            >
              Go home
            </Link>
          </div>
        </div>
      </body>
    </html>
  )
}
