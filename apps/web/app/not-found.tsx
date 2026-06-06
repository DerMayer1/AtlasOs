import Link from 'next/link'

export default function NotFound() {
  return (
    <div className="min-h-screen bg-black flex items-center justify-center">
      <div className="text-center px-6">
        <p className="text-zinc-600 text-xs uppercase tracking-widest mb-4">404</p>
        <h1 className="text-white text-2xl font-semibold mb-3">Page not found</h1>
        <p className="text-zinc-500 text-sm mb-8">
          The page you're looking for doesn't exist or has been moved.
        </p>
        <Link
          href="/"
          className="text-sm bg-white text-black px-4 py-2 rounded-md hover:bg-zinc-200 transition"
        >
          Back to home
        </Link>
      </div>
    </div>
  )
}
