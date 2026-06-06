import Link from 'next/link'

export default function HomePage() {
  return (
    <div className="min-h-screen bg-black text-white flex flex-col">

      {/* Nav */}
      <nav className="flex items-center justify-between px-8 py-6 border-b border-zinc-900">
        <span className="font-semibold tracking-tight">AtlasOS</span>
        <Link
          href="/auth/login"
          className="text-sm text-zinc-400 hover:text-white transition"
        >
          Sign in →
        </Link>
      </nav>

      {/* Hero */}
      <main className="flex-1 flex flex-col items-center justify-center px-6 text-center">
        <p className="text-xs font-medium uppercase tracking-widest text-zinc-500 mb-6">
          Montclair Intelligence Company
        </p>
        <h1 className="text-5xl sm:text-6xl font-semibold tracking-tight leading-tight max-w-2xl">
          Map the competitive<br />landscape of any B2B company.
        </h1>
        <p className="text-zinc-400 mt-6 text-lg max-w-lg leading-relaxed">
          Input a company. Get a structured market map, competitive analysis,
          and strategic memo — in under 60 seconds.
        </p>
        <div className="flex gap-4 mt-10">
          <Link
            href="/demo"
            className="px-6 py-3 border border-zinc-700 rounded-md text-sm hover:border-zinc-500 transition"
          >
            View demo
          </Link>
          <Link
            href="/auth/login"
            className="px-6 py-3 bg-white text-black rounded-md text-sm font-medium hover:bg-zinc-200 transition"
          >
            Get started
          </Link>
        </div>
      </main>

      {/* Footer */}
      <footer className="px-8 py-6 border-t border-zinc-900 text-center">
        <p className="text-zinc-600 text-xs">
          Montclair Intelligence Company — AtlasOS v1
        </p>
      </footer>
    </div>
  )
}
