'use client'

export default function AnalysisError({
  error,
  reset,
}: {
  error: Error & { digest?: string }
  reset: () => void
}) {
  return (
    <div className="min-h-screen bg-black flex items-center justify-center">
      <div className="max-w-sm w-full px-6 text-center">
        <p className="text-zinc-500 text-xs uppercase tracking-widest mb-3">Error</p>
        <h2 className="text-white text-lg font-medium mb-2">Analysis unavailable</h2>
        <p className="text-zinc-500 text-sm mb-6">{error.message}</p>
        <button
          onClick={reset}
          className="text-sm bg-white text-black px-4 py-2 rounded-md hover:bg-zinc-200 transition"
        >
          Try again
        </button>
      </div>
    </div>
  )
}
